import streamlit as st

from edunexus import ui

df, f, settings = ui.page("Student Search", "Find a student and drill into their record")

q = st.text_input("Search by ZID, PIDM, program or major", placeholder="e.g. a ZID, NUR, Psychology")
cols = ["ZID", "PIDM", "Term_Label", "Level", "Classification", "Major", "Program", "Program_Name",
        "Campus_Label", "Time_Status_Label", "Gender", "Ethnicity", "Pell", "COURSES", "CREDIT_HOURS",
        "BILL_HOURS", "WITHDRAWALS", "Load_Band"]
res = f
if q:
    s = q.strip().lower()
    mask = False
    for c in ["ZID", "PIDM", "Major", "Program", "Program_Name"]:
        mask = mask | res[c].astype(str).str.lower().str.contains(s, regex=False)
    res = res[mask]

st.caption(f"{len(res):,} matching records")
event = st.dataframe(res[cols], use_container_width=True, hide_index=True, height=360,
                     on_select="rerun", selection_mode="single-row")
ui.download_csv(res[cols], "student_search.csv")

rows = event.selection.rows if event and hasattr(event, "selection") else []
if rows:
    r = res.iloc[rows[0]]
elif len(res) == 1:
    r = res.iloc[0]
else:
    st.info("Select a row to see the student profile.")
    st.stop()

st.markdown("---")
st.markdown(f"### 🎓 {r['ZID']}  <span class='en-pill'>PIDM {r['PIDM']}</span>"
            f"<span class='en-pill'>{r['Term_Label']}</span>", unsafe_allow_html=True)
ui.kpi_row([
    ("Level", r["Level_Label"], r["Classification"]),
    ("Program", r["Program_Name"], f"{r['Program']} · Major {r['Major']}"),
    ("Time status", r["Time_Status_Label"], r["Load_Band"]),
    ("Pell", r["Pell_Label"] if r["Pell"] else "Unknown", ""),
])
st.write("")
ui.kpi_row([
    ("Courses", ui.fmt_num(r["COURSES"]), ""),
    ("Credit hours", ui.fmt_num(r["CREDIT_HOURS"], 1), ""),
    ("Billed hours", ui.fmt_num(r["BILL_HOURS"], 1), ""),
    ("Withdrawals", ui.fmt_num(r["WITHDRAWALS"]), ""),
])

# Peer comparison
peers = df[(df["Major"] == r["Major"]) & (df["TERM"] == r["TERM"])]
st.markdown(f"#### Compared with {len(peers):,} peers in major {r['Major']}")
cmp = {
    "Measure": ["Courses", "Credit hours", "Withdrawals"],
    "Student": [r["COURSES"], r["CREDIT_HOURS"], r["WITHDRAWALS"]],
    "Peer average": [peers["COURSES"].mean(), peers["CREDIT_HOURS"].mean(), peers["WITHDRAWALS"].mean()],
    "Peer percentile": [
        (peers["COURSES"] <= r["COURSES"]).mean() * 100,
        (peers["CREDIT_HOURS"] <= r["CREDIT_HOURS"]).mean() * 100,
        (peers["WITHDRAWALS"] <= r["WITHDRAWALS"]).mean() * 100,
    ],
}
import pandas as pd  # noqa: E402

ui.table(pd.DataFrame(cmp), pct_cols=["Peer percentile"], num_cols=["Student", "Peer average"])

flags = []
pol = settings.get("credit_policy", {})
if r["Level"] in pol.get("applies_to_levels", ["UG"]) and pd.notna(r["CREDIT_HOURS"]):
    if r["CREDIT_HOURS"] > pol.get("max_credits", 24):
        flags.append("⛔ Credit hours exceed the term maximum")
    elif r["CREDIT_HOURS"] > pol.get("overload_threshold", 18.5):
        flags.append("⚠️ Overload — requires chair & Student Accounts permission")
if r["CREDIT_HOURS"] != r["BILL_HOURS"]:
    flags.append("⚠️ Credit hours differ from billed hours")
if r["WITHDRAWALS"] and r["WITHDRAWALS"] > 0:
    flags.append(f"↩️ {int(r['WITHDRAWALS'])} withdrawal(s)" + (" — Pell recipient" if r["Pell"] == "Y" else ""))
if flags:
    st.markdown("#### Flags")
    for fl in flags:
        st.markdown(f"- {fl}")
