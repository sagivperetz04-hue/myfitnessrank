CREATE TABLE IF NOT EXISTS global_standards (
    lift             TEXT    NOT NULL,
    sex              TEXT    NOT NULL,
    weight_class_kg  NUMERIC NOT NULL,
    percentile       INTEGER NOT NULL,
    min_kg           NUMERIC NOT NULL,
    track            TEXT    NOT NULL,
    PRIMARY KEY (lift, sex, weight_class_kg, percentile, track)
);

CREATE TABLE IF NOT EXISTS users (
    id         SERIAL PRIMARY KEY,
    username   TEXT UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS workout_logs (
    id                     SERIAL PRIMARY KEY,
    user_id                INT REFERENCES users(id),
    exercise               TEXT    NOT NULL,
    weight_kg              NUMERIC NOT NULL,
    reps                   INT     NOT NULL,
    one_rm_kg              NUMERIC NOT NULL,
    tier                   TEXT    NOT NULL,
    world_avg_percentile   INTEGER,
    competition_percentile INTEGER,
    logged_at              TIMESTAMPTZ DEFAULT NOW()
);
