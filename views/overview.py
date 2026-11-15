import streamlit as st

from edunexus import ui
from edunexus.insights import rule_based_insights
from edunexus.metrics import kpis, share
from edunexus.quality import quality_score, run_quality_checks

df, f, settings = ui.page("Executive Overview", "University Student Analytics & Insights")
ui.no_data_guard(f)
k = kpis(f)
terms = ", ".join(sorted(f["Term_Label"].unique()))
st.caption(f"Term(s): **{terms}**")

ui.kpi_row([
    ("Students", ui.fmt_num(k["students"]), f"{k['programs']} programs · {k['majors']} majors"),
    ("Full-time", ui.fmt_pct(k["full_time_pct"]), "by time status"),
    ("Pell recipients", ui.fmt_pct(k["pell_pct"]), "of enrolled students"),
    ("Withdrawal rate", ui.fmt_pct(k["withdrawal_rate"]), f"{int(k['total_withdrawals']):,} withdrawals"),
    ("Graduate / Prof.", ui.fmt_pct(k["grad_pct"]), "non-undergraduate"),
    ("Data quality", f"{quality_score(f, run_quality_checks(f, settings))}%", "rows passing key rules"),
])
st.write("")

c1, c2 = st.columns([1.3, 1])
with c1:
    lv = share(f, "Level_Label")
    ui.show(ui.bar(lv, "Level_Label", "Students", "Students by level", horizontal=True, text="Students"))
with c2:
    ts = share(f, "Time_Status_Label")
    ui.show(ui.donut(ts, "Time_Status_Label", "Students", "Time status"))

c3, c4 = st.columns([1.3, 1])
with c3:
    mj = share(f, "Major").head(12)
    ui.show(ui.bar(mj, "Major", "Students", "Top 12 majors", horizontal=True, text="Students", height=420))
with c4:
    st.markdown("#### Key insights")
    for ins in rule_based_insights(f, settings)[:6]:
        ui.insight_card(ins)
    st.page_link("views/ai_insights.py", label="See all insights →", icon="✨")
