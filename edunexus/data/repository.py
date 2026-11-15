"""Standardisation layer: raw source frame -> clean, typed analytics frame."""
from __future__ import annotations

import pandas as pd

from ..config import label
from .sources import build_source

STANDARD_COLUMNS = [
    "TERM", "PIDM", "ZID", "Student_Type", "Level", "Classification", "Program",
    "Program_Description", "Major", "Campus", "Time_Status", "Gender", "Ethnicity",
    "COURSES", "CREDIT_HOURS", "BILL_HOURS", "WITHDRAWALS", "Pell",
]
NUMERIC = ["COURSES", "CREDIT_HOURS", "BILL_HOURS", "WITHDRAWALS"]
CODE_COLS = ["Student_Type", "Level", "Classification", "Program", "Major", "Campus",
             "Time_Status", "Gender", "Ethnicity", "Pell"]


class SchemaError(ValueError):
    pass


def _clean_code(v):
    if v is None or (isinstance(v, float) and v != v):
        return None
    s = str(v).strip()
    if s.endswith(".0") and s[:-2].isdigit():
        s = s[:-2]
    return s or None


def term_label(term, settings: dict) -> str:
    t = str(term)
    if len(t) == 6 and t.isdigit():
        season = (settings.get("labels", {}).get("Term", {}) or {}).get(t[4:], f"Term {t[4:]}")
        return f"{season} {t[:4]}"
    return t


def standardise(raw: pd.DataFrame, settings: dict) -> pd.DataFrame:
    mapping = settings.get("columns", {}) or {}
    rename = {src: std for std, src in mapping.items() if src in raw.columns}
    df = raw.rename(columns=rename)
    missing = [c for c in STANDARD_COLUMNS if c not in df.columns]
    if missing:
        raise SchemaError(f"Source is missing required columns: {', '.join(missing)}")
    df = df[STANDARD_COLUMNS].copy()

    for c in NUMERIC:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["TERM"] = df["TERM"].map(_clean_code)
    df["PIDM"] = df["PIDM"].map(_clean_code)
    df["ZID"] = df["ZID"].map(lambda v: _clean_code(v))
    for c in CODE_COLS + ["Program_Description"]:
        df[c] = df[c].map(_clean_code)
    df["Ethnicity"] = df["Ethnicity"].fillna("Unknown")

    # Derived fields
    df["Term_Label"] = df["TERM"].map(lambda t: term_label(t, settings))
    for c in ["Level", "Classification", "Time_Status", "Gender", "Pell", "Campus", "Student_Type"]:
        df[f"{c}_Label"] = df[c].map(lambda v, c=c: label(settings, c, v))
    df["Is_Pell"] = df["Pell"].eq("Y")
    df["Has_Withdrawal"] = df["WITHDRAWALS"].fillna(0) > 0
    df["Is_Full_Time"] = df["Time_Status"].eq("F")
    df["Hours_per_Course"] = (df["CREDIT_HOURS"] / df["COURSES"]).where(df["COURSES"] > 0)
    df["Load_Band"] = df.apply(lambda r: load_band(r, settings), axis=1)
    df["Program_Name"] = df["Program_Description"].fillna(df["Program"]).astype(str)
    return df


def load_band(row, settings: dict) -> str:
    pol = settings.get("credit_policy", {})
    ch = row["CREDIT_HOURS"]
    if pd.isna(ch):
        return "Missing"
    if row["Level"] not in pol.get("applies_to_levels", ["UG"]):
        return "Not policy-checked"
    if ch < pol.get("full_time_min", 12):
        return "Part-time (<12)"
    if ch <= pol.get("overload_threshold", 18.5):
        return "Standard full-time (12–18.5)"
    if ch <= pol.get("max_credits", 24):
        return "Overload – needs permission (18.5–24)"
    return "Exceeds maximum (>24)"


LOAD_BAND_ORDER = [
    "Part-time (<12)", "Standard full-time (12–18.5)",
    "Overload – needs permission (18.5–24)", "Exceeds maximum (>24)",
    "Not policy-checked", "Missing",
]


def load_students(settings: dict) -> tuple[pd.DataFrame, str]:
    source = build_source(settings)
    raw = source.read()
    return standardise(raw, settings), source.describe()
