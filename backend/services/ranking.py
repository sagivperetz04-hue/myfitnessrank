import logging

log = logging.getLogger(__name__)

WEIGHT_CLASSES = {
    "M": [59, 66, 74, 83, 93, 105, 120, 999],
    "F": [47, 52, 57, 63, 69, 76, 84, 999],
}

# Descending order — first threshold the percentile meets wins
_TIER_MAP = [
    (99, "Elite"),
    (95, "Platinum"),
    (90, "Gold"),
    (75, "Silver"),
    (50, "Bronze"),
    (0, "Copper"),
]


def calculate_1rm(weight_kg: float, reps: int) -> float:
    return round(weight_kg * (1 + reps / 30), 1)


def assign_weight_class(bodyweight_kg: float, sex: str) -> int:
    for wc in WEIGHT_CLASSES[sex]:
        if bodyweight_kg <= wc:
            return wc
    return 999


def assign_tier(percentile: int) -> str:
    for threshold, tier in _TIER_MAP:
        if percentile >= threshold:
            return tier
    return "Copper"


def get_percentile(
    conn, lift: str, sex: str, bodyweight_kg: float, one_rm_kg: float, track: str
) -> int:
    weight_class = assign_weight_class(bodyweight_kg, sex)
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT percentile FROM global_standards
            WHERE lift = %s AND sex = %s AND weight_class_kg = %s
              AND track = %s AND min_kg <= %s
            ORDER BY percentile DESC
            LIMIT 1
            """,
            (lift, sex, weight_class, track, one_rm_kg),
        )
        row = cur.fetchone()
    if row is None:
        log.warning(
            "no standard found for lift=%s sex=%s weight_class=%s track=%s — defaulting to 0",
            lift,
            sex,
            weight_class,
            track,
        )
        return 0
    return row["percentile"]
