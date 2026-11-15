"""EduNexus - University Student Analytics & Insights.

Run with:  streamlit run app.py
"""
import streamlit as st

from edunexus.auth import is_admin, logout_button, require_login
from edunexus.ui import setup_page

setup_page("EduNexus", "🎓")
require_login()

V = "views/"
pages = {
    "Overview": [
        st.Page(V + "overview.py", title="Executive Overview", icon="🏠", default=True),
        st.Page(V + "ai_insights.py", title="AI Insights", icon="✨"),
    ],
    "Analytics": [
        st.Page(V + "enrollment.py", title="Enrollment", icon="👥"),
        st.Page(V + "workload.py", title="Academic Workload", icon="📚"),
        st.Page(V + "programs.py", title="Programs & Majors", icon="🎓"),
        st.Page(V + "campus.py", title="Campus", icon="🏛️"),
        st.Page(V + "demographics.py", title="Demographics", icon="🧑‍🤝‍🧑"),
        st.Page(V + "withdrawals.py", title="Withdrawals", icon="↩️"),
        st.Page(V + "financial_aid.py", title="Pell & Financial Aid", icon="💵"),
        st.Page(V + "trends.py", title="Term Trends", icon="📈"),
    ],
    "Students": [
        st.Page(V + "student_search.py", title="Student Search", icon="🔎"),
    ],
    "Governance": [
        st.Page(V + "data_quality.py", title="Data Quality", icon="🩺"),
    ] + ([st.Page(V + "admin.py", title="Administration", icon="⚙️")] if is_admin() else []),
}

st.sidebar.markdown("## 🎓 EduNexus")
st.sidebar.caption("Student Analytics & Insights")
logout_button()
nav = st.navigation(pages, position="top")
nav.run()
