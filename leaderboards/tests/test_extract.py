"""Seed extraction filter + dedup logic over a tiny in-memory CSV."""

import csv

from scripts.extract_seed import extract

_HEADER = [
    "Name",
    "Sex",
    "Event",
    "Equipment",
    "BodyweightKg",
    "Best3SquatKg",
    "Best3BenchKg",
    "Best3DeadliftKg",
    "TotalKg",
    "Place",
]


def _row(name, sex, event, equip, bw, sq, bn, dl, total, place):
    return [name, sex, event, equip, bw, sq, bn, dl, total, place]


def _write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(_HEADER)
        for r in rows:
            w.writerow(r)


def _read_pool(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def test_filters_and_dedups(tmp_path):
    src = tmp_path / "opl.csv"
    out = tmp_path / "pool.csv"
    _write_csv(
        src,
        [
            # valid, two meets for the same lifter — keep the higher total
            _row("Lifter A", "M", "SBD", "Raw", 90, 300, 200, 350, 850, "1"),
            _row("Lifter A", "M", "SBD", "Raw", 91, 310, 205, 360, 875, "1"),
            # valid female
            _row("Lifter B", "F", "SBD", "Raw", 60, 170, 100, 200, 470, "1"),
            # dropped: equipped
            _row("Lifter C", "M", "SBD", "Single-ply", 100, 400, 300, 400, 1100, "1"),
            # dropped: not full power
            _row("Lifter D", "M", "B", "Raw", 100, 0, 250, 0, 250, "1"),
            # dropped: disqualified (non-numeric place)
            _row("Lifter E", "M", "SBD", "Raw", 100, 300, 200, 300, 800, "DQ"),
            # dropped: missing a lift
            _row("Lifter F", "M", "SBD", "Raw", 100, 300, 0, 300, 600, "1"),
        ],
    )

    counts = extract(str(src), str(out))

    assert counts == {"M": 1, "F": 1}
    pool = _read_pool(str(out))
    assert len(pool) == 2

    by_name = {p["name"]: p for p in pool}
    assert set(by_name) == {"Lifter A", "Lifter B"}
    # best-total meet kept for Lifter A
    assert by_name["Lifter A"]["total"] == "875.00"
    assert by_name["Lifter A"]["squat"] == "310.00"


def test_empty_when_no_valid_rows(tmp_path):
    src = tmp_path / "opl.csv"
    out = tmp_path / "pool.csv"
    _write_csv(
        src,
        [
            _row("Lifter X", "M", "B", "Raw", 100, 0, 250, 0, 250, "1"),
        ],
    )
    counts = extract(str(src), str(out))
    assert counts == {"M": 0, "F": 0}
    assert _read_pool(str(out)) == []
