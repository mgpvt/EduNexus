import plotly.express as px
import streamlit as st

from edunexus import ui
from edunexus.metrics import group_summary, rate_gap

df, f, settings = ui.page("Pell & Financial Aid", "Pell grant recipients: who they are and how they fare")
ui.no_data_guard(f)
min_n = settings.get("insights", {}).get("min_group_size", 15)

p, n = f[f["Is_Pell"]], f[f["Pell"].eq("N")]
ui.kpi_row([
    ("Pell recipients", ui.fmt_num(len(p)), ui.fmt_pct(100 * len(p) / len(f)) + " of students"),
    ("Pell full-time", ui.fmt_pct(p["Is_Full_Time"].mean() * 100) if len(p) else "—",
     f"non-Pell {ui.fmt_pct(n['Is_Full_Time'].mean() * 100) if len(n) else '—'}"),
    ("Pell withdrawal rate", ui.fmt_pct(p["Has_Withdrawal"].mean() * 100) if len(p) else "—",
     f"non-Pell {ui.fmt_pct(n['Has_Withdrawal'].mean() * 100) if len(n) else '—'}"),
    ("Pell avg courses", ui.fmt_num(p["COURSES"].mean(), 1) if len(p) else "—",
     f"non-Pell {ui.fmt_num(n['COURSES'].mean(), 1) if len(n) else '—'}"),
    ("Pell status missing", ui.fmt_num(f["Pell"].isna().sum()), "records"),
])
st.write("")

c1, c2 = st.columns(2)
with c1:
    dim = st.selectbox("Pell share by", ["Classification", "Level_Label", "Gender_Label", "Ethnicity",
                                         "Campus_Label", "Time_Status_Label"],
                       format_func=lambda s: s.replace("_Label", "").replace("_", " "))
    r = rate_gap(f, dim, "Is_Pell").sort_values("Rate %", ascending=False)
    fig = px.bar(r, x=dim, y="Rate %", text="Rate %", hover_data=["Students"],
                 title=f"Pell share by {dim.replace('_Label', '')}")
    fig.update_traces(marker_color=ui.PRIMARY, texttemplate="%{text:.1f}%", textposition="outside", cliponaxis=False)
    fig.add_hline(y=f["Is_Pell"].mean() * 100, line_dash="dot", line_color="#9a9994", annotation_text="overall")
    fig.update_xaxes(title=None); fig.update_yaxes(title=None); fig.update_layout(height=400)
    ui.show(fig)
with c2:
    comp = group_summary(f.dropna(subset=["Pell"]), "Pell_Label")
    m = comp.melt(id_vars="Pell_Label", value_vars=["Full-time %", "Withdrawal rate %", "Female %"],
                  var_name="Measure", value_name="Value")
    fig = px.bar(m, x="Measure", y="Value", color="Pell_Label", barmode="group", title="Pell vs non-Pell outcomes (%)",
                 text="Value")
    fig.update_traces(texttemplate="%{text:.1f}", textposition="outside", cliponaxis=False)
    fig.update_xaxes(title=None); fig.update_yaxes(title=None); fig.update_layout(height=460)
    ui.show(fig)

st.markdown(f"#### Majors with the highest Pell share (≥ {min_n} students)")
mj = group_summary(f, "Major")
mj = mj[mj["Students"] >= min_n].sort_values("Pell %", ascending=False).head(15)
fig = px.bar(mj, x="Pell %", y="Major", orientation="h", hover_data=["Students", "Withdrawal rate %"])
fig.update_traces(marker_color=ui.PRIMARY)
fig.update_yaxes(categoryorder="total ascending", title=None); fig.update_xaxes(title=None)
fig.update_layout(height=460)
ui.show(fig)

st.markdown("#### Pell recipients with withdrawals (possible aid-impact follow-up)")
lst = f[f["Is_Pell"] & f["Has_Withdrawal"]][["ZID", "Level", "Classification", "Major", "Time_Status_Label",
                                             "COURSES", "CREDIT_HOURS", "WITHDRAWALS"]] \
    .sort_values("WITHDRAWALS", ascending=False)
st.caption(f"{len(lst):,} students. Withdrawals may affect aid eligibility / return-of-funds — review with Financial Aid.")
ui.table(lst, height=340)
ui.download_csv(lst, "pell_with_withdrawals.csv")
