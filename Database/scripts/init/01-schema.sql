-- ============================================
-- Clothify Database Schema
-- ============================================

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- ENUMS
-- ============================================

CREATE TYPE job_status AS ENUM ('pending', 'processing', 'done', 'error', 'sent');

CREATE TYPE garment_type AS ENUM (
    'echarpe', 'pull', 'tshirt', 'chemise', 'veste',
    'manteau', 'pantalon', 'jean', 'short', 'jupe',
    'robe', 'bonnet', 'casquette', 'sac', 'other'
);

CREATE TYPE size_code AS ENUM ('1', '2', '3', '4');

-- ============================================
-- TABLE: users
-- ============================================

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    discord_id VARCHAR(20) UNIQUE NOT NULL,
    discord_name VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    last_seen_at TIMESTAMP DEFAULT NOW(),
    total_jobs INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_users_discord_id ON users(discord_id);

-- ============================================
-- TABLE: jobs
-- ============================================

CREATE TABLE jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    discord_message_id VARCHAR(20),
    custom_prompt TEXT,
    input_file_paths TEXT NOT NULL,
    output_file_path TEXT,
    product_name VARCHAR(255),
    garment garment_type DEFAULT 'other',
    size size_code DEFAULT '2',
    status job_status DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_user_id ON jobs(user_id);
CREATE INDEX idx_jobs_created_at ON jobs(created_at);

-- ============================================
-- TABLE: job_logs
-- ============================================

CREATE TABLE job_logs (
    id SERIAL PRIMARY KEY,
    job_id UUID REFERENCES jobs(id) ON DELETE CASCADE,
    status job_status NOT NULL,
    message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_job_logs_job_id ON job_logs(job_id);

-- ============================================
-- Verification message
-- ============================================

DO $$
BEGIN
    RAISE NOTICE 'Clothify schema created successfully!';
    RAISE NOTICE 'Tables: users, jobs, job_logs';
    RAISE NOTICE 'Enums: job_status, garment_type, size_code';
END $$;
