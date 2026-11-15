import plotly.express as px
import streamlit as st

from edunexus import ui
from edunexus.metrics import group_summary

df, f, settings = ui.page("Programs & Majors", "Size, mix and outcomes by program and major")
ui.no_data_guard(f)
min_n = settings.get("insights", {}).get("min_group_size", 15)

ui.kpi_row([
    ("Programs", ui.fmt_num(f["Program"].nunique()), ""),
    ("Majors", ui.fmt_num(f["Major"].nunique()), ""),
    ("Largest major", str(f["Major"].value_counts().index[0]), f"{f['Major'].value_counts().iloc[0]:,} students"),
    ("Single-student programs", ui.fmt_num((f["Program"].value_counts() == 1).sum()), ""),
])
st.write("")

view = st.radio("Group by", ["Major", "Program"], horizontal=True)
key = "Major" if view == "Major" else "Program_Name"
summ = group_summary(f, key)

c1, c2 = st.columns([1.2, 1])
with c1:
    top_n = st.slider("Show top N", 5, 40, 20)
    ui.show(ui.bar(summ.head(top_n), key, "Students", f"Top {top_n} by headcount",
                   horizontal=True, text="Students", height=max(380, top_n * 22)))
with c2:
    tm = summ.head(40)
    fig = px.treemap(tm, path=[key], values="Students", color="Withdrawal rate %",
                     color_continuous_scale=ui.SEQ, title="Headcount (size) & withdrawal rate (colour)")
    fig.update_traces(hovertemplate="%{label}<br>%{value} students<br>Withdrawal %{color:.1f}%<extra></extra>")
    fig.update_layout(height=max(380, top_n * 22), margin=dict(t=50, l=0, r=0, b=0))
    ui.show(fig)

st.markdown(f"#### Outcome comparison (groups ≥ {min_n} students)")
big = summ[summ["Students"] >= min_n]
if not big.empty:
    fig = px.scatter(big, x="Pell %", y="Withdrawal rate %", size="Students", hover_name=key,
                     title="Pell share vs withdrawal rate", size_max=40)
    fig.update_traces(marker=dict(color=ui.PRIMARY, opacity=0.75, line=dict(color="white", width=1)))
    fig.add_hline(y=f["Has_Withdrawal"].mean() * 100, line_dash="dot", line_color="#9a9994",
                  annotation_text="overall withdrawal rate")
    fig.update_layout(height=420)
    ui.show(fig)

st.markdown("#### Drill-down")
choice = st.selectbox(f"Select a {view.lower()}", summ[key].tolist())
sel = f[f[key] == choice]
a, b = st.columns(2)
with a:
    lv = sel["Classification"].value_counts().reset_index()
    lv.columns = ["Classification", "Students"]
    ui.show(ui.bar(lv, "Classification", "Students", f"{choice}: classification mix", text="Students", height=320))
with b:
    ui.kpi_row([
        ("Students", ui.fmt_num(len(sel)), ""),
        ("Pell", ui.fmt_pct(sel["Is_Pell"].mean() * 100), ""),
        ("Withdrawal", ui.fmt_pct(sel["Has_Withdrawal"].mean() * 100), ""),
    ])
    st.write("")
    ui.kpi_row([
        ("Female", ui.fmt_pct(sel["Gender"].eq("F").mean() * 100), ""),
        ("Full-time", ui.fmt_pct(sel["Is_Full_Time"].mean() * 100), ""),
        ("Avg courses", ui.fmt_num(sel["COURSES"].mean(), 1), ""),
    ])
    if view == "Major":
        st.caption("Programs in this major: " + ", ".join(sorted(sel["Program"].unique())))

st.markdown("#### Full table")
ui.table(summ, pct_cols=["Full-time %", "Pell %", "Withdrawal rate %", "Female %", "Share %"],
         num_cols=["Avg courses", "Avg credit hrs", "Total credit hrs"])
ui.download_csv(summ, f"{view.lower()}_summary.csv")
