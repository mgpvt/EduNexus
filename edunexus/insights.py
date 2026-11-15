"""Insight engine.

1. A deterministic rule-based engine that always runs (no network, no cost).
2. An optional AI narrative via the Anthropic API, enabled when an API key is set.
   Only aggregated statistics are sent - never student identifiers or rows.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass

import pandas as pd

from .metrics import kpis, group_summary, rate_gap


@dataclass
class Insight:
    category: str
    severity: str  # "info" | "positive" | "warning" | "critical"
    title: str
    detail: str


def _fmt(x, d=1):
    return f"{x:,.{d}f}"


def rule_based_insights(df: pd.DataFrame, settings: dict) -> list[Insight]:
    out: list[Insight] = []
    if df.empty:
        return out
    cfg = settings.get("insights", {})
    min_n = cfg.get("min_group_size", 15)
    hi_wd = cfg.get("high_withdrawal_rate_pct", 15)
    pol = settings.get("credit_policy", {})
    k = kpis(df)

    # Enrollment composition
    lvl = df["Level_Label"].value_counts(normalize=True) * 100
    out.append(Insight("Enrollment", "info", "Enrollment mix",
        f"{k['students']:,} students across {k['programs']} programs and {k['majors']} majors. "
        f"{lvl.index[0]} students make up {_fmt(lvl.iloc[0])}% of enrollment."))

    # Majors concentration
    maj = group_summary(df, "Major").head(5)
    top5 = maj["Students"].sum() / len(df) * 100
    out.append(Insight("Programs", "info", "Program concentration",
        f"The five largest majors ({', '.join(maj['Major'].astype(str))}) account for "
        f"{_fmt(top5)}% of all students."))

    # Withdrawals
    out.append(Insight("Withdrawals", "warning" if k["withdrawal_rate"] > hi_wd else "info",
        "Withdrawal rate",
        f"{_fmt(k['withdrawal_rate'])}% of students have at least one withdrawal "
        f"({int(k['total_withdrawals']):,} withdrawals in total)."))
    prog = group_summary(df, "Major")
    prog = prog[prog["Students"] >= min_n]
    risky = prog[prog["Withdrawal rate %"] > hi_wd].sort_values("Withdrawal rate %", ascending=False)
    if not risky.empty:
        names = ", ".join(f"{r.Major} ({_fmt(r['Withdrawal rate %'])}%)" for _, r in risky.head(5).iterrows())
        out.append(Insight("Withdrawals", "warning", "Majors with elevated withdrawals",
            f"{len(risky)} majors (≥{min_n} students) exceed a {hi_wd}% withdrawal rate: {names}."))

    # Pell & withdrawal gap
    if df["Is_Pell"].any() and (~df["Is_Pell"]).any():
        p = df[df["Is_Pell"]]["Has_Withdrawal"].mean() * 100
        np_ = df[~df["Is_Pell"]]["Has_Withdrawal"].mean() * 100
        gap = p - np_
        out.append(Insight("Financial aid", "warning" if gap > 3 else "info",
            "Pell vs non-Pell withdrawals",
            f"Pell recipients withdraw at {_fmt(p)}% vs {_fmt(np_)}% for non-Pell "
            f"({'+' if gap >= 0 else ''}{_fmt(gap)} pp)."))
        lvl_p = rate_gap(df[df["Level"] == "UG"], "Classification", "Is_Pell") if (df["Level"] == "UG").any() else None
        if lvl_p is not None and not lvl_p.empty:
            top = lvl_p.sort_values("Rate %", ascending=False).iloc[0]
            out.append(Insight("Financial aid", "info", "Pell concentration",
                f"{_fmt(k['pell_pct'])}% of students receive Pell. Among undergraduates, the highest "
                f"share is in classification {top['Classification']} ({_fmt(top['Rate %'])}%)."))

    # Demographic gaps in withdrawals
    for col, name in [("Gender_Label", "gender"), ("Ethnicity", "ethnicity")]:
        g = rate_gap(df, col, "Has_Withdrawal")
        g = g[g["Students"] >= min_n]
        if len(g) > 1:
            hi = g.sort_values("Rate %").iloc[-1]
            lo = g.sort_values("Rate %").iloc[0]
            if hi["Rate %"] - lo["Rate %"] >= 3:
                out.append(Insight("Equity", "warning", f"Withdrawal gap by {name}",
                    f"{hi[col]} students withdraw at {_fmt(hi['Rate %'])}% vs {_fmt(lo['Rate %'])}% "
                    f"for {lo[col]} ({_fmt(hi['Rate %'] - lo['Rate %'])} pp gap)."))

    # Workload policy
    levels = pol.get("applies_to_levels", ["UG"])
    sub = df[df["Level"].isin(levels)]
    if not sub.empty:
        over = (sub["CREDIT_HOURS"] > pol.get("max_credits", 24)).mean() * 100
        if over > 5:
            out.append(Insight("Data quality", "critical", "Credit hours exceed policy",
                f"{_fmt(over)}% of {'/'.join(levels)} records exceed the {pol.get('max_credits', 24)}-hour "
                f"term maximum (median {_fmt(sub['CREDIT_HOURS'].median())} hrs vs typical "
                f"{pol.get('typical_load', 16)}). CREDIT_HOURS in the source likely holds cumulative "
                "or mis-scaled values - workload analytics should be read with caution until confirmed."))

    # Campus
    if df["Campus"].nunique() > 1:
        c = group_summary(df, "Campus_Label")
        smallest = c.iloc[-1]
        out.append(Insight("Campus", "info", "Campus distribution",
            f"{c.iloc[0]['Campus_Label']} serves {_fmt(c.iloc[0]['Share %'])}% of students; "
            f"{smallest['Campus_Label']} has {int(smallest['Students'])} students with a "
            f"{_fmt(smallest['Full-time %'])}% full-time rate."))

    # Terms
    if df["TERM"].nunique() < 2:
        out.append(Insight("Trends", "info", "Single term loaded",
            "Only one term is present, so term-over-term trends are not yet available. "
            "Load additional terms (Excel or database) to enable trend analysis."))
    return out


def build_ai_payload(df: pd.DataFrame, settings: dict) -> dict:
    """Aggregated, de-identified statistics for the AI narrative."""
    k = {kk: (round(v, 2) if isinstance(v, float) else int(v)) for kk, v in kpis(df).items()}
    def tbl(col, n=12):
        g = group_summary(df, col).head(n)
        return g[[col, "Students", "Full-time %", "Pell %", "Withdrawal rate %", "Avg credit hrs"]] \
            .round(1).to_dict(orient="records")
    return {
        "kpis": k,
        "credit_policy": settings.get("credit_policy", {}),
        "by_level": tbl("Level_Label"),
        "by_classification": tbl("Classification"),
        "by_major_top": tbl("Major", 15),
        "by_gender": tbl("Gender_Label"),
        "by_ethnicity": tbl("Ethnicity"),
        "by_pell": tbl("Pell_Label"),
        "by_campus": tbl("Campus_Label"),
        "by_time_status": tbl("Time_Status_Label"),
        "terms": sorted(df["TERM"].dropna().unique().tolist()),
    }


def ai_available(settings: dict) -> bool:
    ai = settings.get("ai", {})
    return bool(ai.get("enabled", True) and os.environ.get(ai.get("api_key_env", "ANTHROPIC_API_KEY")))


def ai_narrative(df: pd.DataFrame, settings: dict, question: str | None = None) -> str:
    ai = settings.get("ai", {})
    key = os.environ.get(ai.get("api_key_env", "ANTHROPIC_API_KEY"))
    if not key:
        raise RuntimeError("No API key configured.")
    import anthropic  # optional dependency

    payload = build_ai_payload(df, settings)
    prompt = (
        "You are an institutional research analyst at a university. Using ONLY the aggregated "
        "statistics below, write concise, specific insights for academic leadership: key findings, "
        "risks (withdrawals, equity gaps, financial aid), data-quality caveats, and 3-5 recommended "
        "actions. Use short headed sections and bullet points. Do not invent numbers.\n\n"
        f"DATA:\n{json.dumps(payload, default=str)}"
    )
    if question:
        prompt += f"\n\nAlso answer this question from leadership: {question}"
    client = anthropic.Anthropic(api_key=key)
    msg = client.messages.create(model=ai.get("model", "claude-sonnet-5-5"),
                                 max_tokens=int(ai.get("max_tokens", 1200)),
                                 messages=[{"role": "user", "content": prompt}])
    return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
