-- CareerCompass AI — Database Migration: Add selected_career to career_analyses
-- Allows students to select one career from Top 3 recommendations for role-specific roadmap generation

ALTER TABLE career_analyses
ADD COLUMN IF NOT EXISTS selected_career TEXT;
