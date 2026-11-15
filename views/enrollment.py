import plotly.express as px
import streamlit as st

from edunexus import ui
from edunexus.metrics import group_summary, kpis, share

df, f, settings = ui.page("Enrollment", "Headcount by level, classification, student type and time status")
ui.no_data_guard(f)
k = kpis(f)
ug = (f["Level"] == "UG").sum()
ui.kpi_row([
    ("Headcount", ui.fmt_num(k["students"]), ""),
    ("Undergraduate", ui.fmt_num(ug), ui.fmt_pct(100 * ug / len(f))),
    ("Graduate / Prof.", ui.fmt_num(len(f) - ug), ui.fmt_pct(100 - 100 * ug / len(f))),
    ("Full-time", ui.fmt_pct(k["full_time_pct"]), ""),
    ("Student types", ui.fmt_num(f["Student_Type"].nunique()), "distinct codes"),
])
st.write("")

order = settings.get("order", {}).get("Classification", [])
c1, c2 = st.columns(2)
with c1:
    cl = share(f, "Classification")
    cl["o"] = cl["Classification"].map({v: i for i, v in enumerate(order)}).fillna(99)
    cl = cl.sort_values("o")
    ui.show(ui.bar(cl, "Classification", "Students", "Students by classification", text="Students"))
with c2:
    ct = (f.groupby(["Level_Label", "Time_Status_Label"]).size().reset_index(name="Students"))
    fig = px.bar(ct, x="Level_Label", y="Students", color="Time_Status_Label",
                 title="Time status within level")
    fig.update_xaxes(title=None); fig.update_yaxes(title=None)
    fig.update_layout(height=380)
    ui.show(fig)

c3, c4 = st.columns(2)
with c3:
    stp = share(f, "Student_Type_Label")
    ui.show(ui.bar(stp, "Student_Type_Label", "Students", "Students by student type code",
                   horizontal=True, text="Students", height=460))
    st.caption("Student type labels can be set on the Administration page.")
with c4:
    ug_df = f[f["Level"] == "UG"]
    if not ug_df.empty:
        fig = px.histogram(ug_df, x="Classification", color="Gender_Label", barmode="group",
                           category_orders={"Classification": order},
                           title="Undergraduate classification by gender")
        fig.update_xaxes(title=None); fig.update_yaxes(title=None); fig.update_layout(height=460)
        ui.show(fig)

st.markdown("#### Enrollment summary by level & classification")
t = group_summary(f, ["Level_Label", "Classification"])
ui.table(t, pct_cols=["Full-time %", "Pell %", "Withdrawal rate %", "Female %", "Share %"],
         num_cols=["Avg courses", "Avg credit hrs"])
ui.download_csv(t, "enrollment_summary.csv")
