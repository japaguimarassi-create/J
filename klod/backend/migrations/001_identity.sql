CREATE TABLE IF NOT EXISTS klod_platform_state (
    id SMALLINT PRIMARY KEY CHECK (id = 1),
    owner_google_sub TEXT UNIQUE,
    initialized_at TIMESTAMPTZ
);

INSERT INTO klod_platform_state (id) VALUES (1)
ON CONFLICT (id) DO NOTHING;

CREATE TABLE IF NOT EXISTS klod_users (
    id UUID PRIMARY KEY,
    google_sub TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL,
    display_name TEXT NOT NULL DEFAULT '',
    picture_url TEXT NOT NULL DEFAULT '',
    role TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('user', 'admin')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS klod_sessions (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES klod_users(id) ON DELETE CASCADE,
    token_hash CHAR(64) NOT NULL UNIQUE,
    csrf_hash CHAR(64) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS klod_sessions_expiry_idx ON klod_sessions (expires_at);
CREATE INDEX IF NOT EXISTS klod_users_created_idx ON klod_users (created_at DESC);
