import streamlit as st

from edunexus import ui
from edunexus.insights import ai_available, ai_narrative, rule_based_insights

df, f, settings = ui.page("AI Insights", "Automatically generated findings for the current filter selection")
ui.no_data_guard(f)

ins = rule_based_insights(f, settings)
cats = sorted({i.category for i in ins})
sel = st.multiselect("Categories", cats, default=cats)
sev_rank = {"critical": 0, "warning": 1, "info": 2, "positive": 3}
c1, c2 = st.columns(2)
for idx, i in enumerate(sorted([i for i in ins if i.category in sel], key=lambda i: sev_rank.get(i.severity, 9))):
    with (c1 if idx % 2 == 0 else c2):
        ui.insight_card(i)

st.markdown("---")
st.markdown("### ✨ AI narrative")
if ai_available(settings):
    st.caption(f"Model: {settings.get('ai', {}).get('model')}. Only aggregated statistics are sent — "
               "no student identifiers or individual records.")
    q = st.text_input("Optional question for the AI analyst",
                      placeholder="e.g. Which groups should advising prioritise this term?")
    if st.button("Generate AI briefing", type="primary"):
        with st.spinner("Analysing aggregated statistics…"):
            try:
                st.session_state["ai_text"] = ai_narrative(f, settings, q or None)
            except Exception as exc:  # noqa: BLE001
                st.error(f"AI request failed: {exc}")
    if st.session_state.get("ai_text"):
        st.markdown(st.session_state["ai_text"])
else:
    st.info("The rule-based insights above are always available. To add an AI-written briefing, set the "
            "`ANTHROPIC_API_KEY` environment variable before starting EduNexus and install the "
            "`anthropic` package (see README). Only aggregated statistics are ever sent.")
