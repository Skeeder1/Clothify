-- ============================================
-- Clothify Database Migration: Add channel_id
-- ============================================

-- Add discord_channel_id column to jobs table
-- This is needed to reply to messages when jobs are completed
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS discord_channel_id VARCHAR(20);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_jobs_discord_channel_id ON jobs(discord_channel_id);

DO $$
BEGIN
    RAISE NOTICE 'Migration complete: Added discord_channel_id column to jobs table';
END $$;
