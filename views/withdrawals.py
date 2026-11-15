import plotly.express as px
import streamlit as st

from edunexus import ui
from edunexus.metrics import group_summary, rate_gap

df, f, settings = ui.page("Withdrawals", "Who withdraws, how often, and where risk concentrates")
ui.no_data_guard(f)
min_n = settings.get("insights", {}).get("min_group_size", 15)
hi = settings.get("insights", {}).get("high_withdrawal_rate_pct", 15)

w = f[f["Has_Withdrawal"]]
ui.kpi_row([
    ("Withdrawal rate", ui.fmt_pct(f["Has_Withdrawal"].mean() * 100), "students with ≥1 withdrawal"),
    ("Students withdrawing", ui.fmt_num(len(w)), ""),
    ("Total withdrawals", ui.fmt_num(f["WITHDRAWALS"].sum()), ""),
    ("Avg per withdrawing student", ui.fmt_num(w["WITHDRAWALS"].mean(), 2) if len(w) else "—", ""),
    ("Withdrawals / courses", ui.fmt_pct(100 * f["WITHDRAWALS"].sum() / max(f["COURSES"].sum(), 1)), "of course enrolments"),
])
st.write("")

c1, c2 = st.columns(2)
with c1:
    d = f["WITHDRAWALS"].fillna(0).clip(upper=6).astype(int).map(lambda v: "6+" if v >= 6 else str(v))
    dist = d.value_counts().reindex(["0", "1", "2", "3", "4", "5", "6+"]).dropna().reset_index()
    dist.columns = ["Withdrawals", "Students"]
    fig = ui.bar(dist, "Withdrawals", "Students", "Students by number of withdrawals", text="Students")
    fig.update_xaxes(type="category")
    ui.show(fig)
with c2:
    dim = st.selectbox("Rate by", ["Classification", "Level_Label", "Time_Status_Label", "Pell_Label",
                                   "Gender_Label", "Ethnicity", "Campus_Label"],
                       format_func=lambda s: s.replace("_Label", "").replace("_", " "))
    r = rate_gap(f, dim, "Has_Withdrawal").sort_values("Rate %", ascending=False)
    fig = px.bar(r, x=dim, y="Rate %", text="Rate %", title=f"Withdrawal rate by {dim.replace('_Label', '')}",
                 hover_data=["Students", "Gap vs overall (pp)"])
    fig.update_traces(marker_color=ui.PRIMARY, texttemplate="%{text:.1f}%", textposition="outside", cliponaxis=False)
    fig.add_hline(y=f["Has_Withdrawal"].mean() * 100, line_dash="dot", line_color="#9a9994",
                  annotation_text="overall")
    fig.update_xaxes(title=None); fig.update_yaxes(title=None); fig.update_layout(height=380)
    ui.show(fig)

st.markdown(f"#### Majors with highest withdrawal rate (≥ {min_n} students)")
m = group_summary(f, "Major")
m = m[m["Students"] >= min_n].sort_values("Withdrawal rate %", ascending=False).head(20)
m["Status"] = m["Withdrawal rate %"].map(lambda v: "⚠️ Above threshold" if v > hi else "")
fig = px.bar(m, x="Withdrawal rate %", y="Major", orientation="h", hover_data=["Students", "Total withdrawals"],
             title=f"Top 20 majors by withdrawal rate (threshold {hi}%)")
fig.update_traces(marker_color=[ui.STATUS["critical"] if v > hi else ui.PRIMARY for v in m["Withdrawal rate %"]])
fig.add_vline(x=hi, line_dash="dash", line_color=ui.STATUS["critical"])
fig.update_yaxes(categoryorder="total ascending", title=None); fig.update_xaxes(title=None)
fig.update_layout(height=560)
ui.show(fig)

st.markdown("#### Students with multiple withdrawals")
thr = st.number_input("Minimum withdrawals", 1, 50, 3)
lst = f[f["WITHDRAWALS"] >= thr][["ZID", "Level", "Classification", "Major", "Program_Name", "Time_Status_Label",
                                    "Pell", "COURSES", "CREDIT_HOURS", "WITHDRAWALS"]] \
    .sort_values("WITHDRAWALS", ascending=False)
st.caption(f"{len(lst):,} students")
ui.table(lst, height=360)
ui.download_csv(lst, "multiple_withdrawals.csv")
