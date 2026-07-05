"""Sort-key whitelisting and limit clamping — no database required."""

from services.board import (
    MAX_LIMIT,
    SORT_COLUMNS,
    WORLD_RECORDS_KG,
    WR_MARGIN_KG,
    clamp_limit,
    lift_cap,
    sort_column,
)


class TestSortColumn:
    def test_known_keys_map_to_columns(self):
        assert sort_column("total") == "total_kg"
        assert sort_column("ratio") == "bw_ratio"
        assert sort_column("bench") == "bench_kg"
        assert sort_column("deadlift") == "deadlift_kg"
        assert sort_column("squat") == "squat_kg"

    def test_unknown_key_falls_back_to_total(self):
        # An attacker-supplied sort can never reach SQL as-is.
        assert sort_column("bodyweight_kg; DROP TABLE") == "total_kg"
        assert sort_column("") == "total_kg"

    def test_every_column_is_a_real_table_column(self):
        for col in SORT_COLUMNS.values():
            assert col.replace("_", "").isalnum()


class TestClampLimit:
    def test_caps_at_max(self):
        assert clamp_limit(10_000) == MAX_LIMIT

    def test_floors_at_one(self):
        assert clamp_limit(0) == 1
        assert clamp_limit(-5) == 1

    def test_passes_through_valid(self):
        assert clamp_limit(50) == 50

    def test_invalid_defaults_to_max(self):
        assert clamp_limit("nope") == MAX_LIMIT


class TestLiftCap:
    def test_covers_the_three_competition_lifts(self):
        assert set(WORLD_RECORDS_KG) == {"squat_kg", "bench_kg", "deadlift_kg"}

    def test_cap_is_world_record_plus_margin(self):
        for field, record in WORLD_RECORDS_KG.items():
            assert lift_cap(field) == record + WR_MARGIN_KG

    def test_record_beating_submission_is_over_cap(self):
        # A squat past the world record + margin must fall outside the ceiling.
        assert 600 > lift_cap("squat_kg")

    def test_legitimate_elite_lift_is_within_cap(self):
        assert 500 <= lift_cap("squat_kg")
        assert clamp_limit(None) == MAX_LIMIT
