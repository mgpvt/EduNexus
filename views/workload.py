import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from edunexus import ui
from edunexus.data import LOAD_BAND_ORDER
from edunexus.metrics import group_summary

df, f, settings = ui.page("Academic Workload", "Courses, credit hours and billed hours against credit-load policy")
ui.no_data_guard(f)
ui.caveat_banner(settings, f)
pol = settings.get("credit_policy", {})

ui.kpi_row([
    ("Avg courses", ui.fmt_num(f["COURSES"].mean(), 1), f"median {ui.fmt_num(f['COURSES'].median(), 1)}"),
    ("Avg credit hours", ui.fmt_num(f["CREDIT_HOURS"].mean(), 1), f"median {ui.fmt_num(f['CREDIT_HOURS'].median(), 1)}"),
    ("Total credit hours", ui.fmt_num(f["CREDIT_HOURS"].sum()), ""),
    ("Total billed hours", ui.fmt_num(f["BILL_HOURS"].sum()), ""),
    ("Hours per course", ui.fmt_num(f["Hours_per_Course"].median(), 1), "median"),
])
st.write("")

st.markdown(
    f"**Policy:** full-time ≥ {pol.get('full_time_min')} credits · overload above "
    f"{pol.get('overload_threshold')} needs chair & Student Accounts permission · maximum "
    f"{pol.get('max_credits')} · typical {pol.get('typical_load')}. Applies to: "
    f"{', '.join(pol.get('applies_to_levels', []))}.")

c1, c2 = st.columns(2)
with c1:
    bands = f["Load_Band"].value_counts().reindex(LOAD_BAND_ORDER).dropna().reset_index()
    bands.columns = ["Load band", "Students"]
    colors = {LOAD_BAND_ORDER[0]: ui.SEQ[2], LOAD_BAND_ORDER[1]: ui.STATUS["good"],
              LOAD_BAND_ORDER[2]: ui.STATUS["warning"], LOAD_BAND_ORDER[3]: ui.STATUS["critical"],
              LOAD_BAND_ORDER[4]: "#b8b7b1", LOAD_BAND_ORDER[5]: "#d9d8d3"}
    fig = px.bar(bands, x="Students", y="Load band", orientation="h", color="Load band",
                 color_discrete_map=colors, title="Credit-load policy bands", text="Students")
    fig.update_layout(showlegend=False, height=380)
    fig.update_yaxes(title=None, categoryorder="array", categoryarray=LOAD_BAND_ORDER[::-1])
    fig.update_xaxes(title=None)
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_xaxes(range=[0, bands["Students"].max() * 1.15])
    ui.show(fig)
with c2:
    pc = f[f["Level"].isin(pol.get("applies_to_levels", ["UG"]))]
    fig = px.histogram(pc, x="CREDIT_HOURS", nbins=60, title="Credit hours distribution (policy levels)")
    fig.update_traces(marker_color=ui.PRIMARY)
    for v, name, col in [(pol.get("full_time_min"), "FT min", ui.STATUS["good"]),
                         (pol.get("overload_threshold"), "Overload", ui.STATUS["serious"]),
                         (pol.get("max_credits"), "Max", ui.STATUS["critical"])]:
        fig.add_vline(x=v, line_dash="dash", line_color=col)
    fig.update_xaxes(title="Credit hours"); fig.update_yaxes(title="Students")
    fig.update_layout(height=380)
    ui.show(fig)
    st.caption(f"Dashed lines: full-time minimum ({pol.get('full_time_min')}), overload "
               f"({pol.get('overload_threshold')}), maximum ({pol.get('max_credits')}).")

c3, c4 = st.columns(2)
with c3:
    lv = group_summary(f, "Level_Label")
    ui.show(ui.bar(lv, "Level_Label", "Avg credit hrs", "Average credit hours by level", text="Avg credit hrs"))
with c4:
    fig = px.box(f, x="Time_Status_Label", y="COURSES", title="Courses by time status", points=False)
    fig.update_traces(marker_color=ui.PRIMARY, line_color=ui.PRIMARY)
    fig.update_xaxes(title=None); fig.update_yaxes(title="Courses"); fig.update_layout(height=380)
    ui.show(fig)

st.markdown("#### Credit vs billed hours")
mis = f[(f["CREDIT_HOURS"] - f["BILL_HOURS"]).abs() > 0]
st.caption(f"{len(mis):,} students have credit hours different from billed hours.")
if not mis.empty:
    fig = go.Figure(go.Scattergl(x=mis["CREDIT_HOURS"], y=mis["BILL_HOURS"], mode="markers",
                                 marker=dict(size=8, color=ui.PRIMARY, line=dict(color="white", width=1)),
                                 text=mis["ZID"],
                                 hovertemplate="%{text}<br>Credit %{x}<br>Billed %{y}<extra></extra>"))
    mx = float(max(mis["CREDIT_HOURS"].max(), mis["BILL_HOURS"].max()))
    fig.add_trace(go.Scatter(x=[0, mx], y=[0, mx], mode="lines", line=dict(dash="dot", color="#9a9994"),
                             name="Credit = Billed", hoverinfo="skip"))
    fig.update_layout(height=380, showlegend=False, xaxis_title="Credit hours", yaxis_title="Billed hours")
    ui.show(fig)

st.markdown("#### Workload by major")
t = group_summary(f, "Major")[["Major", "Students", "Avg courses", "Avg credit hrs", "Total credit hrs", "Full-time %"]]
ui.table(t, pct_cols=["Full-time %"], num_cols=["Avg courses", "Avg credit hrs", "Total credit hrs"])
ui.download_csv(t, "workload_by_major.csv")
