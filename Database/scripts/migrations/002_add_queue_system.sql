-- ============================================
-- Migration: Add Queue System
-- Clothify - PostgreSQL Job Queue
-- ============================================

-- ============================================
-- 1. ADD NEW COLUMNS
-- ============================================

ALTER TABLE jobs ADD COLUMN IF NOT EXISTS locked_by TEXT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS locked_at TIMESTAMP;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS attempts INTEGER DEFAULT 0;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS max_attempts INTEGER DEFAULT 3;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS error_message TEXT;

-- ============================================
-- 2. CREATE INDEXES FOR QUEUE PERFORMANCE
-- ============================================

-- Index for fetching next pending job (ordered by creation time)
CREATE INDEX IF NOT EXISTS idx_jobs_queue
  ON jobs (created_at ASC)
  WHERE status = 'pending';

-- Index for finding stale/stuck jobs
CREATE INDEX IF NOT EXISTS idx_jobs_stale
  ON jobs (locked_at)
  WHERE status = 'processing';

-- ============================================
-- 3. FUNCTION: take_next_job
-- Atomically takes the next pending job
-- Uses FOR UPDATE SKIP LOCKED to prevent race conditions
-- ============================================

CREATE OR REPLACE FUNCTION take_next_job(worker_id TEXT DEFAULT 'n8n-worker')
RETURNS SETOF jobs AS $$
  WITH next_job AS (
    SELECT id FROM jobs
    WHERE status = 'pending'
      AND attempts < max_attempts
    ORDER BY created_at ASC
    LIMIT 1
    FOR UPDATE SKIP LOCKED
  )
  UPDATE jobs SET
    status = 'processing',
    started_at = NOW(),
    locked_at = NOW(),
    locked_by = worker_id,
    attempts = attempts + 1
  WHERE id = (SELECT id FROM next_job)
  RETURNING *;
$$ LANGUAGE sql;

COMMENT ON FUNCTION take_next_job IS 'Atomically takes the next pending job and locks it for processing';

-- ============================================
-- 4. FUNCTION: complete_job
-- Marks a job as successfully completed
-- ============================================

CREATE OR REPLACE FUNCTION complete_job(
  p_job_id UUID,
  p_output_path TEXT
) RETURNS VOID AS $$
  UPDATE jobs SET
    status = 'done',
    output_file_path = p_output_path,
    completed_at = NOW(),
    locked_by = NULL,
    locked_at = NULL,
    error_message = NULL
  WHERE id = p_job_id;
$$ LANGUAGE sql;

COMMENT ON FUNCTION complete_job IS 'Marks a job as successfully completed with output path';

-- ============================================
-- 5. FUNCTION: fail_job
-- Marks a job as failed
-- If max attempts reached: permanent error
-- Otherwise: reset to pending for retry
-- ============================================

CREATE OR REPLACE FUNCTION fail_job(
  p_job_id UUID,
  p_error_msg TEXT
) RETURNS VOID AS $$
DECLARE
  v_attempts INTEGER;
  v_max_attempts INTEGER;
BEGIN
  -- Get current attempt count
  SELECT attempts, max_attempts
  INTO v_attempts, v_max_attempts
  FROM jobs
  WHERE id = p_job_id;

  IF v_attempts >= v_max_attempts THEN
    -- Max attempts reached: permanent failure
    UPDATE jobs SET
      status = 'error',
      error_message = p_error_msg,
      locked_by = NULL,
      locked_at = NULL,
      completed_at = NOW()
    WHERE id = p_job_id;
  ELSE
    -- Still has retries: reset to pending
    UPDATE jobs SET
      status = 'pending',
      error_message = p_error_msg,
      locked_by = NULL,
      locked_at = NULL,
      started_at = NULL
    WHERE id = p_job_id;
  END IF;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION fail_job IS 'Marks a job as failed. Retries if attempts < max_attempts, otherwise permanent error';

-- ============================================
-- 6. FUNCTION: reset_stale_jobs
-- Resets jobs stuck in processing for > 5 minutes
-- Returns count of reset jobs
-- ============================================

CREATE OR REPLACE FUNCTION reset_stale_jobs(timeout_minutes INTEGER DEFAULT 5)
RETURNS INTEGER AS $$
DECLARE
  reset_count INTEGER := 0;
BEGIN
  -- Reset jobs that can be retried
  WITH stale_retry AS (
    UPDATE jobs SET
      status = 'pending',
      error_message = 'Job timeout - will retry',
      locked_by = NULL,
      locked_at = NULL,
      started_at = NULL
    WHERE status = 'processing'
      AND locked_at < NOW() - (timeout_minutes || ' minutes')::INTERVAL
      AND attempts < max_attempts
    RETURNING id
  )
  SELECT COUNT(*) INTO reset_count FROM stale_retry;

  -- Mark as error jobs that exceeded max attempts
  WITH stale_error AS (
    UPDATE jobs SET
      status = 'error',
      error_message = 'Job timeout - max attempts reached',
      locked_by = NULL,
      locked_at = NULL,
      completed_at = NOW()
    WHERE status = 'processing'
      AND locked_at < NOW() - (timeout_minutes || ' minutes')::INTERVAL
      AND attempts >= max_attempts
    RETURNING id
  )
  SELECT reset_count + COUNT(*) INTO reset_count FROM stale_error;

  RETURN reset_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION reset_stale_jobs IS 'Resets jobs stuck in processing state. Default timeout: 5 minutes';

-- ============================================
-- 7. FUNCTION: get_queue_stats
-- Returns queue statistics for monitoring
-- ============================================

CREATE OR REPLACE FUNCTION get_queue_stats()
RETURNS TABLE (
  pending_count INTEGER,
  processing_count INTEGER,
  done_count INTEGER,
  error_count INTEGER,
  oldest_pending TIMESTAMP
) AS $$
  SELECT
    (SELECT COUNT(*)::INTEGER FROM jobs WHERE status = 'pending'),
    (SELECT COUNT(*)::INTEGER FROM jobs WHERE status = 'processing'),
    (SELECT COUNT(*)::INTEGER FROM jobs WHERE status = 'done' AND completed_at > NOW() - INTERVAL '24 hours'),
    (SELECT COUNT(*)::INTEGER FROM jobs WHERE status = 'error' AND created_at > NOW() - INTERVAL '24 hours'),
    (SELECT MIN(created_at) FROM jobs WHERE status = 'pending');
$$ LANGUAGE sql;

COMMENT ON FUNCTION get_queue_stats IS 'Returns queue statistics: pending, processing, done (24h), error (24h), oldest pending';

-- ============================================
-- 8. VERIFICATION
-- ============================================

DO $$
BEGIN
  RAISE NOTICE 'Queue system migration completed successfully!';
  RAISE NOTICE 'New columns: locked_by, locked_at, attempts, max_attempts, error_message';
  RAISE NOTICE 'Functions: take_next_job, complete_job, fail_job, reset_stale_jobs, get_queue_stats';
END $$;
