ALTER TABLE klod_users
    ALTER COLUMN google_sub DROP NOT NULL;

ALTER TABLE klod_users
    ADD COLUMN IF NOT EXISTS password_hash TEXT,
    ADD COLUMN IF NOT EXISTS email_verified BOOLEAN NOT NULL DEFAULT FALSE;

UPDATE klod_users
SET email_verified = TRUE
WHERE google_sub IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS klod_users_email_lower_unique
    ON klod_users (lower(email));

ALTER TABLE klod_platform_state
    ADD COLUMN IF NOT EXISTS owner_user_id UUID REFERENCES klod_users(id) ON DELETE SET NULL;

UPDATE klod_platform_state AS state
SET owner_user_id = users.id
FROM klod_users AS users
WHERE state.owner_user_id IS NULL
  AND state.owner_google_sub IS NOT NULL
  AND users.google_sub = state.owner_google_sub;

CREATE TABLE IF NOT EXISTS klod_email_tokens (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES klod_users(id) ON DELETE CASCADE,
    token_hash CHAR(64) NOT NULL UNIQUE,
    purpose TEXT NOT NULL CHECK (purpose IN ('verify_email', 'reset_password')),
    expires_at TIMESTAMPTZ NOT NULL,
    consumed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS klod_email_tokens_user_purpose_idx
    ON klod_email_tokens (user_id, purpose, created_at DESC);

CREATE INDEX IF NOT EXISTS klod_email_tokens_expiry_idx
    ON klod_email_tokens (expires_at);

CREATE TABLE IF NOT EXISTS klod_auth_attempts (
    attempt_key CHAR(64) PRIMARY KEY,
    failed_count INTEGER NOT NULL DEFAULT 0 CHECK (failed_count >= 0),
    first_failed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_failed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    locked_until TIMESTAMPTZ
);
