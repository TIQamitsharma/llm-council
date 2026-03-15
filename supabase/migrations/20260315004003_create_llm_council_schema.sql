/*
  # LLM Council Full Schema

  ## Overview
  Creates the complete database schema for the LLM Council multi-user app.

  ## New Tables

  ### 1. profiles
  - `id` (uuid, pk, references auth.users)
  - `email` (text)
  - `display_name` (text, nullable)
  - `created_at` (timestamptz)
  - `updated_at` (timestamptz)

  ### 2. user_api_keys
  - `id` (uuid, pk)
  - `user_id` (uuid, references auth.users)
  - `provider` (text) - e.g. 'openrouter', 'anthropic', 'openai', 'google', 'xai'
  - `encrypted_key` (text) - key encrypted with pgcrypto using a server-side secret
  - `created_at` (timestamptz)
  - `updated_at` (timestamptz)
  - Unique constraint on (user_id, provider)

  ### 3. user_council_config
  - `id` (uuid, pk)
  - `user_id` (uuid, references auth.users, unique)
  - `council_models` (text[]) - list of model identifiers
  - `chairman_model` (text)
  - `created_at` (timestamptz)
  - `updated_at` (timestamptz)

  ### 4. conversations
  - `id` (uuid, pk)
  - `user_id` (uuid, references auth.users)
  - `title` (text)
  - `created_at` (timestamptz)
  - `updated_at` (timestamptz)

  ### 5. messages
  - `id` (uuid, pk)
  - `conversation_id` (uuid, references conversations)
  - `user_id` (uuid, references auth.users)
  - `role` (text) - 'user' or 'assistant'
  - `content` (text, nullable) - user message content
  - `stage1` (jsonb, nullable) - array of individual model responses
  - `stage2` (jsonb, nullable) - array of peer rankings
  - `stage3` (jsonb, nullable) - final synthesized answer
  - `created_at` (timestamptz)
  - `message_index` (integer) - ordering within conversation

  ## Security
  - RLS enabled on all tables
  - Users can only access their own data
  - All policies check auth.uid() = user_id

  ## Functions
  - `handle_new_user()` trigger: automatically creates a profile when a new user signs up
  - `encrypt_api_key(key text)` - encrypts a key using pgcrypto
  - `decrypt_api_key(encrypted text)` - decrypts a key using pgcrypto
*/

-- Enable pgcrypto for encryption
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ============================================================
-- PROFILES TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS profiles (
  id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email text NOT NULL DEFAULT '',
  display_name text,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own profile"
  ON profiles FOR SELECT
  TO authenticated
  USING (auth.uid() = id);

CREATE POLICY "Users can insert own profile"
  ON profiles FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = id);

CREATE POLICY "Users can update own profile"
  ON profiles FOR UPDATE
  TO authenticated
  USING (auth.uid() = id)
  WITH CHECK (auth.uid() = id);

-- Trigger to auto-create profile on signup
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS trigger AS $$
BEGIN
  INSERT INTO profiles (id, email)
  VALUES (NEW.id, NEW.email)
  ON CONFLICT (id) DO NOTHING;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION handle_new_user();

-- ============================================================
-- USER_API_KEYS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS user_api_keys (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  provider text NOT NULL,
  encrypted_key text NOT NULL,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  UNIQUE(user_id, provider)
);

ALTER TABLE user_api_keys ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own api keys"
  ON user_api_keys FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own api keys"
  ON user_api_keys FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own api keys"
  ON user_api_keys FOR UPDATE
  TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own api keys"
  ON user_api_keys FOR DELETE
  TO authenticated
  USING (auth.uid() = user_id);

-- ============================================================
-- USER_COUNCIL_CONFIG TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS user_council_config (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE UNIQUE,
  council_models text[] NOT NULL DEFAULT ARRAY[
    'anthropic/claude-sonnet-4-5',
    'openai/gpt-4o',
    'google/gemini-2.5-pro-preview',
    'x-ai/grok-3'
  ],
  chairman_model text NOT NULL DEFAULT 'google/gemini-2.5-pro-preview',
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

ALTER TABLE user_council_config ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own council config"
  ON user_council_config FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own council config"
  ON user_council_config FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own council config"
  ON user_council_config FOR UPDATE
  TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own council config"
  ON user_council_config FOR DELETE
  TO authenticated
  USING (auth.uid() = user_id);

-- ============================================================
-- CONVERSATIONS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS conversations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  title text NOT NULL DEFAULT 'New Conversation',
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS conversations_user_id_idx ON conversations(user_id);
CREATE INDEX IF NOT EXISTS conversations_updated_at_idx ON conversations(updated_at DESC);

ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own conversations"
  ON conversations FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own conversations"
  ON conversations FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own conversations"
  ON conversations FOR UPDATE
  TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own conversations"
  ON conversations FOR DELETE
  TO authenticated
  USING (auth.uid() = user_id);

-- ============================================================
-- MESSAGES TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS messages (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id uuid NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  role text NOT NULL DEFAULT 'user',
  content text,
  stage1 jsonb,
  stage2 jsonb,
  stage3 jsonb,
  message_index integer NOT NULL DEFAULT 0,
  created_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS messages_conversation_id_idx ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS messages_user_id_idx ON messages(user_id);
CREATE INDEX IF NOT EXISTS messages_message_index_idx ON messages(conversation_id, message_index);

ALTER TABLE messages ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own messages"
  ON messages FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own messages"
  ON messages FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own messages"
  ON messages FOR UPDATE
  TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own messages"
  ON messages FOR DELETE
  TO authenticated
  USING (auth.uid() = user_id);

-- ============================================================
-- ENCRYPTION HELPER FUNCTIONS
-- These use pgcrypto's symmetric encryption with a passphrase
-- stored as a DB setting. The actual secret is set via app config.
-- ============================================================

CREATE OR REPLACE FUNCTION encrypt_api_key(key_value text, secret text)
RETURNS text AS $$
BEGIN
  RETURN encode(
    pgp_sym_encrypt(key_value, secret),
    'base64'
  );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION decrypt_api_key(encrypted_value text, secret text)
RETURNS text AS $$
BEGIN
  RETURN pgp_sym_decrypt(
    decode(encrypted_value, 'base64'),
    secret
  );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
