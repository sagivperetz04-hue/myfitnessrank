CREATE TABLE IF NOT EXISTS global_standards (
    lift             TEXT    NOT NULL CHECK (lift IN ('squat', 'bench', 'deadlift', 'total')),
    sex              TEXT    NOT NULL CHECK (sex IN ('M', 'F')),
    weight_class_kg  NUMERIC NOT NULL CHECK (weight_class_kg > 0),
    percentile       INTEGER NOT NULL CHECK (percentile BETWEEN 0 AND 100),
    min_kg           NUMERIC NOT NULL CHECK (min_kg >= 0),
    track            TEXT    NOT NULL CHECK (track IN ('world_avg', 'competition')),
    PRIMARY KEY (lift, sex, weight_class_kg, percentile, track)
);

CREATE TABLE IF NOT EXISTS users (
    id         SERIAL PRIMARY KEY,
    username   TEXT UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS workout_logs (
    id                     SERIAL PRIMARY KEY,
    user_id                INT     NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    exercise               TEXT    NOT NULL CHECK (exercise IN ('squat', 'bench', 'deadlift', 'total')),
    weight_kg              NUMERIC NOT NULL CHECK (weight_kg > 0),
    reps                   INT     NOT NULL CHECK (reps > 0),
    one_rm_kg              NUMERIC NOT NULL CHECK (one_rm_kg > 0),
    tier                   TEXT    NOT NULL CHECK (tier IN ('Elite', 'Platinum', 'Gold', 'Silver', 'Bronze', 'Copper')),
    world_avg_percentile   INTEGER          CHECK (world_avg_percentile BETWEEN 0 AND 100),
    competition_percentile INTEGER          CHECK (competition_percentile BETWEEN 0 AND 100),
    logged_at              TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS workout_logs_user_id_idx ON workout_logs (user_id);
