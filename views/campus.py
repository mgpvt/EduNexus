import plotly.express as px
import streamlit as st

from edunexus import ui
from edunexus.metrics import group_summary

df, f, settings = ui.page("Campus", "Enrollment and outcomes by campus")
ui.no_data_guard(f)

summ = group_summary(f, "Campus_Label")
cols = st.columns(max(len(summ), 1))
for c, (_, r) in zip(cols, summ.iterrows()):
    c.markdown(ui.kpi(r["Campus_Label"], ui.fmt_num(r["Students"]),
                      f"{r['Share %']:.1f}% of students · {r['Full-time %']:.0f}% full-time · "
                      f"{r['Withdrawal rate %']:.1f}% withdrawal"), unsafe_allow_html=True)
st.write("")

c1, c2 = st.columns(2)
with c1:
    lv = f.groupby(["Campus_Label", "Level_Label"]).size().reset_index(name="Students")
    lv["Share %"] = lv["Students"] / lv.groupby("Campus_Label")["Students"].transform("sum") * 100
    fig = px.bar(lv, x="Share %", y="Campus_Label", color="Level_Label", orientation="h",
                 title="Level mix within campus (%)")
    fig.update_layout(height=320, barmode="stack"); fig.update_yaxes(title=None); fig.update_xaxes(title=None)
    ui.show(fig)
with c2:
    m = summ.melt(id_vars="Campus_Label", value_vars=["Full-time %", "Pell %", "Withdrawal rate %", "Female %"],
                  var_name="Measure", value_name="Value")
    fig = px.bar(m, x="Measure", y="Value", color="Campus_Label", barmode="group",
                 title="Rates by campus (%)")
    fig.update_layout(height=320); fig.update_xaxes(title=None); fig.update_yaxes(title=None)
    ui.show(fig)

st.markdown("#### Top majors per campus")
camp = st.selectbox("Campus", summ["Campus_Label"].tolist())
cm = f[f["Campus_Label"] == camp]["Major"].value_counts().head(15).reset_index()
cm.columns = ["Major", "Students"]
ui.show(ui.bar(cm, "Major", "Students", f"{camp}: top majors", horizontal=True, text="Students", height=420))

ui.table(summ, pct_cols=["Full-time %", "Pell %", "Withdrawal rate %", "Female %", "Share %"],
         num_cols=["Avg courses", "Avg credit hrs", "Total credit hrs"])
