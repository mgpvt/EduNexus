"""Reusable KPI and aggregation functions (UI-independent, unit-testable)."""
from __future__ import annotations

import pandas as pd


def kpis(df: pd.DataFrame) -> dict:
    n = len(df)
    if n == 0:
        return {k: 0 for k in ["students", "programs", "majors", "full_time_pct", "pell_pct",
                               "withdrawal_rate", "avg_courses", "avg_credits", "total_credits",
                               "total_withdrawals", "female_pct", "hispanic_pct", "grad_pct"]}
    return {
        "students": n,
        "programs": df["Program"].nunique(),
        "majors": df["Major"].nunique(),
        "full_time_pct": 100 * df["Is_Full_Time"].mean(),
        "pell_pct": 100 * df["Is_Pell"].mean(),
        "withdrawal_rate": 100 * df["Has_Withdrawal"].mean(),
        "avg_courses": df["COURSES"].mean(),
        "avg_credits": df["CREDIT_HOURS"].mean(),
        "total_credits": df["CREDIT_HOURS"].sum(),
        "total_withdrawals": df["WITHDRAWALS"].sum(),
        "female_pct": 100 * df["Gender"].eq("F").mean(),
        "hispanic_pct": 100 * df["Ethnicity"].eq("Hispanic").mean(),
        "grad_pct": 100 * (~df["Level"].eq("UG")).mean(),
    }


def group_summary(df: pd.DataFrame, by: str | list[str]) -> pd.DataFrame:
    g = df.groupby(by, dropna=False)
    out = pd.DataFrame({
        "Students": g.size(),
        "Full-time %": g["Is_Full_Time"].mean() * 100,
        "Pell %": g["Is_Pell"].mean() * 100,
        "Withdrawal rate %": g["Has_Withdrawal"].mean() * 100,
        "Total withdrawals": g["WITHDRAWALS"].sum(),
        "Avg courses": g["COURSES"].mean(),
        "Avg credit hrs": g["CREDIT_HOURS"].mean(),
        "Total credit hrs": g["CREDIT_HOURS"].sum(),
        "Female %": g["Gender"].apply(lambda s: (s == "F").mean() * 100),
    }).reset_index()
    out["Share %"] = 100 * out["Students"] / max(len(df), 1)
    return out.sort_values("Students", ascending=False)


def share(df: pd.DataFrame, col: str) -> pd.DataFrame:
    s = df[col].fillna("Unknown").value_counts().rename_axis(col).reset_index(name="Students")
    s["Share %"] = 100 * s["Students"] / max(len(df), 1)
    return s


def rate_gap(df: pd.DataFrame, group_col: str, flag_col: str) -> pd.DataFrame:
    """Rate of a boolean flag per group, with the gap vs overall in percentage points."""
    overall = df[flag_col].mean() * 100
    r = df.groupby(group_col)[flag_col].agg(["mean", "size"]).reset_index()
    r["Rate %"] = r["mean"] * 100
    r["Gap vs overall (pp)"] = r["Rate %"] - overall
    return r.drop(columns="mean").rename(columns={"size": "Students"})


def term_trend(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby(["TERM", "Term_Label"])
    t = pd.DataFrame({
        "Students": g.size(),
        "Full-time %": g["Is_Full_Time"].mean() * 100,
        "Pell %": g["Is_Pell"].mean() * 100,
        "Withdrawal rate %": g["Has_Withdrawal"].mean() * 100,
        "Avg credit hrs": g["CREDIT_HOURS"].mean(),
        "Total credit hrs": g["CREDIT_HOURS"].sum(),
    }).reset_index().sort_values("TERM")
    t["Students Δ %"] = t["Students"].pct_change() * 100
    return t
