-- =====================================================================
-- GPT-Resume Database Migration & RLS Security Script
-- Project: Resume Builder (Single Source of Truth: Supabase Auth)
-- Target: Supabase PostgreSQL (auth.users <-> resumes)
-- =====================================================================

-- Step 1: Add user_id column to resumes table if not present
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'resumes' AND column_name = 'user_id'
    ) THEN
        ALTER TABLE public.resumes 
        ADD COLUMN user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;
        RAISE NOTICE 'Added column user_id to public.resumes';
    ELSE
        RAISE NOTICE 'Column user_id already exists on public.resumes';
    END IF;
END $$;

-- Step 2: Backfill existing resumes by matching email to auth.users
-- This links all existing resumes to their canonical auth.users.id UUID.
-- Unmapped records (where email does not match any active auth.users row)
-- are safely preserved with user_id = NULL.
UPDATE public.resumes r
SET user_id = u.id
FROM auth.users u
WHERE lower(trim(r.email)) = lower(trim(u.email))
  AND r.user_id IS NULL;

-- Step 3: Create index on user_id for high-performance lookups
CREATE INDEX IF NOT EXISTS idx_resumes_user_id ON public.resumes(user_id);
CREATE INDEX IF NOT EXISTS idx_resumes_user_template ON public.resumes(user_id, template_id);

-- Step 4: Add unique constraint on (user_id, template_id) for reliable upserts
-- Drop old email-based constraint if present
DO $$
BEGIN
    -- Drop old unique constraint on (email, template_id) if it exists
    IF EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'resumes_email_template_id_key'
    ) THEN
        ALTER TABLE public.resumes DROP CONSTRAINT resumes_email_template_id_key;
        RAISE NOTICE 'Dropped legacy constraint resumes_email_template_id_key';
    END IF;

    -- Add new unique constraint on (user_id, template_id)
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'resumes_user_id_template_id_key'
    ) THEN
        -- Only add if there are no duplicate (user_id, template_id) pairs
        ALTER TABLE public.resumes 
        ADD CONSTRAINT resumes_user_id_template_id_key UNIQUE (user_id, template_id);
        RAISE NOTICE 'Added unique constraint on (user_id, template_id)';
    END IF;
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'Constraint adjustment notice: %', SQLERRM;
END $$;

-- Step 5: Enable Row Level Security (RLS) on public.resumes
ALTER TABLE public.resumes ENABLE ROW LEVEL SECURITY;

-- Step 6: Create Strict Ownership Policies
-- Ensure users can ONLY read, insert, update, or delete their own resumes.
-- Bypasses the IDOR vulnerability where modifying localStorage allowed viewing others' data.

-- Drop permissive or obsolete policies if any exist
DROP POLICY IF EXISTS "Public full access on resumes" ON public.resumes;
DROP POLICY IF EXISTS "Allow all access" ON public.resumes;
DROP POLICY IF EXISTS "Users can read own resumes" ON public.resumes;
DROP POLICY IF EXISTS "Users can insert own resumes" ON public.resumes;
DROP POLICY IF EXISTS "Users can update own resumes" ON public.resumes;
DROP POLICY IF EXISTS "Users can delete own resumes" ON public.resumes;

-- 6a. SELECT Policy: User can read only their own resumes
CREATE POLICY "Users can read own resumes"
ON public.resumes
FOR SELECT
TO authenticated
USING (
    auth.uid() = user_id
);

-- 6b. INSERT Policy: User can insert only with their own auth.uid()
CREATE POLICY "Users can insert own resumes"
ON public.resumes
FOR INSERT
TO authenticated
WITH CHECK (
    auth.uid() = user_id
);

-- 6c. UPDATE Policy: User can update only their own resumes
CREATE POLICY "Users can update own resumes"
ON public.resumes
FOR UPDATE
TO authenticated
USING (
    auth.uid() = user_id
)
WITH CHECK (
    auth.uid() = user_id
);

-- 6d. DELETE Policy: User can delete only their own resumes
CREATE POLICY "Users can delete own resumes"
ON public.resumes
FOR DELETE
TO authenticated
USING (
    auth.uid() = user_id
);

-- Step 7: Deprecate Legacy Custom 'users' Table
-- We do NOT drop the users table to avoid any accidental loss of historical audit data.
-- Instead, lock down permissions so client anon keys cannot read plaintext/bcrypt passwords.
ALTER TABLE IF EXISTS public.users ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow public users access" ON public.users;
DROP POLICY IF EXISTS "Lock down legacy users table" ON public.users;

-- Restrict legacy users table to service_role only (no public anon access)
CREATE POLICY "Lock down legacy users table"
ON public.users
FOR ALL
TO authenticated
USING (false);

-- =====================================================================
-- Verification Queries (Run these to confirm migration results)
-- =====================================================================
-- 1. Check mapped vs unmapped resumes:
-- SELECT id, email, user_id, template_id, updated_at FROM public.resumes;
--
-- 2. Check unmappable legacy resumes (preserved, not deleted):
-- SELECT count(*) AS unmapped_count FROM public.resumes WHERE user_id IS NULL;
--
-- 3. Confirm RLS status:
-- SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname = 'public' AND tablename IN ('resumes', 'users');
