"""Smoke-test every page headlessly through the real app router (app.py)."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).parent.parent
PAGES = sorted(p.name for p in (ROOT / "views").glob("*.py"))


@pytest.mark.parametrize("page", PAGES)
def test_page_renders(page, monkeypatch):
    monkeypatch.chdir(ROOT)
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=90)
    at.run()
    at.switch_page(f"views/{page}")
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert len(at.markdown) > 0


def test_filters_apply(monkeypatch):
    monkeypatch.chdir(ROOT)
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=90)
    at.run()
    lvl = next(m for m in at.sidebar.multiselect if m.label == "Level")
    lvl.set_value(["GR"]).run()
    assert not at.exception
    assert any("205" in c.value for c in at.sidebar.caption)


def test_student_profile(monkeypatch):
    monkeypatch.chdir(ROOT)
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=90)
    at.run()
    at.switch_page("views/student_search.py").run()
    from edunexus.config import load_settings
    from edunexus.data import load_students
    zid = load_students(load_settings())[0]["ZID"].iloc[0]
    at.text_input[0].set_value(zid).run()
    assert not at.exception
    assert any(zid in m.value for m in at.markdown)
    assert any("peers" in m.value for m in at.markdown)


def test_dataset_switch_shows_banner(monkeypatch, tmp_path):
    """Demo banner shows on demo data and disappears on real data."""
    import shutil
    if not (ROOT / "data" / "TestStudents.xlsx").exists():
        pytest.skip("original data is local-only")
    from edunexus import config
    monkeypatch.chdir(ROOT)
    tmp_settings = tmp_path / "settings.yaml"
    shutil.copy(config.SETTINGS_PATH, tmp_settings)
    monkeypatch.setattr(config, "SETTINGS_PATH", tmp_settings)
    s = config.load_settings(tmp_settings)
    for demo, path in [(True, "data/TestStudents_demo.xlsx"), (False, "data/TestStudents.xlsx")]:
        s["data_source"]["excel"].update({"path": path, "demo": demo})
        config.save_settings(s, tmp_settings)
        at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=90)
        at.run()
        has = any("DEMO DATA" in m.value for m in at.markdown)
        assert has is demo


def test_login_gate(monkeypatch, tmp_path):
    """With [auth] secrets, the app shows only the login form until signed in; viewers have no Admin page."""
    monkeypatch.chdir(ROOT)
    sec = tmp_path / "secrets.toml"
    sec.write_text('[auth]\nviewer_password = "view1"\nadmin_password = "adm1"\n')
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=90)
    at.secrets["auth"] = {"viewer_password": "view1", "admin_password": "adm1"}
    at.run()
    assert not at.exception
    assert len(at.text_input) == 1 and not any("Executive Overview" in m.value for m in at.markdown)
    at.text_input[0].set_value("wrong"); at.button[0].click().run()
    assert any("Incorrect" in e.value for e in at.error)
    at.text_input[0].set_value("view1"); at.button[0].click().run()
    assert any("Executive Overview" in m.value for m in at.markdown)
    with pytest.raises(ValueError):          # Administration is not even in the menu for viewers
        at.switch_page("views/admin.py")

    adm = AppTest.from_file(str(ROOT / "app.py"), default_timeout=90)
    adm.secrets["auth"] = {"viewer_password": "view1", "admin_password": "adm1"}
    adm.run()
    adm.text_input[0].set_value("adm1"); adm.button[0].click().run()
    adm.switch_page("views/admin.py").run()
    assert not adm.exception
    assert any("Administration" in m.value for m in adm.markdown)
