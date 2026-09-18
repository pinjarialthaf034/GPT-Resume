-- CareerCompass AI — Row Level Security (RLS) Policies
-- Enforces canonical Supabase Auth identity (auth.uid() = id / profile_id).
-- Private student data is accessible ONLY by the authenticated owner.
-- Reference data (careers, skills, etc.) is public read, admin write.

-- Enable RLS on all tables
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE careers ENABLE ROW LEVEL SECURITY;
ALTER TABLE skills ENABLE ROW LEVEL SECURITY;
ALTER TABLE interests ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE career_skills ENABLE ROW LEVEL SECURITY;
ALTER TABLE career_projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE student_skills ENABLE ROW LEVEL SECURITY;
ALTER TABLE student_interests ENABLE ROW LEVEL SECURITY;
ALTER TABLE assessment_questions ENABLE ROW LEVEL SECURITY;
ALTER TABLE assessment_options ENABLE ROW LEVEL SECURITY;
ALTER TABLE assessment_answers ENABLE ROW LEVEL SECURITY;
ALTER TABLE career_analyses ENABLE ROW LEVEL SECURITY;
ALTER TABLE roadmap_progress ENABLE ROW LEVEL SECURITY;
ALTER TABLE resume_analyses ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;

-- ---------------------------------------------------------------------------
-- 1. REFERENCE DATA (Public Read, Admin Write)
-- ---------------------------------------------------------------------------
CREATE POLICY "Public read careers" ON careers FOR SELECT USING (true);
CREATE POLICY "Admin write careers" ON careers FOR ALL TO authenticated
USING (auth.uid() IN (SELECT id FROM profiles WHERE is_admin = true))
WITH CHECK (auth.uid() IN (SELECT id FROM profiles WHERE is_admin = true));

CREATE POLICY "Public read skills" ON skills FOR SELECT USING (true);
CREATE POLICY "Admin write skills" ON skills FOR ALL TO authenticated
USING (auth.uid() IN (SELECT id FROM profiles WHERE is_admin = true))
WITH CHECK (auth.uid() IN (SELECT id FROM profiles WHERE is_admin = true));

CREATE POLICY "Public read interests" ON interests FOR SELECT USING (true);
CREATE POLICY "Admin write interests" ON interests FOR ALL TO authenticated
USING (auth.uid() IN (SELECT id FROM profiles WHERE is_admin = true))
WITH CHECK (auth.uid() IN (SELECT id FROM profiles WHERE is_admin = true));

CREATE POLICY "Public read projects" ON projects FOR SELECT USING (true);
CREATE POLICY "Admin write projects" ON projects FOR ALL TO authenticated
USING (auth.uid() IN (SELECT id FROM profiles WHERE is_admin = true))
WITH CHECK (auth.uid() IN (SELECT id FROM profiles WHERE is_admin = true));

CREATE POLICY "Public read career_skills" ON career_skills FOR SELECT USING (true);
CREATE POLICY "Public read career_projects" ON career_projects FOR SELECT USING (true);
CREATE POLICY "Public read assessment_questions" ON assessment_questions FOR SELECT USING (true);
CREATE POLICY "Public read assessment_options" ON assessment_options FOR SELECT USING (true);

CREATE POLICY "Admin write assessment_questions" ON assessment_questions FOR ALL TO authenticated
USING (auth.uid() IN (SELECT id FROM profiles WHERE is_admin = true))
WITH CHECK (auth.uid() IN (SELECT id FROM profiles WHERE is_admin = true));

CREATE POLICY "Admin write assessment_options" ON assessment_options FOR ALL TO authenticated
USING (auth.uid() IN (SELECT id FROM profiles WHERE is_admin = true))
WITH CHECK (auth.uid() IN (SELECT id FROM profiles WHERE is_admin = true));

-- ---------------------------------------------------------------------------
-- 2. STUDENT USER-OWNED DATA (Strict Ownership: auth.uid() = id / profile_id)
-- ---------------------------------------------------------------------------
CREATE POLICY "Users can read own profile" ON profiles FOR SELECT TO authenticated USING (auth.uid() = id);
CREATE POLICY "Users can insert own profile" ON profiles FOR INSERT TO authenticated WITH CHECK (auth.uid() = id);
CREATE POLICY "Users can update own profile" ON profiles FOR UPDATE TO authenticated USING (auth.uid() = id) WITH CHECK (auth.uid() = id);
CREATE POLICY "Users can delete own profile" ON profiles FOR DELETE TO authenticated USING (auth.uid() = id);

CREATE POLICY "Users manage own student_skills" ON student_skills FOR ALL TO authenticated
USING (auth.uid() = profile_id) WITH CHECK (auth.uid() = profile_id);

CREATE POLICY "Users manage own student_interests" ON student_interests FOR ALL TO authenticated
USING (auth.uid() = profile_id) WITH CHECK (auth.uid() = profile_id);

CREATE POLICY "Users manage own assessment_answers" ON assessment_answers FOR ALL TO authenticated
USING (auth.uid() = profile_id) WITH CHECK (auth.uid() = profile_id);

CREATE POLICY "Users manage own career_analyses" ON career_analyses FOR ALL TO authenticated
USING (auth.uid() = profile_id) WITH CHECK (auth.uid() = profile_id);

CREATE POLICY "Users manage own roadmap_progress" ON roadmap_progress FOR ALL TO authenticated
USING (auth.uid() = profile_id) WITH CHECK (auth.uid() = profile_id);

CREATE POLICY "Users manage own resume_analyses" ON resume_analyses FOR ALL TO authenticated
USING (auth.uid() = profile_id) WITH CHECK (auth.uid() = profile_id);

CREATE POLICY "Users manage own chat_sessions" ON chat_sessions FOR ALL TO authenticated
USING (auth.uid() = profile_id) WITH CHECK (auth.uid() = profile_id);

CREATE POLICY "Users manage own chat_messages" ON chat_messages FOR ALL TO authenticated
USING (session_id IN (SELECT id FROM chat_sessions WHERE profile_id = auth.uid()))
WITH CHECK (session_id IN (SELECT id FROM chat_sessions WHERE profile_id = auth.uid()));
