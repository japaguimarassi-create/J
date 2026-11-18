CREATE TABLE IF NOT EXISTS klod_conversations (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES klod_users(id) ON DELETE CASCADE,
    title VARCHAR(160) NOT NULL DEFAULT 'Nova conversa',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS klod_conversations_user_updated_idx
    ON klod_conversations (user_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS klod_messages (
    id UUID PRIMARY KEY,
    conversation_id UUID NOT NULL REFERENCES klod_conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL CHECK (length(content) <= 12000),
    message_order BIGINT GENERATED ALWAYS AS IDENTITY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

ALTER TABLE klod_messages
    ADD COLUMN IF NOT EXISTS message_order BIGINT GENERATED ALWAYS AS IDENTITY;

ALTER TABLE klod_messages
    ALTER COLUMN created_at SET DEFAULT clock_timestamp();

CREATE INDEX IF NOT EXISTS klod_messages_conversation_created_idx
    ON klod_messages (conversation_id, message_order ASC);

CREATE TABLE IF NOT EXISTS klod_projects (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES klod_users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    description VARCHAR(1000) NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, name)
);

CREATE INDEX IF NOT EXISTS klod_projects_user_updated_idx
    ON klod_projects (user_id, updated_at DESC);
