-- ============================================
-- Migration: Cleanup Polling Elements
-- Removes redundant elements now that NOTIFY is used
-- ============================================

-- ============================================
-- 1. DROP REDUNDANT FUNCTION
-- ============================================

DROP FUNCTION IF EXISTS take_next_job(TEXT);

-- ============================================
-- 2. DROP REDUNDANT INDEXES
-- ============================================

DROP INDEX IF EXISTS idx_jobs_queue;
DROP INDEX IF EXISTS idx_jobs_stale;

-- ============================================
-- 3. DROP REDUNDANT COLUMNS
-- ============================================

ALTER TABLE jobs DROP COLUMN IF EXISTS locked_by;
ALTER TABLE jobs DROP COLUMN IF EXISTS locked_at;

-- ============================================
-- 4. UPDATE complete_job FUNCTION
-- ============================================

CREATE OR REPLACE FUNCTION complete_job(
  p_job_id UUID,
  p_output_path TEXT
) RETURNS VOID AS $$
BEGIN
  UPDATE jobs
  SET
    status = 'done',
    output_file_path = p_output_path,
    completed_at = NOW()
  WHERE id = p_job_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION complete_job IS 'Marks a job as successfully completed with output path';

-- ============================================
-- 5. UPDATE fail_job FUNCTION
-- ============================================

CREATE OR REPLACE FUNCTION fail_job(
  p_job_id UUID,
  p_error_msg TEXT
) RETURNS VOID AS $$
DECLARE
  v_attempts INTEGER;
  v_max_attempts INTEGER;
BEGIN
  SELECT attempts, max_attempts
  INTO v_attempts, v_max_attempts
  FROM jobs
  WHERE id = p_job_id;

  IF v_attempts >= v_max_attempts THEN
    -- Max attempts reached: permanent failure
    UPDATE jobs
    SET
      status = 'error',
      error_message = p_error_msg,
      completed_at = NOW()
    WHERE id = p_job_id;
  ELSE
    -- Still has retries: reset to pending
    UPDATE jobs
    SET
      status = 'pending',
      error_message = p_error_msg,
      started_at = NULL
    WHERE id = p_job_id;
  END IF;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION fail_job IS 'Marks a job as failed. Retries if attempts < max_attempts';

-- ============================================
-- 6. UPDATE reset_stale_jobs FUNCTION
-- Uses started_at instead of locked_at
-- ============================================

CREATE OR REPLACE FUNCTION reset_stale_jobs(timeout_minutes INTEGER DEFAULT 5)
RETURNS INTEGER AS $$
DECLARE
  v_count INTEGER := 0;
BEGIN
  -- Reset jobs that can be retried
  WITH stale_retry AS (
    UPDATE jobs
    SET
      status = 'pending',
      error_message = 'Job timeout - will retry',
      started_at = NULL
    WHERE status = 'processing'
      AND started_at < NOW() - (timeout_minutes || ' minutes')::INTERVAL
      AND attempts < max_attempts
    RETURNING id
  )
  SELECT COUNT(*) INTO v_count FROM stale_retry;

  -- Mark as error jobs that exceeded max attempts
  WITH stale_error AS (
    UPDATE jobs
    SET
      status = 'error',
      error_message = 'Job timeout - max attempts reached',
      completed_at = NOW()
    WHERE status = 'processing'
      AND started_at < NOW() - (timeout_minutes || ' minutes')::INTERVAL
      AND attempts >= max_attempts
    RETURNING id
  )
  SELECT v_count + COUNT(*) INTO v_count FROM stale_error;

  RETURN v_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION reset_stale_jobs IS 'Resets jobs stuck in processing state based on started_at';

-- ============================================
-- 7. VERIFICATION
-- ============================================

DO $$
BEGIN
  RAISE NOTICE 'Cleanup migration completed successfully!';
  RAISE NOTICE 'Dropped: take_next_job(), locked_by, locked_at, idx_jobs_queue, idx_jobs_stale';
  RAISE NOTICE 'Updated: complete_job(), fail_job(), reset_stale_jobs()';
END $$;
