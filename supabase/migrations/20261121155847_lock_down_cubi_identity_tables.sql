ALTER TABLE public.identity_users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.identity_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.identity_login_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.identity_password_reset_tokens ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.identity_users, public.identity_sessions, public.identity_login_attempts, public.identity_password_reset_tokens FROM anon, authenticated;
REVOKE ALL ON SEQUENCE public.identity_login_attempts_attempt_id_seq FROM anon, authenticated;
