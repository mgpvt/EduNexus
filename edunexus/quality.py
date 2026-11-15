"""Data quality rules. Each rule returns the offending rows so they can be reviewed."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .data.repository import STANDARD_COLUMNS


@dataclass
class RuleResult:
    rule: str
    category: str
    severity: str  # "High" | "Medium" | "Low"
    description: str
    rows: pd.DataFrame

    @property
    def count(self) -> int:
        return len(self.rows)


def run_quality_checks(df: pd.DataFrame, settings: dict) -> list[RuleResult]:
    pol = settings.get("credit_policy", {})
    dq = settings.get("data_quality", {})
    levels = pol.get("applies_to_levels", ["UG"])
    in_policy = df["Level"].isin(levels)
    results: list[RuleResult] = []

    def add(rule, cat, sev, desc, mask):
        results.append(RuleResult(rule, cat, sev, desc, df[mask.fillna(False)]))

    # Completeness
    req = [c for c in STANDARD_COLUMNS]
    add("Missing values", "Completeness", "High",
        "Rows with one or more blank required fields.", df[req].isna().any(axis=1))
    add("Unknown ethnicity", "Completeness", "Low",
        "Ethnicity recorded as Unknown or blank.", df["Ethnicity"].eq("Unknown"))

    # Uniqueness
    add("Duplicate student-term", "Uniqueness", "High",
        "Same PIDM appears more than once in a term.",
        df.duplicated(["PIDM", "TERM"], keep=False))
    zid_per_pidm = df.groupby("PIDM")["ZID"].transform("nunique")
    add("PIDM ↔ ZID conflict", "Uniqueness", "High",
        "One PIDM linked to more than one ZID.", zid_per_pidm > 1)

    # Validity / policy
    mx = pol.get("max_credits", 24)
    add(f"Credit hours above maximum ({mx})", "Policy", "High",
        f"{', '.join(levels)} students with CREDIT_HOURS above the {mx}-hour term maximum. "
        "Often indicates cumulative or mis-scaled hours in the extract.",
        in_policy & (df["CREDIT_HOURS"] > mx))
    ov = pol.get("overload_threshold", 18.5)
    add(f"Overload without approval check ({ov}–{mx})", "Policy", "Medium",
        f"Students between {ov} and {mx} hours require department chair & Student Accounts permission.",
        in_policy & (df["CREDIT_HOURS"] > ov) & (df["CREDIT_HOURS"] <= mx))
    ftmin = pol.get("full_time_min", 12)
    add("Full-time status below minimum", "Consistency", "Medium",
        f"Time status is Full-time but CREDIT_HOURS < {ftmin}.",
        in_policy & df["Is_Full_Time"] & (df["CREDIT_HOURS"] < ftmin))
    add("Part-time status at full-time load", "Consistency", "Low",
        f"Time status is not Full-time but CREDIT_HOURS between {ftmin} and {mx}.",
        in_policy & ~df["Is_Full_Time"] & df["CREDIT_HOURS"].between(ftmin, mx))
    tol = dq.get("credit_bill_tolerance", 0)
    add("Credit vs billed hours mismatch", "Consistency", "Medium",
        "CREDIT_HOURS differs from BILL_HOURS.",
        (df["CREDIT_HOURS"] - df["BILL_HOURS"]).abs() > tol)
    mc = dq.get("max_courses_per_term", 10)
    add(f"More than {mc} courses", "Validity", "Medium",
        f"COURSES above {mc} in a single term.", df["COURSES"] > mc)
    add("Withdrawals exceed courses", "Validity", "High",
        "WITHDRAWALS greater than COURSES.", df["WITHDRAWALS"] > df["COURSES"])
    add("Zero credit hours", "Validity", "Low",
        "Enrolled with 0 credit hours.", df["CREDIT_HOURS"].eq(0))
    mw = dq.get("max_withdrawals_flag", 5)
    add(f"More than {mw} withdrawals", "Validity", "Medium",
        f"Students with more than {mw} withdrawals.", df["WITHDRAWALS"] > mw)

    # Code formats
    add("Numeric Student_Type code", "Format", "Low",
        "Student_Type is numeric while most codes are letters - confirm code set.",
        df["Student_Type"].fillna("").str.fullmatch(r"\d+"))
    add("Unlabelled Level code", "Format", "Low",
        "Level codes without a label in settings.",
        ~df["Level"].isin((settings.get("labels", {}).get("Level") or {}).keys()))
    return results


def quality_score(df: pd.DataFrame, results: list[RuleResult]) -> float:
    """Share of rows passing all High and Medium rules (0-100)."""
    if df.empty:
        return 100.0
    bad = set()
    for r in results:
        if r.severity in ("High", "Medium"):
            bad.update(r.rows.index.tolist())
    return round(100 * (1 - len(bad) / len(df)), 1)
