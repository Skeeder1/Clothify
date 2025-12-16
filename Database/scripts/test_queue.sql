-- ============================================
-- Test Script: Queue System Functions
-- Run after applying all migrations
-- ============================================

-- ============================================
-- SETUP: Create test user and jobs
-- ============================================

-- Create a test user
INSERT INTO users (discord_id, discord_name)
VALUES ('TEST123456789', 'TestUser')
ON CONFLICT (discord_id) DO NOTHING;

-- Get test user ID
DO $$
DECLARE
  v_user_id UUID;
BEGIN
  SELECT id INTO v_user_id FROM users WHERE discord_id = 'TEST123456789';

  -- Create test jobs
  INSERT INTO jobs (user_id, discord_message_id, input_file_paths, product_name, garment, size, status)
  VALUES
    (v_user_id, 'MSG001', '["test1.jpg"]', 'TEST01', 'pull', '2', 'pending'),
    (v_user_id, 'MSG002', '["test2.jpg"]', 'TEST02', 'tshirt', '1', 'pending'),
    (v_user_id, 'MSG003', '["test3.jpg"]', 'TEST03', 'jean', '3', 'pending');

  RAISE NOTICE 'Created 3 test jobs for user %', v_user_id;
END $$;

-- ============================================
-- TEST 1: Queue Stats (initial state)
-- ============================================

\echo '=== TEST 1: Initial Queue Stats ==='
SELECT * FROM get_queue_stats();

-- ============================================
-- TEST 2: Complete a job
-- ============================================

\echo ''
\echo '=== TEST 2: Complete a Job ==='

DO $$
DECLARE
  v_job_id UUID;
BEGIN
  SELECT id INTO v_job_id FROM jobs WHERE product_name = 'TEST01';
  PERFORM complete_job(v_job_id, '/images/output/test01_result.png');
  RAISE NOTICE 'Completed job %', v_job_id;
END $$;

-- Verify completion
SELECT id, product_name, status, output_file_path, completed_at
FROM jobs
WHERE product_name = 'TEST01';

-- ============================================
-- TEST 3: Fail a job (should retry)
-- ============================================

\echo ''
\echo '=== TEST 3: Fail Job (should reset to pending for retry) ==='

-- First set job to processing state
UPDATE jobs SET status = 'processing', started_at = NOW(), attempts = 1
WHERE product_name = 'TEST02';

DO $$
DECLARE
  v_job_id UUID;
BEGIN
  SELECT id INTO v_job_id FROM jobs WHERE product_name = 'TEST02';
  PERFORM fail_job(v_job_id, 'API timeout - test error');
  RAISE NOTICE 'Failed job %', v_job_id;
END $$;

-- Verify it's back to pending (attempts=1, can still retry)
SELECT id, product_name, status, attempts, max_attempts, error_message
FROM jobs
WHERE product_name = 'TEST02';

-- ============================================
-- TEST 4: Fail job until max attempts
-- ============================================

\echo ''
\echo '=== TEST 4: Fail Job Until Max Attempts ==='

DO $$
DECLARE
  v_job_id UUID;
BEGIN
  SELECT id INTO v_job_id FROM jobs WHERE product_name = 'TEST02';

  -- Simulate multiple failures
  UPDATE jobs SET status = 'processing', attempts = 2 WHERE id = v_job_id;
  PERFORM fail_job(v_job_id, 'API error attempt 2');

  UPDATE jobs SET status = 'processing', attempts = 3 WHERE id = v_job_id;
  PERFORM fail_job(v_job_id, 'API error attempt 3 - should be permanent');

  RAISE NOTICE 'Failed job % multiple times', v_job_id;
END $$;

-- Verify it's now in error state
SELECT id, product_name, status, attempts, max_attempts, error_message
FROM jobs
WHERE product_name = 'TEST02';

-- ============================================
-- TEST 5: Reset stale jobs
-- ============================================

\echo ''
\echo '=== TEST 5: Reset Stale Jobs ==='

-- Simulate a stale job (started 10 minutes ago)
UPDATE jobs
SET status = 'processing',
    started_at = NOW() - INTERVAL '10 minutes',
    attempts = 1
WHERE product_name = 'TEST03';

\echo 'Before reset:'
SELECT id, product_name, status, started_at, attempts
FROM jobs
WHERE product_name = 'TEST03';

-- Reset stale jobs
SELECT reset_stale_jobs() AS jobs_reset;

\echo 'After reset:'
SELECT id, product_name, status, started_at, attempts, error_message
FROM jobs
WHERE product_name = 'TEST03';

-- ============================================
-- TEST 6: Final Queue Stats
-- ============================================

\echo ''
\echo '=== TEST 6: Final Queue Stats ==='
SELECT * FROM get_queue_stats();

-- ============================================
-- TEST 7: Verify NOTIFY trigger exists
-- ============================================

\echo ''
\echo '=== TEST 7: Verify NOTIFY Trigger ==='
SELECT tgname AS trigger_name
FROM pg_trigger
WHERE tgname = 'trg_n8n_new_job';

-- ============================================
-- CLEANUP: Remove test data
-- ============================================

\echo ''
\echo '=== CLEANUP ==='

DELETE FROM jobs WHERE product_name LIKE 'TEST%';
DELETE FROM users WHERE discord_id = 'TEST123456789';

\echo 'Test data cleaned up.'
\echo ''
\echo '=== ALL TESTS COMPLETED ==='
