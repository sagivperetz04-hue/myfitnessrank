CREATE TABLE IF NOT EXISTS accounts (
    id            BIGSERIAL PRIMARY KEY,
    email         TEXT UNIQUE NOT NULL CHECK (email <> ''),
    username      TEXT NOT NULL CHECK (username <> ''),
    password_hash TEXT NOT NULL,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

-- Usernames are unique case-insensitively but stored as the user typed them,
-- so "Sagiv" and "sagiv" can't both exist. This functional index is the gate.
CREATE UNIQUE INDEX IF NOT EXISTS accounts_username_lower_idx ON accounts (LOWER(username));

-- Logins look the account up by email; the unique constraint already covers it,
-- but make the lookup contract explicit at the app layer.
CREATE INDEX IF NOT EXISTS accounts_email_idx ON accounts (email);
