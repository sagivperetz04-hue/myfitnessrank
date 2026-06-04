"""Unit tests for ranking logic — no database required."""
import pytest
from services.ranking import assign_tier, assign_weight_class, calculate_1rm


class TestCalculate1RM:
    def test_epley_formula(self):
        assert calculate_1rm(100, 5) == 116.7

    def test_single_rep(self):
        assert calculate_1rm(100, 1) == 103.3

    def test_rounds_to_one_decimal(self):
        assert calculate_1rm(75, 8) == round(75 * (1 + 8 / 30), 1)

    def test_max_reps(self):
        assert calculate_1rm(60, 20) == round(60 * (1 + 20 / 30), 1)


class TestAssignWeightClass:
    def test_male_exact_class_boundary(self):
        assert assign_weight_class(59, "M") == 59

    def test_male_just_above_boundary(self):
        assert assign_weight_class(59.1, "M") == 66

    def test_male_mid_range(self):
        assert assign_weight_class(85, "M") == 93

    def test_male_heaviest_class(self):
        assert assign_weight_class(120, "M") == 120

    def test_male_open_class(self):
        assert assign_weight_class(121, "M") == 999

    def test_female_exact_boundary(self):
        assert assign_weight_class(63, "F") == 63

    def test_female_open_class(self):
        assert assign_weight_class(85, "F") == 999


class TestAssignTier:
    def test_elite_at_99(self):
        assert assign_tier(99) == "Elite"

    def test_platinum_at_95(self):
        assert assign_tier(95) == "Platinum"

    def test_gold_at_90(self):
        assert assign_tier(90) == "Gold"

    def test_silver_at_75(self):
        assert assign_tier(75) == "Silver"

    def test_bronze_at_50(self):
        assert assign_tier(50) == "Bronze"

    def test_copper_at_0(self):
        assert assign_tier(0) == "Copper"

    def test_just_below_platinum(self):
        assert assign_tier(94) == "Gold"

    def test_just_below_gold(self):
        assert assign_tier(89) == "Silver"

    def test_just_below_silver(self):
        assert assign_tier(74) == "Bronze"

    def test_just_below_bronze(self):
        assert assign_tier(49) == "Copper"
