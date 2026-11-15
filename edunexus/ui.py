"""Shared Streamlit UI: theme, data loading, global filters, KPI tiles, chart helpers."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

from .config import load_settings
from .data.repository import load_students

# Validated categorical palette (fixed order - never cycled, colour follows entity)
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
SEQ = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
DIVERGING = ["#256abf", "#86b6ef", "#f0efec", "#f1a3a2", "#d03b3b"]
STATUS = {"good": "#0ca30c", "warning": "#fab219", "serious": "#ec835a", "critical": "#d03b3b"}
PRIMARY = "#2a78d6"
TEXT = "#0b0b0b"
TEXT2 = "#52514e"
GRID = "#e8e7e3"

pio.templates["edunexus"] = go.layout.Template(
    layout=dict(
        font=dict(family="Inter, Segoe UI, system-ui, sans-serif", size=13, color=TEXT2),
        title=dict(font=dict(size=15, color=TEXT), x=0, xanchor="left"),
        colorway=SERIES,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(gridcolor=GRID, linecolor=GRID, zeroline=False, ticks=""),
        yaxis=dict(gridcolor=GRID, linecolor=GRID, zeroline=False, ticks=""),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, title_text=""),
        margin=dict(l=10, r=10, t=50, b=10),
        hoverlabel=dict(bgcolor="white", font_size=12, bordercolor=GRID),
        bargap=0.25, barcornerradius=4,
    )
)
pio.templates.default = "edunexus"

CSS = """
<style>
.block-container {padding-top: 3.2rem; padding-bottom: 2rem; max-width: 1400px;}
h1, h2, h3 {letter-spacing: -0.01em;}
.en-header {display:flex; align-items:center; gap:.8rem; margin-bottom:.3rem;}
.en-logo {width:40px;height:40px;border-radius:10px;background:linear-gradient(135deg,#2a78d6,#104281);
  color:#fff;font-weight:700;display:flex;align-items:center;justify-content:center;font-size:18px;}
.en-title {font-size:1.6rem;font-weight:700;color:#0b0b0b;line-height:1.1;}
.en-sub {color:#52514e;font-size:.92rem;}
.en-kpi {background:#fff;border:1px solid #e8e7e3;border-radius:12px;padding:14px 16px;height:100%;}
.en-kpi .lbl {color:#52514e;font-size:.78rem;text-transform:uppercase;letter-spacing:.04em;font-weight:600;}
.en-kpi .val {color:#0b0b0b;font-size:1.65rem;font-weight:700;margin-top:2px;}
.en-kpi .sub {color:#6b6a66;font-size:.8rem;margin-top:2px;}
.en-insight {border:1px solid #e8e7e3;border-left:4px solid var(--c);border-radius:10px;padding:10px 14px;
  margin-bottom:10px;background:#fff;}
.en-insight .t {font-weight:650;color:#0b0b0b;}
.en-insight .cat {font-size:.72rem;color:#52514e;text-transform:uppercase;letter-spacing:.05em;}
.en-insight .d {color:#3a3936;font-size:.92rem;margin-top:2px;}
.en-pill {display:inline-block;padding:2px 8px;border-radius:999px;font-size:.75rem;font-weight:600;
  background:#f0efec;color:#3a3936;margin-right:4px;}
.en-banner {background:#fff7e6;border:1px solid #f5d48a;border-radius:10px;padding:10px 14px;color:#5a4300;
  font-size:.9rem;margin-bottom:12px;}
.en-demo {background:#eef4fd;border:1px dashed #2a78d6;border-radius:10px;padding:8px 14px;color:#104281;
  font-size:.88rem;margin-bottom:12px;}
[data-testid="stSidebar"] {background:#f7f7f5;}
</style>
"""


def setup_page(title: str, icon: str = "📊") -> None:
    st.set_page_config(page_title=title, page_icon=icon, layout="wide")
    st.markdown(CSS, unsafe_allow_html=True)


def is_demo(settings: dict) -> bool:
    ds = settings.get("data_source", {})
    return ds.get("type") == "excel" and bool(ds.get("excel", {}).get("demo"))


def page(title: str, subtitle: str = "", filters: bool = True):
    """Standard page prologue: header + data + global filters."""
    header(title, subtitle)
    df, desc, settings = get_data()
    if is_demo(settings):
        from .auth import is_admin
        tail = ("Switch to real data under <b>Administration → Data source</b>." if is_admin()
                else "Student IDs and workload figures are made up for testing.")
        st.markdown(
            '<div class="en-demo">🧪 <b>DEMO DATA</b> — workload figures (courses, credit, billed hours, '
            f'withdrawal counts) are synthetic and policy-compliant. Not for reporting. {tail}</div>',
            unsafe_allow_html=True)
    fdf = sidebar_filters(df) if filters else df
    st.sidebar.caption(f"Source: {desc}")
    return df, fdf, settings


def header(title: str, subtitle: str = "") -> None:
    st.markdown(
        f"""<div class="en-header"><div class="en-logo">E</div><div>
        <div class="en-title">{title}</div><div class="en-sub">{subtitle}</div></div></div>""",
        unsafe_allow_html=True,
    )


@st.cache_data(ttl=900, show_spinner="Loading student data…")
def _cached_load(_settings_key: str) -> tuple[pd.DataFrame, str]:
    return load_students(load_settings())


def get_settings() -> dict:
    return load_settings()


def get_data() -> tuple[pd.DataFrame, str, dict]:
    settings = get_settings()
    key = str(settings.get("data_source"))
    try:
        df, desc = _cached_load(key)
    except Exception as exc:  # noqa: BLE001
        st.error(f"Could not load data: {exc}")
        st.info("Check the data source on the **Administration** page.")
        st.stop()
    return df, desc, settings


def clear_cache() -> None:
    _cached_load.clear()


FILTERS = [
    ("TERM", "Term", "Term_Label"),
    ("Level", "Level", "Level_Label"),
    ("Classification", "Classification", None),
    ("Campus", "Campus", "Campus_Label"),
    ("Time_Status", "Time status", "Time_Status_Label"),
    ("Gender", "Gender", "Gender_Label"),
    ("Ethnicity", "Ethnicity", None),
    ("Pell", "Pell", "Pell_Label"),
    ("Major", "Major", None),
]


def sidebar_filters(df: pd.DataFrame) -> pd.DataFrame:
    """Global filters, persisted across pages via session_state."""
    st.sidebar.markdown("### Filters")
    out = df
    for col, name, lbl in FILTERS:
        opts = sorted(df[col].dropna().unique().tolist(), key=str)
        if len(opts) < 2 and col != "TERM":
            continue
        fmt = (lambda v, lbl=lbl: f"{df.loc[df[col] == v, lbl].iloc[0]}") if lbl else str
        key = f"flt_{col}"
        sel = st.sidebar.multiselect(name, opts, key=key, format_func=fmt, placeholder="All")
        if sel:
            out = out[out[col].isin(sel)]
    if st.sidebar.button("Reset filters", use_container_width=True):
        for col, _, _ in FILTERS:
            st.session_state.pop(f"flt_{col}", None)
        st.rerun()
    st.sidebar.caption(f"Showing **{len(out):,}** of {len(df):,} student records")
    return out


def kpi(label: str, value: str, sub: str = "") -> str:
    return f'<div class="en-kpi"><div class="lbl">{label}</div><div class="val">{value}</div><div class="sub">{sub}</div></div>'


def kpi_row(items: list[tuple[str, str, str]]) -> None:
    cols = st.columns(len(items))
    for c, (l, v, s) in zip(cols, items):
        c.markdown(kpi(l, v, s), unsafe_allow_html=True)


SEV_COLOR = {"info": PRIMARY, "positive": STATUS["good"], "warning": STATUS["serious"],
             "critical": STATUS["critical"]}
SEV_ICON = {"info": "ℹ️", "positive": "✅", "warning": "⚠️", "critical": "⛔"}


def insight_card(ins) -> None:
    st.markdown(
        f'<div class="en-insight" style="--c:{SEV_COLOR.get(ins.severity, PRIMARY)}">'
        f'<div class="cat">{SEV_ICON.get(ins.severity, "")} {ins.category} · {ins.severity}</div>'
        f'<div class="t">{ins.title}</div><div class="d">{ins.detail}</div></div>',
        unsafe_allow_html=True,
    )


def no_data_guard(df: pd.DataFrame) -> None:
    if df.empty:
        st.warning("No students match the current filters.")
        st.stop()


# ---------------- chart helpers ----------------
def bar(df, x, y, title="", horizontal=False, color=None, text=None, height=380, **kw):
    if horizontal:
        fig = px.bar(df, x=y, y=x, orientation="h", color=color, title=title, text=text, **kw)
        fig.update_yaxes(categoryorder="total ascending", title=None)
        fig.update_xaxes(title=None)
    else:
        fig = px.bar(df, x=x, y=y, color=color, title=title, text=text, **kw)
        fig.update_xaxes(title=None)
        fig.update_yaxes(title=None)
    if color is None:
        fig.update_traces(marker_color=PRIMARY)
    if text:
        fmt = "%{text:,.1f}" if df[text].dtype.kind == "f" and (df[text] % 1 != 0).any() else "%{text:,.0f}"
        fig.update_traces(texttemplate=fmt, textposition="outside", cliponaxis=False,
                          textfont_color=TEXT2)
        mx = float(df[y].max() or 0) * 1.15
        (fig.update_xaxes if horizontal else fig.update_yaxes)(range=[0, mx])
    fig.update_layout(height=height, showlegend=color is not None)
    return fig


def donut(df, names, values, title="", height=340, colors=None):
    fig = px.pie(df, names=names, values=values, hole=0.62, title=title,
                 color_discrete_sequence=colors or SERIES)
    fig.update_traces(textinfo="percent", textposition="inside", insidetextorientation="horizontal",
                      marker=dict(line=dict(color="white", width=2)),
                      hovertemplate="%{label}<br>%{value:,} students (%{percent})<extra></extra>")
    fig.update_layout(height=height, legend=dict(orientation="v", y=0.5, x=1.0),
                      uniformtext_minsize=11, uniformtext_mode="hide")
    return fig


def show(fig) -> None:
    st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})


def download_csv(df: pd.DataFrame, name: str, label: str = "⬇ Download CSV") -> None:
    st.download_button(label, df.to_csv(index=False).encode("utf-8"), file_name=name, mime="text/csv")


def fmt_pct(x, d=1):
    return "—" if pd.isna(x) else f"{x:.{d}f}%"


def fmt_num(x, d=0):
    return "—" if pd.isna(x) else f"{x:,.{d}f}"


def caveat_banner(settings: dict, df: pd.DataFrame) -> None:
    """Shown on workload pages when hours look non-term (e.g. cumulative)."""
    pol = settings.get("credit_policy", {})
    sub = df[df["Level"].isin(pol.get("applies_to_levels", ["UG"]))]
    if sub.empty:
        return
    over = (sub["CREDIT_HOURS"] > pol.get("max_credits", 24)).mean() * 100
    if over > 5:
        st.markdown(
            f'<div class="en-banner">⚠️ <b>Data caveat:</b> {over:.1f}% of policy-checked records exceed '
            f'the {pol.get("max_credits", 24)}-credit term maximum. CREDIT_HOURS / COURSES in the source '
            f'appear to be cumulative or mis-scaled. Values are shown as supplied - see '
            f'<b>Data Quality</b>.</div>', unsafe_allow_html=True)


def table(df: pd.DataFrame, pct_cols=(), num_cols=(), height=None) -> None:
    cfg = {c: st.column_config.NumberColumn(c, format="%.1f%%") for c in pct_cols if c in df}
    cfg.update({c: st.column_config.NumberColumn(c, format="%.1f") for c in num_cols if c in df})
    kw = {"height": height} if height else {}
    st.dataframe(df, use_container_width=True, hide_index=True, column_config=cfg, **kw)
