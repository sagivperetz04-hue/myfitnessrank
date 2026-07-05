import os
import requests

_BASE = os.environ.get("CLOSE_POWERLIFTING_URL", "https://closepowerlifting.com")
_LEADERBOARDS_URL = os.environ.get("LEADERBOARDS_URL", "http://leaderboards:5000")

_SEX_MAP = {"M": "men", "F": "women"}
_SORT_MAP = {
    "squat": "by-squat",
    "bench": "by-bench",
    "deadlift": "by-deadlift",
    "total": "by-total",
}


def get_top_lifters(sex: str, weight_class: str, lift: str) -> list:
    url = f"{_BASE}/api/rankings/filter/raw/{_SEX_MAP[sex]}/{weight_class}"
    resp = requests.get(
        url,
        params={"sort": _SORT_MAP[lift], "per_page": 10, "units": "kg"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json().get("data", [])


def submit_bests(bearer: str, sex: str, bodyweight_kg: float, bests: dict) -> None:
    """Forward a user's best lifts to the leaderboards service.

    Identity and dedup are owned by the leaderboards service: it takes the
    user from the bearer token and upserts one row per (sex, user) keeping
    the best of each lift, so resubmits can never create duplicates.
    """
    resp = requests.post(
        f"{_LEADERBOARDS_URL}/api/leaderboards/submit",
        json={
            "sex": sex,
            "squat_kg": bests["squat"],
            "bench_kg": bests["bench"],
            "deadlift_kg": bests["deadlift"],
            "bodyweight_kg": bodyweight_kg,
        },
        headers={"Authorization": bearer},
        timeout=5,
    )
    resp.raise_for_status()
