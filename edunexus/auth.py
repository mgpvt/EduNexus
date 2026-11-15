"""Simple password login for hosted deployments.

Login is switched ON only when an [auth] section exists in Streamlit secrets
(.streamlit/secrets.toml locally, or the Secrets box on Streamlit Community Cloud):

    [auth]
    viewer_password = "tester-password"
    admin_password  = "admin-password"

Without it (normal local use) the app opens directly with full admin rights.
Roles:  viewer -> all dashboards;  admin -> dashboards + Administration page.
"""
from __future__ import annotations

import hmac

import streamlit as st


def _auth_cfg() -> dict:
    try:
        return dict(st.secrets.get("auth", {}))
    except Exception:  # noqa: BLE001  (no secrets file)
        return {}


def auth_enabled() -> bool:
    cfg = _auth_cfg()
    return bool(cfg.get("viewer_password") or cfg.get("admin_password"))


def role() -> str:
    if not auth_enabled():
        return "admin"
    return st.session_state.get("en_role", "")


def is_admin() -> bool:
    return role() == "admin"


def _check(pw: str) -> str:
    cfg = _auth_cfg()
    for r in ("admin", "viewer"):
        secret = str(cfg.get(f"{r}_password", ""))
        if secret and hmac.compare_digest(pw.encode(), secret.encode()):
            return r
    return ""


def require_login() -> None:
    """Show a login form and stop the script until the user is signed in."""
    if not auth_enabled() or role():
        return
    _, mid, _ = st.columns([1, 1.2, 1])
    with mid:
        st.markdown(
            '<div style="text-align:center;margin-top:8vh"><div class="en-logo" '
            'style="margin:0 auto 12px;width:56px;height:56px;font-size:26px">E</div>'
            '<div class="en-title">EduNexus</div>'
            '<div class="en-sub">University Student Analytics &amp; Insights — test environment</div></div>',
            unsafe_allow_html=True)
        with st.form("login"):
            pw = st.text_input("Access password", type="password")
            ok = st.form_submit_button("Sign in", type="primary", use_container_width=True)
        if ok:
            r = _check(pw)
            if r:
                st.session_state["en_role"] = r
                st.rerun()
            else:
                st.error("Incorrect password.")
        st.caption("This test site uses synthetic demo data only.")
    st.stop()


def logout_button() -> None:
    if auth_enabled() and role():
        st.sidebar.caption(f"Signed in as **{role()}**")
        if st.sidebar.button("Sign out", use_container_width=True):
            st.session_state.pop("en_role", None)
            st.rerun()
