-- Run this in the Supabase SQL Editor (Dashboard > SQL Editor > New Query)
-- Creates the profiles table and RLS policies for Auth & RBAC

CREATE TABLE IF NOT EXISTS public.profiles (
    id          UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    role        TEXT NOT NULL CHECK (role IN ('patient', 'admin', 'health_coach')),
    prevent_id  TEXT UNIQUE,
    display_name TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

-- Users can read their own profile
CREATE POLICY "users_read_own_profile"
    ON public.profiles FOR SELECT
    USING (auth.uid() = id);

-- Only service role can insert/update/delete (backend admin operations)
CREATE POLICY "service_role_manage_profiles"
    ON public.profiles FOR ALL
    USING (auth.role() = 'service_role');
