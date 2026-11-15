import sqlite3
from pathlib import Path

import pandas as pd
import pytest

from edunexus.config import load_settings
from edunexus.data import load_students, standardise
from edunexus.insights import build_ai_payload, rule_based_insights
from edunexus.metrics import group_summary, kpis, term_trend
from edunexus.quality import quality_score, run_quality_checks


ORIGINAL = Path(__file__).parent.parent / "data" / "TestStudents.xlsx"
pytestmark_local = pytest.mark.skipif(not ORIGINAL.exists(), reason="original data is local-only")


@pytest.fixture(scope="module")
def settings():
    """Core tests run against the ORIGINAL upload so data-quality expectations stay fixed."""
    s = load_settings()
    s["data_source"]["type"] = "excel"
    s["data_source"]["excel"] = {"path": "data/TestStudents.xlsx", "sheet": 0, "demo": False}
    return s


@pytest.fixture(scope="module")
def df(settings):
    d, _ = load_students(settings)
    return d


@pytestmark_local
def test_load_shape(df):
    assert len(df) == 2400
    assert df["PIDM"].is_unique
    assert df["Campus"].isin(["1", "X"]).all()
    assert set(df["Student_Type"].dropna()) >= {"F", "7"}  # numeric codes normalised to text


@pytestmark_local
def test_kpis(df):
    k = kpis(df)
    assert k["students"] == 2400
    assert 0 < k["pell_pct"] < 100
    assert round(k["female_pct"], 1) == round(1448 / 2400 * 100, 1)


@pytestmark_local
def test_group_summary_sums(df):
    g = group_summary(df, "Level")
    assert g["Students"].sum() == len(df)


@pytestmark_local
def test_quality(df, settings):
    res = {r.rule: r for r in run_quality_checks(df, settings)}
    assert res["Missing values"].count == 1
    assert res["Duplicate student-term"].count == 0
    assert res["Credit vs billed hours mismatch"].count == 111  # excludes the one fully-blank row
    assert 0 <= quality_score(df, list(res.values())) <= 100


@pytestmark_local
def test_insights(df, settings):
    ins = rule_based_insights(df, settings)
    assert any(i.category == "Data quality" for i in ins)
    payload = build_ai_payload(df, settings)
    assert "ZID" not in str(payload) and "PIDM" not in str(payload.keys())


@pytestmark_local
def test_trend_multi_term(df, settings):
    d2 = df.copy(); d2["TERM"] = "202210"; d2["Term_Label"] = "Spring 2022"
    t = term_trend(pd.concat([df, d2]))
    assert len(t) == 2


@pytestmark_local
def test_database_source_equivalent(tmp_path: Path, settings):
    raw = pd.read_excel(Path(__file__).parent.parent / "data" / "TestStudents.xlsx")
    db = tmp_path / "t.db"
    with sqlite3.connect(db) as con:
        raw.to_sql("student_term_enrollment", con, index=False)
    s = dict(settings)
    s["data_source"] = {"type": "database", "database": {"url": f"sqlite:///{db}", "url_env": "NOPE_UNSET",
                                                         "table": "student_term_enrollment", "query": ""}}
    d, desc = load_students(s)
    x, _ = load_students(settings)
    assert len(d) == len(x)
    assert d["Campus"].tolist() == x["Campus"].tolist()
    assert d["CREDIT_HOURS"].sum() == pytest.approx(x["CREDIT_HOURS"].sum())


def test_missing_column_raises(settings):
    with pytest.raises(ValueError):
        standardise(pd.DataFrame({"TERM": [1]}), settings)


@pytestmark_local
def test_demo_data_follows_policy(settings):
    s = dict(settings)
    s["data_source"] = {"type": "excel", "excel": {"path": "data/TestStudents_demo.xlsx", "sheet": 0, "demo": True}}
    demo, _ = load_students(s)
    orig, _ = load_students(settings)
    ug = demo[demo["Level"] == "UG"]
    assert (ug["CREDIT_HOURS"].dropna() <= 24).all()
    ft = ug[ug["Is_Full_Time"]]
    assert (ft["CREDIT_HOURS"].dropna() >= 12).all()
    v = demo.dropna(subset=["COURSES"])
    assert (v["WITHDRAWALS"] <= v["COURSES"]).all()
    # identity and demographic fields untouched
    for c in ["PIDM", "ZID", "Major", "Program", "Gender", "Ethnicity", "Pell", "Time_Status"]:
        assert demo[c].fillna("").tolist() == orig[c].fillna("").tolist()
    # same students withdraw
    assert demo["Has_Withdrawal"].tolist() == orig["Has_Withdrawal"].tolist()


@pytestmark_local
def test_demo_generator_is_reproducible(tmp_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location("mk", Path(__file__).parent.parent / "scripts" / "make_demo_data.py")
    mk = importlib.util.module_from_spec(spec); spec.loader.exec_module(mk)
    a = mk.build(out=tmp_path / "a.xlsx"); b = mk.build(out=tmp_path / "b.xlsx")
    assert a["CREDIT_HOURS"].fillna(-1).tolist() == b["CREDIT_HOURS"].fillna(-1).tolist()


PUBLIC = Path(__file__).parent.parent / "data" / "EduNexus_public_demo.xlsx"


def test_public_demo_has_no_original_ids():
    pub = pd.read_excel(PUBLIC)
    assert len(pub) == 2400 and pub["PIDM"].is_unique and pub["ZID"].is_unique
    assert pub["ZID"].str.match(r"^Z9\d{7}$").all()
    if ORIGINAL.exists():
        orig = pd.read_excel(ORIGINAL)
        assert not set(pub["ZID"]) & set(orig["ZID"].astype(str))
        assert not set(pub["PIDM"]) & set(orig["PIDM"])


def test_public_demo_loads_with_default_settings():
    df, _ = load_students(load_settings())
    assert len(df) == 2400
    ug = df[df["Level"] == "UG"]
    assert (ug["CREDIT_HOURS"].dropna() <= 24).all()
