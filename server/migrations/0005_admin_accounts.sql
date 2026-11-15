-- Admin panel accounts (python -m app.cli create-admin <email>). Passwords are scrypt hashes.
CREATE TABLE IF NOT EXISTS public.admin_users (
    email          text PRIMARY KEY,          -- stored lowercase
    password_hash  text NOT NULL,
    created_at     timestamptz NOT NULL DEFAULT now()
);

-- Roles: viewer reads, editor also adds and deletes jobs, admin also manages users and AI costs.
-- Accounts that existed before roles were admins, so the default keeps them admins.
-- Users created by an admin get a one-time password and must change it at first sign-in.
ALTER TABLE public.admin_users ADD COLUMN IF NOT EXISTS role text NOT NULL DEFAULT 'admin'
    CHECK (role IN ('viewer', 'editor', 'admin'));
ALTER TABLE public.admin_users ADD COLUMN IF NOT EXISTS must_change_password boolean NOT NULL DEFAULT false;
ALTER TABLE public.admin_users ADD COLUMN IF NOT EXISTS created_by text;  -- the admin who created this user

-- Signed-in sessions. Only a SHA-256 of the cookie token is kept; deleting a row signs that session out.
CREATE TABLE IF NOT EXISTS public.admin_sessions (
    token_hash  text PRIMARY KEY,
    email       text NOT NULL REFERENCES public.admin_users (email) ON DELETE CASCADE,
    expires_at  timestamptz NOT NULL
);
