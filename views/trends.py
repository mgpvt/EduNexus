import plotly.express as px
import streamlit as st

from edunexus import ui
from edunexus.metrics import term_trend

df, f, settings = ui.page("Term Trends", "Term-over-term change in enrollment and outcomes")
ui.no_data_guard(f)

t = term_trend(f)
if len(t) < 2:
    st.info(
        f"Only one term is loaded (**{t['Term_Label'].iloc[0]}**). Trend charts appear automatically "
        "once more terms are available — append additional terms to the Excel file (same columns, "
        "different TERM values) or point EduNexus at the database on the **Administration** page.")
    ui.kpi_row([
        ("Students", ui.fmt_num(t["Students"].iloc[0]), t["Term_Label"].iloc[0]),
        ("Full-time", ui.fmt_pct(t["Full-time %"].iloc[0]), ""),
        ("Pell", ui.fmt_pct(t["Pell %"].iloc[0]), ""),
        ("Withdrawal rate", ui.fmt_pct(t["Withdrawal rate %"].iloc[0]), ""),
    ])
    st.stop()

last, prev = t.iloc[-1], t.iloc[-2]


def delta(c, pp=True):
    d = last[c] - prev[c]
    return f"{'+' if d >= 0 else ''}{d:.1f}{' pp' if pp else ''} vs {prev['Term_Label']}"


ui.kpi_row([
    ("Students", ui.fmt_num(last["Students"]), f"{'+' if last['Students Δ %'] >= 0 else ''}{last['Students Δ %']:.1f}% vs {prev['Term_Label']}"),
    ("Full-time", ui.fmt_pct(last["Full-time %"]), delta("Full-time %")),
    ("Pell", ui.fmt_pct(last["Pell %"]), delta("Pell %")),
    ("Withdrawal rate", ui.fmt_pct(last["Withdrawal rate %"]), delta("Withdrawal rate %")),
])
st.write("")

order = t["Term_Label"].tolist()
c1, c2 = st.columns(2)
with c1:
    fig = px.line(t, x="Term_Label", y="Students", markers=True, title="Headcount by term")
    fig.update_traces(line=dict(width=2, color=ui.PRIMARY), marker=dict(size=8))
    fig.update_xaxes(title=None, categoryorder="array", categoryarray=order); fig.update_yaxes(title=None)
    ui.show(fig)
with c2:
    m = t.melt(id_vars="Term_Label", value_vars=["Full-time %", "Pell %", "Withdrawal rate %"],
               var_name="Measure", value_name="Rate")
    fig = px.line(m, x="Term_Label", y="Rate", color="Measure", markers=True, title="Key rates by term (%)")
    fig.update_traces(line=dict(width=2), marker=dict(size=8))
    fig.update_xaxes(title=None, categoryorder="array", categoryarray=order); fig.update_yaxes(title=None)
    ui.show(fig)

dim = st.selectbox("Headcount trend by", ["Level_Label", "Classification", "Campus_Label", "Gender_Label", "Pell_Label"],
                   format_func=lambda s: s.replace("_Label", "").replace("_", " "))
x = f.groupby(["TERM", "Term_Label", dim]).size().reset_index(name="Students").sort_values("TERM")
fig = px.line(x, x="Term_Label", y="Students", color=dim, markers=True)
fig.update_xaxes(title=None, categoryorder="array", categoryarray=order); fig.update_yaxes(title=None)
ui.show(fig)

ui.table(t.drop(columns="TERM"), pct_cols=["Full-time %", "Pell %", "Withdrawal rate %", "Students Δ %"],
         num_cols=["Avg credit hrs", "Total credit hrs"])
