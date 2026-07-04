-- =========================================================================
-- Supabase SQL Initialization & Seeding Script
-- Creates all required tables and indexes for the Faculty Research Assistant
-- =========================================================================

-- 1. Create query_logs table
CREATE TABLE IF NOT EXISTS query_logs (
    id SERIAL PRIMARY KEY,
    query_text VARCHAR(500) NOT NULL,
    response_text TEXT NOT NULL,
    mode VARCHAR(50) DEFAULT 'chat',
    role VARCHAR(50) DEFAULT 'student',
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 2. Create recommendations table
CREATE TABLE IF NOT EXISTS recommendations (
    id SERIAL PRIMARY KEY,
    query_log_id INTEGER REFERENCES query_logs(id) ON DELETE CASCADE,
    faculty_name VARCHAR(200) NOT NULL,
    reasoning TEXT NOT NULL,
    is_fallback BOOLEAN DEFAULT FALSE,
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_recommendations_query_log_id ON recommendations(query_log_id);

-- 3. Create collaborations table
CREATE TABLE IF NOT EXISTS collaborations (
    id SERIAL PRIMARY KEY,
    query_log_id INTEGER REFERENCES query_logs(id) ON DELETE CASCADE,
    faculty_a VARCHAR(200) NOT NULL,
    faculty_b VARCHAR(200) NOT NULL,
    synergy_reason TEXT NOT NULL,
    project_idea TEXT NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_collaborations_query_log_id ON collaborations(query_log_id);

-- 4. Create project_suggestions table
CREATE TABLE IF NOT EXISTS project_suggestions (
    id SERIAL PRIMARY KEY,
    query_log_id INTEGER REFERENCES query_logs(id) ON DELETE CASCADE,
    title VARCHAR(300) NOT NULL,
    description TEXT NOT NULL,
    target_faculty VARCHAR(500),
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_project_suggestions_query_log_id ON project_suggestions(query_log_id);

-- 5. Create feedback table
CREATE TABLE IF NOT EXISTS feedback (
    id SERIAL PRIMARY KEY,
    query_log_id INTEGER REFERENCES query_logs(id) ON DELETE CASCADE,
    rating INTEGER,
    comments TEXT,
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_feedback_query_log_id ON feedback(query_log_id);

-- 6. Create faculty_workload table
CREATE TABLE IF NOT EXISTS faculty_workload (
    id SERIAL PRIMARY KEY,
    faculty_name VARCHAR(200) NOT NULL UNIQUE,
    active_projects INTEGER DEFAULT 0,
    project_titles JSONB DEFAULT '[]'::jsonb,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 7. Create paper_enrichments table
CREATE TABLE IF NOT EXISTS paper_enrichments (
    id SERIAL PRIMARY KEY,
    paper_title_key VARCHAR(500) NOT NULL UNIQUE,
    s2_paper_id VARCHAR(100),
    doi VARCHAR(100),
    venue VARCHAR(200),
    year INTEGER,
    citation_count INTEGER DEFAULT 0,
    influential_citation_count INTEGER DEFAULT 0,
    authors TEXT,
    fields_of_study TEXT,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_paper_enrichments_paper_title_key ON paper_enrichments(paper_title_key);

-- 8. Create semantic_cache table
CREATE TABLE IF NOT EXISTS semantic_cache (
    id SERIAL PRIMARY KEY,
    cache_key VARCHAR(250) NOT NULL UNIQUE,
    response_json TEXT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_semantic_cache_cache_key ON semantic_cache(cache_key);

-- =========================================================================
-- SEED DATA: Seed initial faculty workloads matching paper author profiles
-- =========================================================================
INSERT INTO faculty_workload (faculty_name, active_projects, project_titles)
VALUES 
    ('shirina samreen', 3, '["Trust Management in MANETs", "Refinement of Recommendation Trust", "Attack Patterns in Ad Hoc Networks"]'::jsonb),
    ('akhil jabbar meerja', 2, '["Refinement of Recommendation Trust", "Security in MANETs"]'::jsonb),
    ('jaishree agrawal', 1, '["Software Engineering Practices"]'::jsonb),
    ('nimesh raj', 1, '["Network Security"]'::jsonb),
    ('gagandeep', 2, '["IoT based Health Monitoring", "Blockchain Security"]'::jsonb)
ON CONFLICT (faculty_name) DO NOTHING;
