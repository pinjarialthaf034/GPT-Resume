-- =====================================================================
-- CareerCompass AI — Unified Database Identity & Strict RLS Migration
-- Project: Career-Guidance + GPT-Resume Unified Auth System
-- Target: Supabase PostgreSQL (auth.users.id is the canonical identity)
-- =====================================================================

-- Step 1: Ensure profiles table references auth.users(id)
DO $$
BEGIN
    -- Add foreign key constraint if not already referencing auth.users
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints tc
        JOIN information_schema.constraint_column_usage ccu 
          ON tc.constraint_name = ccu.constraint_name
        WHERE tc.table_name = 'profiles' 
          AND tc.constraint_type = 'FOREIGN KEY'
          AND ccu.table_name = 'users'
          AND ccu.column_name = 'id'
    ) THEN
        -- Check if any orphan profiles exist before adding foreign key
        -- In case of existing test profiles not in auth.users, remove or leave notice
        BEGIN
            ALTER TABLE public.profiles
            ADD CONSTRAINT fk_profiles_auth_users
            FOREIGN KEY (id) REFERENCES auth.users(id) ON DELETE CASCADE;
            RAISE NOTICE 'Added foreign key constraint fk_profiles_auth_users to public.profiles';
        EXCEPTION WHEN OTHERS THEN
            RAISE NOTICE 'Could not add fk_profiles_auth_users immediately (may have orphan rows): %', SQLERRM;
        END;
    ELSE
        RAISE NOTICE 'Foreign key to auth.users already exists on public.profiles';
    END IF;
END $$;

-- Step 2: Add assessment_language column to profiles if not present
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'profiles' AND column_name = 'assessment_language'
    ) THEN
        ALTER TABLE public.profiles 
        ADD COLUMN assessment_language TEXT NOT NULL DEFAULT 'en';
        RAISE NOTICE 'Added column assessment_language to public.profiles';
    END IF;
END $$;

-- Step 3: Add multilingual support columns to assessment_questions and assessment_options
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'assessment_questions' AND column_name = 'question_text_te'
    ) THEN
        ALTER TABLE public.assessment_questions 
        ADD COLUMN question_text_te TEXT;
        RAISE NOTICE 'Added question_text_te to public.assessment_questions';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'assessment_options' AND column_name = 'option_text_te'
    ) THEN
        ALTER TABLE public.assessment_options 
        ADD COLUMN option_text_te TEXT;
        RAISE NOTICE 'Added option_text_te to public.assessment_options';
    END IF;
END $$;

-- Step 4: Seed Telugu translations for Assessment Questions
-- Natural, student-friendly Telugu for diploma students in Andhra Pradesh & Telangana
UPDATE public.assessment_questions 
SET question_text_te = 'మీ కాలేజీ మీకు ఒక ప్రాజెక్ట్ ఇచ్చి: "ఏదైనా ఉపయోగకరమైన పనిని నిర్మించండి లేదా మెరుగుపరచండి" అని చెబితే, మీరు దేనిపై పనిచేయడానికి అత్యంత ఆసక్తి చూపుతారు?'
WHERE order_num = 1;

UPDATE public.assessment_questions 
SET question_text_te = 'ఒక స్మార్ట్ హాస్పిటల్ క్లినిక్ తయారుచేసే బృందంలో పనిచేస్తున్నారని ఊహించుకోండి. పరిష్కారంలో ఏ విభాగంలో పనిచేయడం మీకు అత్యంత ఆసక్తికరంగా ఉంటుంది?'
WHERE order_num = 2;

UPDATE public.assessment_questions 
SET question_text_te = 'మీ పనిదినాన్ని ఎక్కడ గడిపినప్పుడు మీరు అత్యంత ఉత్సాహంగా, చురుగ్గా పనిచేయగలరు?'
WHERE order_num = 3;

UPDATE public.assessment_questions 
SET question_text_te = 'ఆసక్తికరమైన వాస్తవాలు మరియు సంఖ్యలు (డేటా) ఎదురైనప్పుడు, మీకు ఏది చేయడం ఆకర్షణీయంగా అనిపిస్తుంది?'
WHERE order_num = 4;

UPDATE public.assessment_questions 
SET question_text_te = 'ఎలక్ట్రిక్ వాహనం లేదా ఆధునిక యంత్రాన్ని చూసినప్పుడు, మీకు ఏ విషయంపై అత్యంత కుతూహలం కలుగుతుంది?'
WHERE order_num = 5;

UPDATE public.assessment_questions 
SET question_text_te = 'ఒక ఆటోమేటెడ్ కర్మాగారం లేదా ప్రొడక్షన్ యూనిట్ చూసినప్పుడు, మీకు ఏ విభాగంపై ఆసక్తి ఉంటుంది?'
WHERE order_num = 6;

UPDATE public.assessment_questions 
SET question_text_te = 'మీరు ఏదైనా సిస్టమ్‌లో సమస్య వచ్చినప్పుడు దాన్ని ఎలా పరిష్కరిస్తారు?'
WHERE order_num = 7;

UPDATE public.assessment_questions 
SET question_text_te = 'ఒక కొత్త సాఫ్ట్‌వేర్ అప్లికేషన్ లేదా ప్రాజెక్ట్ తయారుచేసేటప్పుడు మీ ప్రాధాన్యత ఏమిటి?'
WHERE order_num = 8;

UPDATE public.assessment_questions 
SET question_text_te = 'మీ పనితీరు శైలి (Work Style) ఎలా ఉండాలని మీరు కోరుకుంటారు?'
WHERE order_num = 9;

UPDATE public.assessment_questions 
SET question_text_te = 'ఒక సంక్లిష్టమైన సాంకేతిక సమస్య ఎదురైనప్పుడు, దాన్ని పరిష్కరించడానికి మీ విధానం ఏమిటి?'
WHERE order_num = 10;

-- Telugu options translations for key broad discovery questions
UPDATE public.assessment_options
SET option_text_te = '💻 ఫోన్ లేదా కంప్యూటర్‌లో ప్రజలు ఉపయోగించగల యాప్ లేదా వెబ్‌సైట్ తయారు చేయడం'
WHERE option_text ILIKE '%phone or computer%';

UPDATE public.assessment_options
SET option_text_te = '📊 సమాచారాన్ని విశ్లేషించి, నిర్ణయాలు తీసుకోవడానికి ఉపయోగపడే నమూనాలను కనుగొనడం'
WHERE option_text ILIKE '%discover useful patterns%';

UPDATE public.assessment_options
SET option_text_te = '🛡️ కంప్యూటర్ సిస్టమ్‌ను మరింత సురక్షితంగా మరియు హ్యాకింగ్ నుండి కాపాడటం'
WHERE option_text ILIKE '%Make a computer system safer%';

UPDATE public.assessment_options
SET option_text_te = '⚡ సెన్సార్లు, వైర్లు లేదా ఎలక్ట్రానిక్ భాగాలతో పరికరాలను నిర్మించడం'
WHERE option_text ILIKE '%sensors, wires, or electronic parts%';

UPDATE public.assessment_options
SET option_text_te = '🏍️ యంత్రం, వాహనం లేదా మెకానికల్ పరికరం పనితీరును మెరుగుపరచడం'
WHERE option_text ILIKE '%machine, vehicle, or physical product%';

UPDATE public.assessment_options
SET option_text_te = '📐 భవనం, మౌలిక వసతులు లేదా నిర్మాణాలను డిజైన్ చేయడం'
WHERE option_text ILIKE '%building, space, or physical structure%';

UPDATE public.assessment_options
SET option_text_te = '🏭 ఉత్పత్తి ప్రక్రియలను వేగంగా మరియు ఆటోమేటిక్‌గా మార్చడం'
WHERE option_text ILIKE '%process faster or more automatic%';

UPDATE public.assessment_options
SET option_text_te = '🤷 నాకు ఇంకా స్పష్టత లేదు'
WHERE option_text ILIKE '%not sure yet%';

-- Step 5: Secure Row Level Security (RLS) Configuration
-- Enable RLS on all tables
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.student_skills ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.student_interests ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.assessment_answers ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.career_analyses ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.roadmap_progress ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.resume_analyses ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_messages ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.careers ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.skills ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.interests ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.career_skills ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.career_projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.assessment_questions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.assessment_options ENABLE ROW LEVEL SECURITY;

-- Drop obsolete insecure policies
DROP POLICY IF EXISTS "Public full profiles" ON public.profiles;
DROP POLICY IF EXISTS "Public full student_skills" ON public.student_skills;
DROP POLICY IF EXISTS "Public full student_interests" ON public.student_interests;
DROP POLICY IF EXISTS "Public full assessment_answers" ON public.assessment_answers;
DROP POLICY IF EXISTS "Public full career_analyses" ON public.career_analyses;
DROP POLICY IF EXISTS "Public full roadmap_progress" ON public.roadmap_progress;
DROP POLICY IF EXISTS "Public full resume_analyses" ON public.resume_analyses;
DROP POLICY IF EXISTS "Public full chat_sessions" ON public.chat_sessions;
DROP POLICY IF EXISTS "Public full chat_messages" ON public.chat_messages;

DROP POLICY IF EXISTS "Public full careers" ON public.careers;
DROP POLICY IF EXISTS "Public full skills" ON public.skills;
DROP POLICY IF EXISTS "Public full interests" ON public.interests;
DROP POLICY IF EXISTS "Public full projects" ON public.projects;
DROP POLICY IF EXISTS "Public full career_skills" ON public.career_skills;
DROP POLICY IF EXISTS "Public full career_projects" ON public.career_projects;
DROP POLICY IF EXISTS "Public full assessment_questions" ON public.assessment_questions;
DROP POLICY IF EXISTS "Public full assessment_options" ON public.assessment_options;

-- ---------------------------------------------------------------------------
-- 5a. PROFILES (auth.uid() = id)
-- ---------------------------------------------------------------------------
DROP POLICY IF EXISTS "Users can read own profile" ON public.profiles;
CREATE POLICY "Users can read own profile"
ON public.profiles FOR SELECT
TO authenticated
USING (auth.uid() = id);

DROP POLICY IF EXISTS "Users can insert own profile" ON public.profiles;
CREATE POLICY "Users can insert own profile"
ON public.profiles FOR INSERT
TO authenticated
WITH CHECK (auth.uid() = id);

DROP POLICY IF EXISTS "Users can update own profile" ON public.profiles;
CREATE POLICY "Users can update own profile"
ON public.profiles FOR UPDATE
TO authenticated
USING (auth.uid() = id)
WITH CHECK (auth.uid() = id);

DROP POLICY IF EXISTS "Users can delete own profile" ON public.profiles;
CREATE POLICY "Users can delete own profile"
ON public.profiles FOR DELETE
TO authenticated
USING (auth.uid() = id);

-- ---------------------------------------------------------------------------
-- 5b. STUDENT SKILLS & INTERESTS (auth.uid() = profile_id)
-- ---------------------------------------------------------------------------
DROP POLICY IF EXISTS "Users manage own student_skills" ON public.student_skills;
CREATE POLICY "Users manage own student_skills"
ON public.student_skills FOR ALL
TO authenticated
USING (auth.uid() = profile_id)
WITH CHECK (auth.uid() = profile_id);

DROP POLICY IF EXISTS "Users manage own student_interests" ON public.student_interests;
CREATE POLICY "Users manage own student_interests"
ON public.student_interests FOR ALL
TO authenticated
USING (auth.uid() = profile_id)
WITH CHECK (auth.uid() = profile_id);

-- ---------------------------------------------------------------------------
-- 5c. ASSESSMENTS & ANALYSES (auth.uid() = profile_id)
-- ---------------------------------------------------------------------------
DROP POLICY IF EXISTS "Users manage own assessment_answers" ON public.assessment_answers;
CREATE POLICY "Users manage own assessment_answers"
ON public.assessment_answers FOR ALL
TO authenticated
USING (auth.uid() = profile_id)
WITH CHECK (auth.uid() = profile_id);

DROP POLICY IF EXISTS "Users manage own career_analyses" ON public.career_analyses;
CREATE POLICY "Users manage own career_analyses"
ON public.career_analyses FOR ALL
TO authenticated
USING (auth.uid() = profile_id)
WITH CHECK (auth.uid() = profile_id);

DROP POLICY IF EXISTS "Users manage own roadmap_progress" ON public.roadmap_progress;
CREATE POLICY "Users manage own roadmap_progress"
ON public.roadmap_progress FOR ALL
TO authenticated
USING (auth.uid() = profile_id)
WITH CHECK (auth.uid() = profile_id);

DROP POLICY IF EXISTS "Users manage own resume_analyses" ON public.resume_analyses;
CREATE POLICY "Users manage own resume_analyses"
ON public.resume_analyses FOR ALL
TO authenticated
USING (auth.uid() = profile_id)
WITH CHECK (auth.uid() = profile_id);

-- ---------------------------------------------------------------------------
-- 5d. CHAT SESSIONS & MESSAGES (auth.uid() = profile_id)
-- ---------------------------------------------------------------------------
DROP POLICY IF EXISTS "Users manage own chat_sessions" ON public.chat_sessions;
CREATE POLICY "Users manage own chat_sessions"
ON public.chat_sessions FOR ALL
TO authenticated
USING (auth.uid() = profile_id)
WITH CHECK (auth.uid() = profile_id);

DROP POLICY IF EXISTS "Users manage own chat_messages" ON public.chat_messages;
CREATE POLICY "Users manage own chat_messages"
ON public.chat_messages FOR ALL
TO authenticated
USING (
    session_id IN (SELECT id FROM public.chat_sessions WHERE profile_id = auth.uid())
)
WITH CHECK (
    session_id IN (SELECT id FROM public.chat_sessions WHERE profile_id = auth.uid())
);

-- ---------------------------------------------------------------------------
-- 5e. REFERENCE TABLES (Public Read, Admin Write)
-- ---------------------------------------------------------------------------
DROP POLICY IF EXISTS "Public read careers" ON public.careers;
CREATE POLICY "Public read careers" ON public.careers FOR SELECT USING (true);

DROP POLICY IF EXISTS "Admin write careers" ON public.careers;
CREATE POLICY "Admin write careers" ON public.careers FOR ALL
TO authenticated
USING (auth.uid() IN (SELECT id FROM public.profiles WHERE is_admin = true))
WITH CHECK (auth.uid() IN (SELECT id FROM public.profiles WHERE is_admin = true));

DROP POLICY IF EXISTS "Public read skills" ON public.skills;
CREATE POLICY "Public read skills" ON public.skills FOR SELECT USING (true);

DROP POLICY IF EXISTS "Admin write skills" ON public.skills;
CREATE POLICY "Admin write skills" ON public.skills FOR ALL
TO authenticated
USING (auth.uid() IN (SELECT id FROM public.profiles WHERE is_admin = true))
WITH CHECK (auth.uid() IN (SELECT id FROM public.profiles WHERE is_admin = true));

DROP POLICY IF EXISTS "Public read interests" ON public.interests;
CREATE POLICY "Public read interests" ON public.interests FOR SELECT USING (true);

DROP POLICY IF EXISTS "Admin write interests" ON public.interests;
CREATE POLICY "Admin write interests" ON public.interests FOR ALL
TO authenticated
USING (auth.uid() IN (SELECT id FROM public.profiles WHERE is_admin = true))
WITH CHECK (auth.uid() IN (SELECT id FROM public.profiles WHERE is_admin = true));

DROP POLICY IF EXISTS "Public read projects" ON public.projects;
CREATE POLICY "Public read projects" ON public.projects FOR SELECT USING (true);

DROP POLICY IF EXISTS "Admin write projects" ON public.projects;
CREATE POLICY "Admin write projects" ON public.projects FOR ALL
TO authenticated
USING (auth.uid() IN (SELECT id FROM public.profiles WHERE is_admin = true))
WITH CHECK (auth.uid() IN (SELECT id FROM public.profiles WHERE is_admin = true));

DROP POLICY IF EXISTS "Public read career_skills" ON public.career_skills;
CREATE POLICY "Public read career_skills" ON public.career_skills FOR SELECT USING (true);

DROP POLICY IF EXISTS "Public read career_projects" ON public.career_projects;
CREATE POLICY "Public read career_projects" ON public.career_projects FOR SELECT USING (true);

DROP POLICY IF EXISTS "Public read assessment_questions" ON public.assessment_questions;
CREATE POLICY "Public read assessment_questions" ON public.assessment_questions FOR SELECT USING (true);

DROP POLICY IF EXISTS "Admin write assessment_questions" ON public.assessment_questions;
CREATE POLICY "Admin write assessment_questions" ON public.assessment_questions FOR ALL
TO authenticated
USING (auth.uid() IN (SELECT id FROM public.profiles WHERE is_admin = true))
WITH CHECK (auth.uid() IN (SELECT id FROM public.profiles WHERE is_admin = true));

DROP POLICY IF EXISTS "Public read assessment_options" ON public.assessment_options;
CREATE POLICY "Public read assessment_options" ON public.assessment_options FOR SELECT USING (true);

DROP POLICY IF EXISTS "Admin write assessment_options" ON public.assessment_options;
CREATE POLICY "Admin write assessment_options" ON public.assessment_options FOR ALL
TO authenticated
USING (auth.uid() IN (SELECT id FROM public.profiles WHERE is_admin = true))
WITH CHECK (auth.uid() IN (SELECT id FROM public.profiles WHERE is_admin = true));
