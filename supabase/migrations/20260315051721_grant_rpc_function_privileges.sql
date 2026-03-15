/*
  # Grant RPC Function Privileges

  ## Overview
  Ensures encrypt_api_key and decrypt_api_key functions have proper execute
  grants for all relevant roles so the backend service role can call them
  via PostgREST RPC endpoint.

  ## Changes
  - Grants EXECUTE on encrypt_api_key and decrypt_api_key to service_role and authenticated
*/

GRANT EXECUTE ON FUNCTION encrypt_api_key(text, text) TO service_role;
GRANT EXECUTE ON FUNCTION decrypt_api_key(text, text) TO service_role;
GRANT EXECUTE ON FUNCTION encrypt_api_key(text, text) TO authenticated;
GRANT EXECUTE ON FUNCTION decrypt_api_key(text, text) TO authenticated;
