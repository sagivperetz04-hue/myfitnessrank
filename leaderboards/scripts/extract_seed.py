#!/usr/bin/env python3
"""Extract a compact top-lifter seed pool from the OpenPowerlifting CSV.

Run once locally against the full 573 MB export; commit the small output
(`seed_pool.csv`). load_seed.py later encrypts the names and loads them.

    OPL_CSV=/path/to/openpowerlifting-YYYY-MM-DD.csv python scripts/extract_seed.py

Filter (the "professional" pool): Raw equipment, full-power meets (Event=SBD),
placed (numeric Place), with a valid bodyweight, all three lifts, and a total.
Keeps each lifter's best total, then takes the union of the top 200 by each
sortable metric per sex so every sort's top 200 is fully covered.
"""

import csv
import os
import sys

TOP_N = 200
METRICS = ("total", "ratio", "bench", "deadlift", "squat")
OUT_FIELDS = ("sex", "name", "bodyweight", "squat", "bench", "deadlift", "total")

_HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUT = os.path.join(_HERE, "seed_pool.csv")


def _pos_float(value: str):
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return f if f > 0 else None


def _is_placed(place: str) -> bool:
    # Numeric placings are real results; DQ, NS, DD, G, etc. are not.
    return (place or "").strip().isdigit()


def extract(csv_path: str, out_path: str) -> dict:
    best: dict[tuple[str, str], dict] = {}

    with open(csv_path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            if row.get("Equipment") != "Raw" or row.get("Event") != "SBD":
                continue
            sex = row.get("Sex")
            if sex not in ("M", "F"):
                continue
            if not _is_placed(row.get("Place")):
                continue

            bodyweight = _pos_float(row.get("BodyweightKg"))
            squat = _pos_float(row.get("Best3SquatKg"))
            bench = _pos_float(row.get("Best3BenchKg"))
            deadlift = _pos_float(row.get("Best3DeadliftKg"))
            total = _pos_float(row.get("TotalKg"))
            if None in (bodyweight, squat, bench, deadlift, total):
                continue

            name = row.get("Name", "").strip()
            if not name:
                continue

            key = (name, sex)
            prev = best.get(key)
            if prev is None or total > prev["total"]:
                best[key] = {
                    "sex": sex,
                    "name": name,
                    "bodyweight": bodyweight,
                    "squat": squat,
                    "bench": bench,
                    "deadlift": deadlift,
                    "total": total,
                    "ratio": total / bodyweight,
                }

    selected: set[tuple[str, str]] = set()
    counts = {}
    for sex in ("M", "F"):
        pool = [(k, v) for k, v in best.items() if v["sex"] == sex]
        for metric in METRICS:
            pool.sort(key=lambda kv: kv[1][metric], reverse=True)
            for key, _ in pool[:TOP_N]:
                selected.add(key)
        counts[sex] = sum(1 for k in selected if k[1] == sex)

    with open(out_path, "w", newline="", encoding="utf-8") as out:
        writer = csv.DictWriter(out, fieldnames=OUT_FIELDS)
        writer.writeheader()
        for key in sorted(selected, key=lambda k: (k[1], -best[k]["total"])):
            v = best[key]
            writer.writerow(
                {
                    "sex": v["sex"],
                    "name": v["name"],
                    "bodyweight": f"{v['bodyweight']:.2f}",
                    "squat": f"{v['squat']:.2f}",
                    "bench": f"{v['bench']:.2f}",
                    "deadlift": f"{v['deadlift']:.2f}",
                    "total": f"{v['total']:.2f}",
                }
            )

    return counts


def main() -> int:
    csv_path = os.environ.get("OPL_CSV") or (sys.argv[1] if len(sys.argv) > 1 else "")
    if not csv_path or not os.path.exists(csv_path):
        print(
            "set OPL_CSV (or pass a path arg) to the OpenPowerlifting CSV",
            file=sys.stderr,
        )
        return 1
    out_path = os.environ.get("SEED_OUT", DEFAULT_OUT)
    counts = extract(csv_path, out_path)
    print(f"wrote {out_path}: M={counts['M']} F={counts['F']} lifters")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
