-- Migration 005: Add gender column to jobs table
-- Date: 2026-01-12
-- Purpose: Store user's gender selection (Homme/Femme) for virtual try-on

-- Add genre column to jobs table
-- Using VARCHAR(10) to support "Homme" and "Femme" values
-- Nullable for backward compatibility with existing jobs
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS genre VARCHAR(10);

-- Add comment to document the column
COMMENT ON COLUMN jobs.genre IS 'User selected gender: Homme or Femme';
