-- CareerCompass AI — Database Schema
-- Requires Supabase (PostgreSQL)

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ---------------------------------------------------------------------------
-- 1. PROFILES
-- ---------------------------------------------------------------------------
CREATE TABLE profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT UNIQUE NOT NULL,
    full_name TEXT NOT NULL,
    branch TEXT,
    semester INTEGER CHECK (semester >= 1 AND semester <= 6),
    cgpa NUMERIC(4,2) CHECK (cgpa >= 0.0 AND cgpa <= 10.0),
    career_goal TEXT,
    profile_version INTEGER NOT NULL DEFAULT 1,
    is_admin BOOLEAN NOT NULL DEFAULT false,
    assessment_signals JSONB DEFAULT '{}'::jsonb,
    assessment_language TEXT NOT NULL DEFAULT 'en',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- 2. REFERENCE DATA (Careers, Skills, Interests, Projects)
-- ---------------------------------------------------------------------------
CREATE TABLE careers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT NOT NULL UNIQUE,
    description TEXT,
    branches TEXT[] NOT NULL DEFAULT '{}',
    min_cgpa NUMERIC(4,2),
    avg_salary_lpa NUMERIC(5,2),
    job_growth TEXT,
    industry TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE skills (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE interests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    difficulty TEXT CHECK (difficulty IN ('beginner', 'intermediate', 'advanced')),
    estimated_hours INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- 3. MAPPINGS
-- ---------------------------------------------------------------------------
CREATE TABLE career_skills (
    career_id UUID REFERENCES careers(id) ON DELETE CASCADE,
    skill_id UUID REFERENCES skills(id) ON DELETE CASCADE,
    required_level TEXT CHECK (required_level IN ('beginner', 'intermediate', 'advanced')) NOT NULL DEFAULT 'beginner',
    weight NUMERIC(3,2) NOT NULL DEFAULT 1.0,
    PRIMARY KEY (career_id, skill_id)
);

CREATE TABLE career_projects (
    career_id UUID REFERENCES careers(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    PRIMARY KEY (career_id, project_id)
);

-- ---------------------------------------------------------------------------
-- 4. STUDENT DATA
-- ---------------------------------------------------------------------------
CREATE TABLE student_skills (
    profile_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    skill_id UUID REFERENCES skills(id) ON DELETE CASCADE,
    proficiency TEXT CHECK (proficiency IN ('beginner', 'intermediate', 'advanced')) NOT NULL DEFAULT 'beginner',
    PRIMARY KEY (profile_id, skill_id)
);

CREATE TABLE student_interests (
    profile_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    interest_id UUID REFERENCES interests(id) ON DELETE CASCADE,
    PRIMARY KEY (profile_id, interest_id)
);

-- ---------------------------------------------------------------------------
-- 5. ASSESSMENTS
-- ---------------------------------------------------------------------------
CREATE TABLE assessment_questions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    question_text TEXT NOT NULL,
    question_text_te TEXT,
    category TEXT NOT NULL,
    phase TEXT NOT NULL DEFAULT 'broad',
    domain TEXT NOT NULL DEFAULT 'general',
    order_num INTEGER NOT NULL DEFAULT 1,
    is_active BOOLEAN NOT NULL DEFAULT true
);

CREATE TABLE assessment_options (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    question_id UUID REFERENCES assessment_questions(id) ON DELETE CASCADE,
    option_text TEXT NOT NULL,
    option_text_te TEXT,
    career_weight JSONB NOT NULL DEFAULT '{}'::jsonb,
    domain_weight JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE assessment_answers (
    profile_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    question_id UUID REFERENCES assessment_questions(id) ON DELETE CASCADE,
    option_id UUID REFERENCES assessment_options(id) ON DELETE CASCADE,
    PRIMARY KEY (profile_id, question_id)
);

-- ---------------------------------------------------------------------------
-- 6. AI ANALYSES
-- ---------------------------------------------------------------------------
CREATE TABLE career_analyses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    profile_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    profile_version INTEGER NOT NULL,
    model_name TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    summary TEXT,
    recommended_careers JSONB NOT NULL DEFAULT '[]'::jsonb,
    strengths JSONB NOT NULL DEFAULT '[]'::jsonb,
    skill_gaps JSONB NOT NULL DEFAULT '[]'::jsonb,
    priority_skills JSONB NOT NULL DEFAULT '[]'::jsonb,
    roadmap_steps JSONB NOT NULL DEFAULT '[]'::jsonb,
    project_recommendations JSONB NOT NULL DEFAULT '[]'::jsonb,
    next_steps JSONB NOT NULL DEFAULT '[]'::jsonb,
    selected_career TEXT NULL
);

CREATE TABLE roadmap_progress (
    analysis_id UUID REFERENCES career_analyses(id) ON DELETE CASCADE,
    profile_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    step_number INTEGER NOT NULL,
    completed BOOLEAN NOT NULL DEFAULT false,
    completed_at TIMESTAMPTZ,
    PRIMARY KEY (analysis_id, profile_id, step_number)
);

CREATE TABLE resume_analyses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    profile_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    analyzed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    guidance_score INTEGER CHECK (guidance_score >= 0 AND guidance_score <= 100),
    strengths JSONB NOT NULL DEFAULT '[]'::jsonb,
    missing_skills JSONB NOT NULL DEFAULT '[]'::jsonb,
    formatting_feedback JSONB NOT NULL DEFAULT '[]'::jsonb,
    project_suggestions JSONB NOT NULL DEFAULT '[]'::jsonb,
    skill_alignment TEXT,
    improvement_suggestions JSONB NOT NULL DEFAULT '[]'::jsonb
);

-- ---------------------------------------------------------------------------
-- 7. CHAT
-- ---------------------------------------------------------------------------
CREATE TABLE chat_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    profile_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE chat_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role TEXT CHECK (role IN ('user', 'assistant')) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- INDEXES
-- ---------------------------------------------------------------------------
CREATE INDEX idx_career_analyses_profile ON career_analyses(profile_id);
CREATE INDEX idx_resume_analyses_profile ON resume_analyses(profile_id);
CREATE INDEX idx_chat_sessions_profile ON chat_sessions(profile_id);
CREATE INDEX idx_chat_messages_session ON chat_messages(session_id);
