-- ============================================
-- Migration: Add n8n NOTIFY Trigger
-- Sends notification when new job is inserted
-- ============================================

-- ============================================
-- 1. NOTIFY FUNCTION
-- Sends JSON payload to n8n_jobs_channel
-- ============================================

CREATE OR REPLACE FUNCTION notify_n8n_new_job()
RETURNS TRIGGER AS $$
BEGIN
  -- Only notify for pending jobs
  IF NEW.status = 'pending' THEN
    PERFORM pg_notify(
      'n8n_jobs_channel',
      json_build_object(
        'id', NEW.id,
        'user_id', NEW.user_id,
        'discord_message_id', NEW.discord_message_id,
        'product_name', NEW.product_name,
        'garment', NEW.garment,
        'size', NEW.size,
        'input_file_paths', NEW.input_file_paths,
        'custom_prompt', NEW.custom_prompt,
        'created_at', NEW.created_at
      )::text
    );
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION notify_n8n_new_job IS 'Sends NOTIFY event to n8n when a new pending job is inserted';

-- ============================================
-- 2. TRIGGER ON INSERT
-- ============================================

DROP TRIGGER IF EXISTS trg_n8n_new_job ON jobs;

CREATE TRIGGER trg_n8n_new_job
  AFTER INSERT ON jobs
  FOR EACH ROW
  EXECUTE FUNCTION notify_n8n_new_job();

COMMENT ON TRIGGER trg_n8n_new_job ON jobs IS 'Triggers n8n notification on new job insert';

-- ============================================
-- 3. VERIFICATION
-- ============================================

DO $$
BEGIN
  RAISE NOTICE 'n8n NOTIFY trigger created successfully!';
  RAISE NOTICE 'Channel: n8n_jobs_channel';
  RAISE NOTICE 'Trigger: trg_n8n_new_job';
  RAISE NOTICE 'Function: notify_n8n_new_job';
END $$;

-- Verify trigger exists
SELECT tgname AS trigger_name,
       proname AS function_name
FROM pg_trigger t
JOIN pg_proc p ON t.tgfoid = p.oid
WHERE tgname = 'trg_n8n_new_job';
