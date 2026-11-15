import pandas as pd
import plotly.express as px
import streamlit as st

from edunexus import ui
from edunexus.data import STANDARD_COLUMNS
from edunexus.quality import quality_score, run_quality_checks

df, f, settings = ui.page("Data Quality", "Completeness, validity, consistency and policy checks on the source data",
                          filters=False)

results = run_quality_checks(df, settings)
score = quality_score(df, results)
high = sum(r.count for r in results if r.severity == "High")
ui.kpi_row([
    ("Quality score", f"{score}%", "rows passing High & Medium rules"),
    ("Records", ui.fmt_num(len(df)), f"{df.shape[1]} fields (incl. derived)"),
    ("Rules failing", f"{sum(1 for r in results if r.count)} / {len(results)}", ""),
    ("High-severity issues", ui.fmt_num(high), "row-level hits"),
    ("Completeness", ui.fmt_pct(100 * (1 - df[STANDARD_COLUMNS].isna().any(axis=1).mean()), 2),
     f"{int(df[STANDARD_COLUMNS].isna().any(axis=1).sum())} incomplete row(s)"),
])
st.write("")

summary = pd.DataFrame([{
    "Rule": r.rule, "Category": r.category, "Severity": r.severity, "Records": r.count,
    "% of records": 100 * r.count / max(len(df), 1), "Description": r.description,
} for r in results])
sev_order = {"High": 0, "Medium": 1, "Low": 2}
summary = summary.sort_values(["Records"], ascending=False).sort_values("Severity", key=lambda s: s.map(sev_order), kind="stable")
summary["Status"] = summary["Records"].map(lambda n: "✅ Pass" if n == 0 else "❌ Fail")
summary["Severity"] = summary["Severity"].map({"High": "⛔ High", "Medium": "⚠️ Medium", "Low": "ℹ️ Low"})

c1, c2 = st.columns([1.5, 1])
with c1:
    st.markdown("#### Rule results")
    ui.table(summary[["Status", "Severity", "Category", "Rule", "Records", "% of records", "Description"]],
             pct_cols=["% of records"])
with c2:
    miss = df[STANDARD_COLUMNS].isna().sum().reset_index()
    miss.columns = ["Field", "Missing"]
    miss = miss[miss["Missing"] > 0]
    if miss.empty:
        st.success("No missing values in required fields.")
    else:
        ui.show(ui.bar(miss, "Field", "Missing", "Missing values by field", horizontal=True, text="Missing", height=300))
    ts = df["Student_Type"].map(lambda v: "Numeric" if str(v).isdigit() else "Letter").value_counts().reset_index()
    ts.columns = ["Code format", "Records"]
    fig = px.bar(ts, x="Code format", y="Records", title="Student_Type code formats", text="Records")
    fig.update_traces(marker_color=ui.PRIMARY, textposition="outside", cliponaxis=False)
    fig.update_layout(height=280); fig.update_xaxes(title=None); fig.update_yaxes(title=None)
    ui.show(fig)

st.markdown("#### Review failing records")
failing = [r for r in results if r.count]
if failing:
    pick = st.selectbox("Rule", [r.rule for r in failing])
    r = next(x for x in failing if x.rule == pick)
    st.caption(r.description)
    show_cols = ["ZID", "PIDM", "TERM", "Level", "Classification", "Major", "Time_Status", "Student_Type",
                 "COURSES", "CREDIT_HOURS", "BILL_HOURS", "WITHDRAWALS", "Pell", "Ethnicity"]
    ui.table(r.rows[show_cols], height=360)
    ui.download_csv(r.rows[show_cols], f"dq_{pick[:30].replace(' ', '_')}.csv")

st.markdown("#### Field profile")
prof = pd.DataFrame({
    "Field": STANDARD_COLUMNS,
    "Type": [str(df[c].dtype) for c in STANDARD_COLUMNS],
    "Distinct": [df[c].nunique() for c in STANDARD_COLUMNS],
    "Missing": [int(df[c].isna().sum()) for c in STANDARD_COLUMNS],
    "Min": [df[c].min() if df[c].dtype.kind in "fi" else "" for c in STANDARD_COLUMNS],
    "Max": [df[c].max() if df[c].dtype.kind in "fi" else "" for c in STANDARD_COLUMNS],
    "Sample values": [", ".join(map(str, df[c].dropna().astype(str).value_counts().index[:5])) for c in STANDARD_COLUMNS],
})
prof["Min"] = prof["Min"].astype(str); prof["Max"] = prof["Max"].astype(str)
ui.table(prof)
