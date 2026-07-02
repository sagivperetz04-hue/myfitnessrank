"""Integration tests for all API routes against a real Postgres database."""

import app as app_module

VALID = {
    "username": "testuser",
    "exercise": "squat",
    "weight_kg": 100,
    "reps": 5,
    "bodyweight_kg": 85,
    "sex": "M",
}

VALID_TIERS = {"Elite", "Platinum", "Gold", "Silver", "Bronze", "Copper"}


# ── /health ───────────────────────────────────────────────────────────────────


class TestHealth:
    def test_returns_200_and_ok(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.get_json()["status"] == "ok"

    def test_live_returns_200_without_db(self, client):
        r = client.get("/health/live")
        assert r.status_code == 200
        assert r.get_json()["status"] == "ok"


# ── POST /api/rank ────────────────────────────────────────────────────────────


class TestRankHappyPath:
    def test_returns_200(self, client):
        assert client.post("/api/rank", json=VALID).status_code == 200

    def test_response_shape(self, client):
        data = client.post("/api/rank", json=VALID).get_json()
        assert {
            "one_rm_kg",
            "weight_class_kg",
            "competition",
            "world_avg",
        } <= data.keys()
        assert {"percentile", "tier"} <= data["competition"].keys()
        assert {"percentile", "tier"} <= data["world_avg"].keys()

    def test_1rm_calculation(self, client):
        # 100kg × (1 + 5/30) = 116.666… → rounded to 116.7
        data = client.post("/api/rank", json=VALID).get_json()
        assert data["one_rm_kg"] == 116.7

    def test_1rm_at_one_rep_equals_weight(self, client):
        data = client.post(
            "/api/rank", json={**VALID, "weight_kg": 200, "reps": 1}
        ).get_json()
        assert data["one_rm_kg"] == 200

    def test_weight_class_for_85kg_male(self, client):
        data = client.post("/api/rank", json=VALID).get_json()
        assert data["weight_class_kg"] == 93

    def test_weight_class_for_female(self, client):
        data = client.post(
            "/api/rank", json={**VALID, "sex": "F", "bodyweight_kg": 60}
        ).get_json()
        assert data["weight_class_kg"] == 63

    def test_tiers_are_valid(self, client):
        data = client.post("/api/rank", json=VALID).get_json()
        assert data["competition"]["tier"] in VALID_TIERS
        assert data["world_avg"]["tier"] in VALID_TIERS

    def test_percentiles_in_range(self, client):
        data = client.post("/api/rank", json=VALID).get_json()
        assert 0 <= data["competition"]["percentile"] <= 100
        assert 0 <= data["world_avg"]["percentile"] <= 100

    def test_same_username_twice_is_idempotent(self, client):
        r1 = client.post("/api/rank", json=VALID)
        r2 = client.post("/api/rank", json=VALID)
        assert r1.status_code == 200
        assert r2.status_code == 200

    def test_all_exercises_accepted(self, client):
        for exercise in ("squat", "bench", "deadlift", "total"):
            r = client.post("/api/rank", json={**VALID, "exercise": exercise})
            assert r.status_code == 200, f"exercise={exercise} failed"

    def test_lowercase_sex_accepted(self, client):
        r = client.post("/api/rank", json={**VALID, "sex": "m"})
        assert r.status_code == 200


class TestRankValidation:
    def test_missing_field_returns_400(self, client):
        for field in VALID:
            payload = {k: v for k, v in VALID.items() if k != field}
            r = client.post("/api/rank", json=payload)
            assert r.status_code == 400, f"expected 400 when '{field}' is missing"

    def test_empty_username_returns_400(self, client):
        assert (
            client.post("/api/rank", json={**VALID, "username": ""}).status_code == 400
        )

    def test_whitespace_username_returns_400(self, client):
        assert (
            client.post("/api/rank", json={**VALID, "username": "   "}).status_code
            == 400
        )

    def test_invalid_sex_returns_400(self, client):
        assert client.post("/api/rank", json={**VALID, "sex": "X"}).status_code == 400

    def test_invalid_exercise_returns_400(self, client):
        assert (
            client.post("/api/rank", json={**VALID, "exercise": "curls"}).status_code
            == 400
        )

    def test_reps_above_20_returns_400(self, client):
        assert client.post("/api/rank", json={**VALID, "reps": 21}).status_code == 400

    def test_reps_zero_returns_400(self, client):
        assert client.post("/api/rank", json={**VALID, "reps": 0}).status_code == 400

    def test_reps_negative_returns_400(self, client):
        assert client.post("/api/rank", json={**VALID, "reps": -1}).status_code == 400

    def test_weight_zero_returns_400(self, client):
        assert (
            client.post("/api/rank", json={**VALID, "weight_kg": 0}).status_code == 400
        )

    def test_weight_negative_returns_400(self, client):
        assert (
            client.post("/api/rank", json={**VALID, "weight_kg": -10}).status_code
            == 400
        )

    def test_non_numeric_weight_returns_400(self, client):
        assert (
            client.post("/api/rank", json={**VALID, "weight_kg": "heavy"}).status_code
            == 400
        )

    def test_non_numeric_reps_returns_400(self, client):
        assert (
            client.post("/api/rank", json={**VALID, "reps": "five"}).status_code == 400
        )

    def test_empty_body_returns_400(self, client):
        assert client.post("/api/rank", json={}).status_code == 400

    def test_weight_above_world_record_cap_returns_400(self, client):
        r = client.post(
            "/api/rank", json={**VALID, "exercise": "deadlift", "weight_kg": 600}
        )
        assert r.status_code == 400
        assert "world record" in r.get_json()["error"]

    def test_weight_at_world_record_cap_accepted(self, client):
        r = client.post(
            "/api/rank",
            json={**VALID, "exercise": "deadlift", "weight_kg": 507, "reps": 1},
        )
        assert r.status_code == 200

    def test_cap_is_per_exercise(self, client):
        # 400 kg is a legal deadlift but an impossible bench
        assert (
            client.post(
                "/api/rank",
                json={**VALID, "exercise": "bench", "weight_kg": 400},
            ).status_code
            == 400
        )
        assert (
            client.post(
                "/api/rank",
                json={**VALID, "exercise": "deadlift", "weight_kg": 400, "reps": 1},
            ).status_code
            == 200
        )


class TestRankLeaderboardSync:
    """Signed-in lifts are forwarded to the leaderboards service; guests are not."""

    AUTH = {"Authorization": "Bearer test-token"}

    def _capture(self, monkeypatch):
        calls = []
        monkeypatch.setattr(
            app_module,
            "submit_bests",
            lambda bearer, sex, bodyweight_kg, bests: calls.append(
                {
                    "bearer": bearer,
                    "sex": sex,
                    "bodyweight_kg": bodyweight_kg,
                    "bests": bests,
                }
            ),
        )
        return calls

    def _log(self, client, exercise, weight, headers=None):
        return client.post(
            "/api/rank",
            json={**VALID, "exercise": exercise, "weight_kg": weight},
            headers=headers or {},
        )

    def test_guest_lift_is_not_forwarded(self, client, monkeypatch):
        calls = self._capture(monkeypatch)
        assert self._log(client, "squat", 100).status_code == 200
        assert calls == []

    def test_incomplete_total_is_not_forwarded(self, client, monkeypatch):
        calls = self._capture(monkeypatch)
        assert self._log(client, "squat", 100, self.AUTH).status_code == 200
        assert self._log(client, "bench", 80, self.AUTH).status_code == 200
        assert calls == []

    def test_full_total_forwards_best_one_rms(self, client, monkeypatch):
        calls = self._capture(monkeypatch)
        self._log(client, "squat", 100, self.AUTH)  # 1RM 116.7
        self._log(client, "squat", 120, self.AUTH)  # 1RM 140.0 — the best
        self._log(client, "bench", 80, self.AUTH)  # 1RM 93.3
        self._log(client, "deadlift", 140, self.AUTH)  # 1RM 163.3 — completes the total
        assert len(calls) == 1
        call = calls[0]
        assert call["bearer"] == "Bearer test-token"
        assert call["sex"] == "M"
        assert call["bodyweight_kg"] == 85
        assert call["bests"] == {"squat": 140.0, "bench": 93.3, "deadlift": 163.3}

    def test_forwarding_failure_does_not_fail_rank(self, client, monkeypatch):
        def boom(*args, **kwargs):
            raise RuntimeError("leaderboards down")

        monkeypatch.setattr(app_module, "submit_bests", boom)
        self._log(client, "squat", 100, self.AUTH)
        self._log(client, "bench", 80, self.AUTH)
        r = self._log(client, "deadlift", 140, self.AUTH)
        assert r.status_code == 200


# ── GET /api/users/<username>/history ────────────────────────────────────────


class TestHistory:
    def test_unknown_user_returns_404(self, client):
        assert client.get("/api/users/nobody/history").status_code == 404

    def test_returns_log_after_rank(self, client):
        client.post("/api/rank", json=VALID)
        r = client.get(f"/api/users/{VALID['username']}/history")
        assert r.status_code == 200
        logs = r.get_json()["logs"]
        assert len(logs) == 1
        assert logs[0]["exercise"] == "squat"
        assert logs[0]["competition"]["tier"] in VALID_TIERS
        assert logs[0]["world_avg"]["tier"] in VALID_TIERS

    def test_log_contains_expected_fields(self, client):
        client.post("/api/rank", json=VALID)
        log = client.get(f"/api/users/{VALID['username']}/history").get_json()["logs"][
            0
        ]
        expected = {
            "exercise",
            "weight_kg",
            "reps",
            "one_rm_kg",
            "bodyweight_kg",
            "sex",
            "weight_class_kg",
            "competition",
            "world_avg",
            "logged_at",
        }
        assert expected <= log.keys()

    def test_log_values_match_input(self, client):
        client.post("/api/rank", json=VALID)
        log = client.get(f"/api/users/{VALID['username']}/history").get_json()["logs"][
            0
        ]
        assert log["weight_kg"] == float(VALID["weight_kg"])
        assert log["reps"] == VALID["reps"]
        assert log["bodyweight_kg"] == float(VALID["bodyweight_kg"])
        assert log["sex"] == VALID["sex"]

    def test_multiple_logs_ordered_newest_first(self, client):
        client.post("/api/rank", json={**VALID, "weight_kg": 80})
        client.post("/api/rank", json={**VALID, "weight_kg": 100})
        logs = client.get(f"/api/users/{VALID['username']}/history").get_json()["logs"]
        assert len(logs) == 2
        assert logs[0]["weight_kg"] == 100.0  # newest first

    def test_filter_by_exercise(self, client):
        client.post("/api/rank", json=VALID)
        client.post("/api/rank", json={**VALID, "exercise": "bench"})
        logs = client.get(
            f"/api/users/{VALID['username']}/history?exercise=squat"
        ).get_json()["logs"]
        assert len(logs) == 1
        assert logs[0]["exercise"] == "squat"

    def test_pagination_limit(self, client):
        for _ in range(5):
            client.post("/api/rank", json=VALID)
        logs = client.get(f"/api/users/{VALID['username']}/history?limit=2").get_json()[
            "logs"
        ]
        assert len(logs) == 2

    def test_pagination_offset(self, client):
        for w in (80, 90, 100):
            client.post("/api/rank", json={**VALID, "weight_kg": w})
        # newest first: 100, 90, 80 — offset 1 should give 90, 80
        logs = client.get(
            f"/api/users/{VALID['username']}/history?limit=2&offset=1"
        ).get_json()["logs"]
        assert logs[0]["weight_kg"] == 90.0

    def test_invalid_exercise_filter_returns_400(self, client):
        assert (
            client.get("/api/users/testuser/history?exercise=curls").status_code == 400
        )

    def test_limit_capped_at_100(self, client):
        client.post("/api/rank", json=VALID)
        r = client.get(f"/api/users/{VALID['username']}/history?limit=9999")
        assert r.status_code == 200  # capped silently, not an error


# ── GET /api/users/<username>/best ───────────────────────────────────────────


class TestBest:
    def test_unknown_user_returns_404(self, client):
        assert client.get("/api/users/nobody/best").status_code == 404

    def test_returns_best_per_lift(self, client):
        client.post("/api/rank", json={**VALID, "weight_kg": 80})
        client.post("/api/rank", json={**VALID, "weight_kg": 100})
        bests = client.get(f"/api/users/{VALID['username']}/best").get_json()["bests"]
        # 100 * (1 + 5/30) = 116.7
        assert bests["squat"]["one_rm_kg"] == 116.7

    def test_best_selects_highest_1rm_not_last(self, client):
        client.post("/api/rank", json={**VALID, "weight_kg": 100})
        client.post(
            "/api/rank", json={**VALID, "weight_kg": 80}
        )  # logged last but lower
        bests = client.get(f"/api/users/{VALID['username']}/best").get_json()["bests"]
        assert bests["squat"]["one_rm_kg"] == 116.7

    def test_best_across_multiple_exercises(self, client):
        client.post("/api/rank", json=VALID)
        client.post("/api/rank", json={**VALID, "exercise": "bench"})
        bests = client.get(f"/api/users/{VALID['username']}/best").get_json()["bests"]
        assert "squat" in bests
        assert "bench" in bests

    def test_empty_bests_for_user_with_no_logs(self, client):
        # Create a user via rank, then wipe only workout_logs manually
        client.post("/api/rank", json=VALID)
        import psycopg2

        conn = psycopg2.connect(
            "postgresql://postgres:testpass@localhost:5433/fitrank_test"
        )
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("TRUNCATE workout_logs")
        conn.close()
        bests = client.get(f"/api/users/{VALID['username']}/best").get_json()["bests"]
        assert bests == {}
