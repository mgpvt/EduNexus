import plotly.express as px
import streamlit as st

from edunexus import ui
from edunexus.metrics import group_summary, share

df, f, settings = ui.page("Demographics", "Gender and ethnicity composition, and outcome gaps")
ui.no_data_guard(f)

ui.kpi_row([
    ("Female", ui.fmt_pct(f["Gender"].eq("F").mean() * 100), f"{f['Gender'].eq('F').sum():,} students"),
    ("Male", ui.fmt_pct(f["Gender"].eq("M").mean() * 100), f"{f['Gender'].eq('M').sum():,} students"),
    ("Hispanic", ui.fmt_pct(f["Ethnicity"].eq("Hispanic").mean() * 100), ""),
    ("Ethnicity unknown", ui.fmt_pct(f["Ethnicity"].eq("Unknown").mean() * 100), "reporting gap"),
])
st.write("")

c1, c2 = st.columns(2)
with c1:
    ui.show(ui.donut(share(f, "Gender_Label"), "Gender_Label", "Students", "Gender"))
with c2:
    ui.show(ui.donut(share(f, "Ethnicity"), "Ethnicity", "Students", "Ethnicity"))

dim = st.selectbox("Compare across", ["Level_Label", "Classification", "Major", "Campus_Label", "Pell_Label"],
                   format_func=lambda s: s.replace("_Label", "").replace("_", " "))
c3, c4 = st.columns(2)
for col, dem in [(c3, "Gender_Label"), (c4, "Ethnicity")]:
    with col:
        x = f.groupby([dim, dem]).size().reset_index(name="Students")
        if dim == "Major":
            top = f["Major"].value_counts().head(12).index
            x = x[x["Major"].isin(top)]
        x["Share %"] = x["Students"] / x.groupby(dim)["Students"].transform("sum") * 100
        fig = px.bar(x, x=dim, y="Share %", color=dem, title=f"{dem.replace('_Label', '')} mix by {dim.replace('_Label', '')}")
        fig.update_layout(barmode="stack", height=380); fig.update_xaxes(title=None); fig.update_yaxes(title=None)
        ui.show(fig)

st.markdown("#### Outcome gaps")
g1, g2 = st.columns(2)
with g1:
    t = group_summary(f, "Gender_Label")
    ui.table(t[["Gender_Label", "Students", "Full-time %", "Pell %", "Withdrawal rate %", "Avg credit hrs"]],
             pct_cols=["Full-time %", "Pell %", "Withdrawal rate %"], num_cols=["Avg credit hrs"])
with g2:
    t = group_summary(f, "Ethnicity")
    ui.table(t[["Ethnicity", "Students", "Full-time %", "Pell %", "Withdrawal rate %", "Avg credit hrs"]],
             pct_cols=["Full-time %", "Pell %", "Withdrawal rate %"], num_cols=["Avg credit hrs"])

st.markdown("#### Gender × ethnicity")
ct = f.pivot_table(index="Ethnicity", columns="Gender_Label", values="PIDM", aggfunc="count", fill_value=0)
fig = px.imshow(ct, text_auto=True, color_continuous_scale=ui.SEQ, aspect="auto")
fig.update_layout(height=300, coloraxis_showscale=False)
ui.show(fig)
