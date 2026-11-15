"""Create a clearly-labelled SYNTHETIC demo copy of the student file.

Keeps every student, ID, program and demographic field from the source file and
regenerates only the workload fields (COURSES, CREDIT_HOURS, BILL_HOURS,
WITHDRAWALS) so they follow the university credit-load policy:

  * full-time >= 12 credits, overload > 18.5 needs permission, max 24 per term
  * part-time levels below 12

Which students withdrew is preserved from the source (so withdrawal patterns by
Pell, gender, major etc. stay realistic); the count is capped at their course count.

These values do NOT describe any real student. Use for testing/demo only.

Usage:  python scripts/make_demo_data.py [source.xlsx] [output.xlsx]
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "TestStudents.xlsx"
OUT = ROOT / "data" / "TestStudents_demo.xlsx"
SEED = 202130

# Credit bands (min, max) by level and time status.
UG_BANDS = {
    "F": [((12, 18), 0.90), ((19, 21), 0.08), ((22, 24), 0.02)],  # 19-24 = approved overload
    "T": [((9, 11), 1.0)],
    "H": [((6, 8), 1.0)],
    "L": [((1, 5), 1.0)],
    "P": [((3, 11), 1.0)],
    "N": [((3, 11), 1.0)],
}
GRAD_BANDS = {  # GR / PR / doctoral / certificate
    "F": [((9, 15), 1.0)],
    "T": [((6, 8), 1.0)],
    "H": [((4, 6), 1.0)],
    "L": [((1, 3), 1.0)],
    "P": [((3, 8), 1.0)],
    "N": [((3, 8), 1.0)],
}
COURSE_CREDITS = [3, 4, 1, 2]
COURSE_WEIGHTS = [0.78, 0.12, 0.06, 0.04]


def pick_band(rng, bands):
    i = rng.choice(len(bands), p=[w for _, w in bands])
    return bands[i][0]


def make_load(rng, level, status):
    bands = (UG_BANDS if level == "UG" else GRAD_BANDS).get(status, UG_BANDS["P"] if level == "UG" else GRAD_BANDS["P"])
    lo, hi = pick_band(rng, bands)
    for _ in range(200):
        target = rng.integers(lo, hi + 1)
        credits, n = [], 0
        while sum(credits) < target:
            credits.append(int(rng.choice(COURSE_CREDITS, p=COURSE_WEIGHTS)))
        if lo <= sum(credits) <= hi:
            return len(credits), float(sum(credits))
    return max(1, round(lo / 3)), float(lo)


def build(src: Path = SRC, out: Path = OUT, seed: int = SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    df = pd.read_excel(src)
    blank = df[["COURSES", "CREDIT_HOURS", "BILL_HOURS", "WITHDRAWALS"]].isna().all(axis=1)

    courses, credits, bills, wds = [], [], [], []
    for _, r in df.iterrows():
        if blank.loc[_]:
            courses.append(np.nan); credits.append(np.nan); bills.append(np.nan); wds.append(np.nan)
            continue
        n, ch = make_load(rng, str(r["Level"]), str(r["Time_Status"]))
        bh = ch
        if rng.random() < 0.04:  # small, realistic billing differences (audits, flat-rate, waivers)
            bh = max(0.0, ch + float(rng.choice([-3, -1, 1, 3])))
        w = r["WITHDRAWALS"]
        w = 0 if pd.isna(w) else int(min(w, n))
        courses.append(n); credits.append(ch); bills.append(bh); wds.append(w)

    df["COURSES"], df["CREDIT_HOURS"], df["BILL_HOURS"], df["WITHDRAWALS"] = courses, credits, bills, wds

    note = pd.DataFrame({"About this file": [
        "SYNTHETIC DEMO DATA - NOT FOR REPORTING.",
        f"Generated from {src.name} by scripts/make_demo_data.py (seed {seed}).",
        "Student IDs, programs, demographics, Pell and time status are copied from the source file.",
        "COURSES, CREDIT_HOURS, BILL_HOURS and WITHDRAWALS are generated to follow the credit-load policy:",
        "full-time >= 12; overload > 18.5 needs chair & Student Accounts permission; maximum 24.",
        "Which students withdrew is kept from the source; counts are capped at their course count.",
        "Replace with the corrected extract from the student system when available.",
    ]})
    with pd.ExcelWriter(out, engine="openpyxl") as xw:
        df.to_excel(xw, sheet_name="TestStudents", index=False)
        note.to_excel(xw, sheet_name="README_SYNTHETIC", index=False)
    return df


if __name__ == "__main__":
    a = sys.argv[1:]
    d = build(Path(a[0]) if a else SRC, Path(a[1]) if len(a) > 1 else OUT)
    print(f"Wrote {OUT if len(a) < 2 else a[1]}: {len(d)} rows")
