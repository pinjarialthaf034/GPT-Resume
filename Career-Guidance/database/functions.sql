-- CareerCompass AI — Database Functions and Triggers
-- Execute after schema.sql

-- 1. Function to safely increment profile version
-- This is used to invalidate AI caches when a student's profile changes significantly.
CREATE OR REPLACE FUNCTION increment_profile_version(profile_id UUID)
RETURNS void AS $$
BEGIN
    UPDATE profiles
    SET profile_version = profile_version + 1,
        updated_at = NOW()
    WHERE id = profile_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
-- SECURITY DEFINER allows this function to bypass RLS if called by service role

-- 2. Trigger to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Attach to profiles
CREATE TRIGGER update_profiles_updated_at
    BEFORE UPDATE ON profiles
    FOR EACH ROW
    EXECUTE PROCEDURE update_updated_at_column();

-- 3. Attach to chat_sessions
CREATE TRIGGER update_chat_sessions_updated_at
    BEFORE UPDATE ON chat_sessions
    FOR EACH ROW
    EXECUTE PROCEDURE update_updated_at_column();
