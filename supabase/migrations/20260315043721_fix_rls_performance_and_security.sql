/*
  # Fix RLS Performance and Security Issues

  ## Changes

  ### 1. RLS Policy Optimization (all tables)
  Replace `auth.uid()` with `(select auth.uid())` in all policies across:
  - profiles
  - user_api_keys
  - user_council_config
  - conversations
  - messages

  This prevents re-evaluation of auth functions per row, improving query performance.

  ### 2. Function Search Path Security
  Recreate handle_new_user, encrypt_api_key, decrypt_api_key with
  `SET search_path = public, pg_catalog` to prevent search_path injection attacks.

  ### 3. Index Cleanup
  Drop unused indexes that add write overhead without query benefit.
  The RLS policies themselves filter by user_id, making separate indexes
  on small early-stage tables premature.
*/

-- ============================================================
-- FIX: profiles RLS policies
-- ============================================================
DROP POLICY IF EXISTS "Users can view own profile" ON profiles;
DROP POLICY IF EXISTS "Users can insert own profile" ON profiles;
DROP POLICY IF EXISTS "Users can update own profile" ON profiles;

CREATE POLICY "Users can view own profile"
  ON profiles FOR SELECT
  TO authenticated
  USING ((select auth.uid()) = id);

CREATE POLICY "Users can insert own profile"
  ON profiles FOR INSERT
  TO authenticated
  WITH CHECK ((select auth.uid()) = id);

CREATE POLICY "Users can update own profile"
  ON profiles FOR UPDATE
  TO authenticated
  USING ((select auth.uid()) = id)
  WITH CHECK ((select auth.uid()) = id);

-- ============================================================
-- FIX: user_api_keys RLS policies
-- ============================================================
DROP POLICY IF EXISTS "Users can view own api keys" ON user_api_keys;
DROP POLICY IF EXISTS "Users can insert own api keys" ON user_api_keys;
DROP POLICY IF EXISTS "Users can update own api keys" ON user_api_keys;
DROP POLICY IF EXISTS "Users can delete own api keys" ON user_api_keys;

CREATE POLICY "Users can view own api keys"
  ON user_api_keys FOR SELECT
  TO authenticated
  USING ((select auth.uid()) = user_id);

CREATE POLICY "Users can insert own api keys"
  ON user_api_keys FOR INSERT
  TO authenticated
  WITH CHECK ((select auth.uid()) = user_id);

CREATE POLICY "Users can update own api keys"
  ON user_api_keys FOR UPDATE
  TO authenticated
  USING ((select auth.uid()) = user_id)
  WITH CHECK ((select auth.uid()) = user_id);

CREATE POLICY "Users can delete own api keys"
  ON user_api_keys FOR DELETE
  TO authenticated
  USING ((select auth.uid()) = user_id);

-- ============================================================
-- FIX: user_council_config RLS policies
-- ============================================================
DROP POLICY IF EXISTS "Users can view own council config" ON user_council_config;
DROP POLICY IF EXISTS "Users can insert own council config" ON user_council_config;
DROP POLICY IF EXISTS "Users can update own council config" ON user_council_config;
DROP POLICY IF EXISTS "Users can delete own council config" ON user_council_config;

CREATE POLICY "Users can view own council config"
  ON user_council_config FOR SELECT
  TO authenticated
  USING ((select auth.uid()) = user_id);

CREATE POLICY "Users can insert own council config"
  ON user_council_config FOR INSERT
  TO authenticated
  WITH CHECK ((select auth.uid()) = user_id);

CREATE POLICY "Users can update own council config"
  ON user_council_config FOR UPDATE
  TO authenticated
  USING ((select auth.uid()) = user_id)
  WITH CHECK ((select auth.uid()) = user_id);

CREATE POLICY "Users can delete own council config"
  ON user_council_config FOR DELETE
  TO authenticated
  USING ((select auth.uid()) = user_id);

-- ============================================================
-- FIX: conversations RLS policies
-- ============================================================
DROP POLICY IF EXISTS "Users can view own conversations" ON conversations;
DROP POLICY IF EXISTS "Users can insert own conversations" ON conversations;
DROP POLICY IF EXISTS "Users can update own conversations" ON conversations;
DROP POLICY IF EXISTS "Users can delete own conversations" ON conversations;

CREATE POLICY "Users can view own conversations"
  ON conversations FOR SELECT
  TO authenticated
  USING ((select auth.uid()) = user_id);

CREATE POLICY "Users can insert own conversations"
  ON conversations FOR INSERT
  TO authenticated
  WITH CHECK ((select auth.uid()) = user_id);

CREATE POLICY "Users can update own conversations"
  ON conversations FOR UPDATE
  TO authenticated
  USING ((select auth.uid()) = user_id)
  WITH CHECK ((select auth.uid()) = user_id);

CREATE POLICY "Users can delete own conversations"
  ON conversations FOR DELETE
  TO authenticated
  USING ((select auth.uid()) = user_id);

-- ============================================================
-- FIX: messages RLS policies
-- ============================================================
DROP POLICY IF EXISTS "Users can view own messages" ON messages;
DROP POLICY IF EXISTS "Users can insert own messages" ON messages;
DROP POLICY IF EXISTS "Users can update own messages" ON messages;
DROP POLICY IF EXISTS "Users can delete own messages" ON messages;

CREATE POLICY "Users can view own messages"
  ON messages FOR SELECT
  TO authenticated
  USING ((select auth.uid()) = user_id);

CREATE POLICY "Users can insert own messages"
  ON messages FOR INSERT
  TO authenticated
  WITH CHECK ((select auth.uid()) = user_id);

CREATE POLICY "Users can update own messages"
  ON messages FOR UPDATE
  TO authenticated
  USING ((select auth.uid()) = user_id)
  WITH CHECK ((select auth.uid()) = user_id);

CREATE POLICY "Users can delete own messages"
  ON messages FOR DELETE
  TO authenticated
  USING ((select auth.uid()) = user_id);

-- ============================================================
-- FIX: Function search_path security
-- ============================================================
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_catalog
AS $$
BEGIN
  INSERT INTO public.profiles (id, email)
  VALUES (NEW.id, NEW.email)
  ON CONFLICT (id) DO NOTHING;
  RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION encrypt_api_key(key_value text, secret text)
RETURNS text
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_catalog
AS $$
BEGIN
  RETURN encode(
    pgp_sym_encrypt(key_value, secret),
    'base64'
  );
END;
$$;

CREATE OR REPLACE FUNCTION decrypt_api_key(encrypted_value text, secret text)
RETURNS text
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_catalog
AS $$
BEGIN
  RETURN pgp_sym_decrypt(
    decode(encrypted_value, 'base64'),
    secret
  );
END;
$$;

-- ============================================================
-- FIX: Drop unused indexes
-- ============================================================
DROP INDEX IF EXISTS conversations_user_id_idx;
DROP INDEX IF EXISTS conversations_updated_at_idx;
DROP INDEX IF EXISTS messages_conversation_id_idx;
DROP INDEX IF EXISTS messages_user_id_idx;
DROP INDEX IF EXISTS messages_message_index_idx;
