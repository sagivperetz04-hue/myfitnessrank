CREATE TABLE IF NOT EXISTS accounts (
    id            BIGSERIAL PRIMARY KEY,
    email         TEXT UNIQUE NOT NULL CHECK (email <> ''),
    username      TEXT NOT NULL CHECK (username <> ''),
    password_hash TEXT NOT NULL,
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    last_login_at TIMESTAMPTZ
);

-- Usernames are unique case-insensitively but stored as the user typed them.
CREATE UNIQUE INDEX IF NOT EXISTS accounts_username_lower_idx ON accounts (LOWER(username));

CREATE INDEX IF NOT EXISTS accounts_email_idx ON accounts (email);
