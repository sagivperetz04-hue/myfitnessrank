CREATE TABLE IF NOT EXISTS leaderboard_entries (
    id            BIGSERIAL PRIMARY KEY,
    sex           CHAR(1) NOT NULL CHECK (sex IN ('M', 'F')),
    source        TEXT    NOT NULL CHECK (source IN ('seed', 'user')),
    user_id       BIGINT,                      -- NULL for seed (dataset) rows
    name_enc      TEXT    NOT NULL,            -- Fernet ciphertext of the lifter name
    bodyweight_kg NUMERIC(6,2) NOT NULL CHECK (bodyweight_kg > 0),
    squat_kg      NUMERIC(6,2) NOT NULL DEFAULT 0,
    bench_kg      NUMERIC(6,2) NOT NULL DEFAULT 0,
    deadlift_kg   NUMERIC(6,2) NOT NULL DEFAULT 0,
    total_kg      NUMERIC(7,2) NOT NULL,
    bw_ratio      NUMERIC(6,4) GENERATED ALWAYS AS (total_kg / bodyweight_kg) STORED,
    updated_at    TIMESTAMPTZ DEFAULT NOW()
);

-- One leaderboard row per user per sex. Partial unique index is also the
-- ON CONFLICT target for the overwrite-when-better upsert in services/board.py.
CREATE UNIQUE INDEX IF NOT EXISTS lb_user_uniq
    ON leaderboard_entries (sex, user_id) WHERE source = 'user';

-- One index per sortable metric; each leaderboard read filters by sex then
-- orders by one of these columns descending.
CREATE INDEX IF NOT EXISTS lb_total_idx    ON leaderboard_entries (sex, total_kg DESC);
CREATE INDEX IF NOT EXISTS lb_ratio_idx    ON leaderboard_entries (sex, bw_ratio DESC);
CREATE INDEX IF NOT EXISTS lb_bench_idx    ON leaderboard_entries (sex, bench_kg DESC);
CREATE INDEX IF NOT EXISTS lb_deadlift_idx ON leaderboard_entries (sex, deadlift_kg DESC);
CREATE INDEX IF NOT EXISTS lb_squat_idx    ON leaderboard_entries (sex, squat_kg DESC);
