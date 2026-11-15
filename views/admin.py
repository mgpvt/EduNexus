import os

import pandas as pd
import streamlit as st

from edunexus import ui
from edunexus.auth import is_admin
from edunexus.config import PROJECT_ROOT, deep_copy, save_settings
from edunexus.data.sources import build_source

if not is_admin():
    st.error("Administration is available to administrators only.")
    st.stop()

df, f, settings = ui.page("Administration", "Data source, policy thresholds, code labels and cache", filters=False)
new = deep_copy(settings)

tab1, tab2, tab3, tab4 = st.tabs(["🔌 Data source", "📏 Policy & thresholds", "🏷️ Code labels", "🧰 System"])

with tab1:
    ds = new["data_source"]
    ds["type"] = st.radio("Source type", ["excel", "database"], index=0 if ds.get("type") == "excel" else 1,
                          horizontal=True)
    if ds["type"] == "excel":
        datasets = new.setdefault("datasets", [])
        datasets[:] = [d for d in datasets if (PROJECT_ROOT / d["path"]).exists()]
        if datasets:
            names = [d["name"] for d in datasets]
            cur = next((i for i, d in enumerate(datasets) if d["path"] == ds["excel"]["path"]), None)
            choice = st.radio("Dataset", names + (["Custom path"] if cur is None else []),
                              index=cur if cur is not None else len(names))
            if choice in names:
                d = datasets[names.index(choice)]
                ds["excel"]["path"], ds["excel"]["demo"] = d["path"], bool(d.get("demo"))
                st.caption(("🧪 Synthetic demo data — not for reporting." if d.get("demo")
                            else "✅ Real data — results are reportable.") + f"  `{d['path']}`")
                if cur is None or names.index(choice) != cur:
                    if st.button(f"Apply: switch to “{choice}”", type="primary"):
                        save_settings(new)
                        ui.clear_cache()
                        st.rerun()
        with st.expander("Advanced: custom path / sheet"):
            ds["excel"]["path"] = st.text_input("Workbook path (relative to app folder or absolute)", ds["excel"]["path"])
            ds["excel"]["sheet"] = st.text_input("Sheet (index or name)", str(ds["excel"].get("sheet", 0)))
            ds["excel"]["demo"] = st.checkbox("This file is demo / synthetic data", bool(ds["excel"].get("demo")))
        if str(ds["excel"]["sheet"]).isdigit():
            ds["excel"]["sheet"] = int(ds["excel"]["sheet"])
        up = st.file_uploader("Upload real data (corrected extract) — same 18 columns",
                              type=["xlsx", "xls", "csv"])
        if up is not None:
            dest = PROJECT_ROOT / "data" / up.name
            dest.write_bytes(up.getbuffer())
            ds["excel"]["path"], ds["excel"]["demo"] = f"data/{up.name}", False
            if not any(d["path"] == f"data/{up.name}" for d in datasets):
                datasets.insert(0, {"name": f"Real data - {up.name}", "path": f"data/{up.name}", "demo": False})
            ok, msg = build_source(new).test_connection()
            (st.success if ok else st.error)(f"Saved to data/{up.name} — {msg}. Click **Save settings** to switch to it.")
    else:
        db = ds["database"]
        st.caption("Any SQLAlchemy URL works (PostgreSQL, SQL Server, Oracle, MySQL, SQLite). "
                   "Install the matching driver, e.g. `pip install psycopg2-binary` or `pyodbc`.")
        db["url_env"] = st.text_input("Environment variable holding the URL (recommended)", db.get("url_env", "EDUNEXUS_DB_URL"))
        st.caption(f"Env var currently {'**set** ✅' if os.environ.get(db['url_env']) else '**not set**'}")
        db["url"] = st.text_input("…or URL stored in settings (not recommended for passwords)", db.get("url", ""),
                                  type="password")
        db["table"] = st.text_input("Table / view", db.get("table", ""))
        db["query"] = st.text_area("Custom SQL (overrides table)", db.get("query", ""), height=100)
    st.markdown("##### Column mapping")
    st.caption("Map each standard field to the column name in your source.")
    cm = pd.DataFrame({"Standard field": list(new["columns"].keys()), "Source column": list(new["columns"].values())})
    cm = st.data_editor(cm, hide_index=True, disabled=["Standard field"], use_container_width=True)
    new["columns"] = dict(zip(cm["Standard field"], cm["Source column"]))

    if st.button("Test connection"):
        ok, msg = build_source(new).test_connection()
        (st.success if ok else st.error)(msg)

with tab2:
    pol = new["credit_policy"]
    c1, c2 = st.columns(2)
    pol["full_time_min"] = c1.number_input("Full-time minimum credits", 0.0, 40.0, float(pol["full_time_min"]), 0.5)
    pol["overload_threshold"] = c2.number_input("Overload threshold (needs permission)", 0.0, 40.0,
                                                float(pol["overload_threshold"]), 0.5)
    pol["max_credits"] = c1.number_input("Maximum credits per term", 0.0, 60.0, float(pol["max_credits"]), 0.5)
    pol["typical_load"] = c2.number_input("Typical load", 0.0, 40.0, float(pol["typical_load"]), 0.5)
    pol["applies_to_levels"] = st.multiselect("Levels the policy applies to", sorted(df["Level"].dropna().unique()),
                                              default=[l for l in pol["applies_to_levels"] if l in set(df["Level"])])
    st.markdown("##### Data quality & insight thresholds")
    dq, ins = new["data_quality"], new["insights"]
    c3, c4 = st.columns(2)
    dq["max_courses_per_term"] = c3.number_input("Max courses per term", 1, 50, int(dq["max_courses_per_term"]))
    dq["max_withdrawals_flag"] = c4.number_input("Flag students with withdrawals above", 0, 50, int(dq["max_withdrawals_flag"]))
    ins["high_withdrawal_rate_pct"] = c3.number_input("High withdrawal rate (%)", 0.0, 100.0,
                                                      float(ins["high_withdrawal_rate_pct"]), 1.0)
    ins["min_group_size"] = c4.number_input("Minimum group size for rankings", 1, 500, int(ins["min_group_size"]))
    st.markdown("##### AI")
    new["ai"]["enabled"] = st.toggle("Enable AI narrative (needs API key)", new["ai"].get("enabled", True))
    new["ai"]["model"] = st.text_input("Model", new["ai"].get("model", "claude-sonnet-5-5"))

with tab3:
    st.caption("Labels marked “(verify)” are assumptions — confirm with the Registrar. Codes found in the data "
               "but not labelled are listed so you can add them.")
    field = st.selectbox("Field", ["Level", "Classification", "Time_Status", "Student_Type", "Campus", "Gender", "Pell", "Term"])
    current = new["labels"].get(field) or {}
    codes = sorted(set(map(str, current.keys())) |
                   (set(df[field].dropna().astype(str)) if field in df else set()), key=str)
    if field == "Term":
        codes = sorted(set(map(str, current.keys())) | {t[4:] for t in df["TERM"].dropna().astype(str)})
    counts = df[field].astype(str).value_counts() if field in df else pd.Series(dtype=int)
    ed = pd.DataFrame({"Code": codes, "Label": [current.get(c, "") for c in codes],
                       "Records": [int(counts.get(c, 0)) for c in codes]})
    ed = st.data_editor(ed, hide_index=True, disabled=["Code", "Records"], use_container_width=True, key=f"lbl_{field}")
    new["labels"][field] = {r.Code: r.Label for r in ed.itertuples() if str(r.Label).strip()}

with tab4:
    st.write(f"**App folder:** `{PROJECT_ROOT}`")
    st.write(f"**Rows loaded:** {len(df):,}")
    if st.button("🔄 Reload data (clear cache)"):
        ui.clear_cache()
        st.success("Cache cleared — data will reload.")
        st.rerun()

st.markdown("---")
if st.button("💾 Save settings", type="primary"):
    save_settings(new)
    ui.clear_cache()
    st.success("Settings saved to config/settings.yaml and data reloaded.")
    st.rerun()
