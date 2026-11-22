CREATE TABLE IF NOT EXISTS public.identity_users (
  user_id TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  email TEXT NOT NULL,
  username TEXT,
  display_name TEXT NOT NULL DEFAULT '',
  roles_json TEXT NOT NULL,
  password_hash TEXT NOT NULL,
  active BOOLEAN NOT NULL DEFAULT TRUE,
  locked_at TIMESTAMPTZ,
  expires_at TIMESTAMPTZ,
  must_change_password BOOLEAN NOT NULL DEFAULT FALSE,
  last_login_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  password_changed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS identity_users_email_unique ON public.identity_users (lower(email));
CREATE UNIQUE INDEX IF NOT EXISTS identity_users_username_unique ON public.identity_users (lower(username)) WHERE username IS NOT NULL;
CREATE TABLE IF NOT EXISTS public.identity_sessions (
  token_hash TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES public.identity_users(user_id) ON DELETE CASCADE,
  tenant_id TEXT NOT NULL,
  roles_json TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL,
  last_seen_at TIMESTAMPTZ NOT NULL,
  expires_at TIMESTAMPTZ NOT NULL,
  revoked_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS identity_sessions_user ON public.identity_sessions(user_id);
CREATE INDEX IF NOT EXISTS identity_sessions_expiry ON public.identity_sessions(expires_at);
CREATE TABLE IF NOT EXISTS public.identity_login_attempts (
  attempt_id BIGSERIAL PRIMARY KEY,
  email TEXT NOT NULL,
  tenant_id TEXT,
  ip_hash TEXT NOT NULL DEFAULT '',
  attempted_at TIMESTAMPTZ NOT NULL,
  succeeded BOOLEAN NOT NULL
);
CREATE INDEX IF NOT EXISTS identity_attempts_email ON public.identity_login_attempts(email, attempted_at);
CREATE INDEX IF NOT EXISTS identity_attempts_ip ON public.identity_login_attempts(ip_hash, attempted_at);
CREATE TABLE IF NOT EXISTS public.identity_password_reset_tokens (
  token_hash TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES public.identity_users(user_id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at TIMESTAMPTZ NOT NULL,
  consumed_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS identity_password_reset_expiry ON public.identity_password_reset_tokens(expires_at);
