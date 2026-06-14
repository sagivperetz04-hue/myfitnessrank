CREATE TABLE IF NOT EXISTS accounts (
    id            BIGSERIAL PRIMARY KEY,
    email         TEXT UNIQUE NOT NULL CHECK (email <> ''),
    username      TEXT UNIQUE NOT NULL CHECK (username <> ''),
    password_hash TEXT NOT NULL,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS accounts_email_idx ON accounts (email);
