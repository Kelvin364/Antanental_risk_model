"""Hosting safeguards for the Render deployment (R14): the database kind in /health, the refusal
to start on a SQLite file where a restart wipes files, the read only database check and the
backup copy that make restore-local loads."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from tests.integration.accounts import sign_in_as
from tests.integration.test_api import CASE, VISIT_ONE, VISIT_TWO
from webapp.app.core.settings import Settings
from webapp.app.db.database import EphemeralDatabase, backend
from webapp.app.db.maintenance import check, copy_to_sqlite
from webapp.app.main import create_app


@pytest.fixture
def settings(root, tmp_path) -> Settings:
    return Settings(
        model_dir=root / "webapp" / "model",
        database_url=f"sqlite:///{tmp_path / 'app.sqlite3'}",
        static_dir=root / "frontend" / "out",
    )


def _one_assessed_case(settings: Settings) -> float:
    client = sign_in_as(TestClient(create_app(settings)), "keeper")
    number = client.post("/api/cases", json=CASE).json()["id"]
    client.put(f"/api/cases/{number}/visits/1", json=VISIT_ONE)
    client.put(f"/api/cases/{number}/visits/2", json=VISIT_TWO)
    return client.post(f"/api/cases/{number}/assessment").json()["probability"]


@pytest.mark.parametrize(
    ("address", "kind"),
    [
        ("sqlite:////app/state/app.sqlite3", "sqlite"),
        ("postgresql://u:p@host/db?sslmode=require", "postgresql"),
        ("postgres://u:p@host/db", "postgresql"),
    ],
)
def test_backend_names_the_kind_only(address, kind):
    assert backend(address) == kind


def test_health_reports_the_database_kind_without_its_address(settings):
    body = TestClient(create_app(settings)).get("/health").json()
    assert body["database"] == "sqlite"
    assert settings.database_url not in json.dumps(body)


def test_server_refuses_a_sqlite_file_when_a_persistent_database_is_required(settings):
    from dataclasses import replace

    with pytest.raises(EphemeralDatabase, match="ANTENATAL_DATABASE_URL"):
        create_app(replace(settings, require_persistent_database=True))


def test_requirement_is_read_from_the_environment(monkeypatch):
    monkeypatch.setenv("ANTENATAL_REQUIRE_PERSISTENT_DATABASE", "true")
    assert Settings.from_env().require_persistent_database
    monkeypatch.setenv("ANTENATAL_REQUIRE_PERSISTENT_DATABASE", "")
    assert not Settings.from_env().require_persistent_database


def test_check_counts_rows_and_reads_only(settings):
    _one_assessed_case(settings)
    report = check(settings.database_url)
    assert report["database"] == "sqlite" and report["missing_tables"] == []
    assert report["rows"]["synthetic_cases"] == 1 and report["rows"]["assessments"] == 1
    assert check(settings.database_url)["rows"] == report["rows"]


def test_backup_copies_every_table_and_serves_the_same_case(settings, tmp_path):
    from dataclasses import replace

    probability = _one_assessed_case(settings)
    target = tmp_path / "backups" / "online.sqlite3"
    counts = copy_to_sqlite(settings.database_url, target)
    assert counts == check(settings.database_url)["rows"]
    assert not target.with_suffix(".partial").exists()
    restored = replace(settings, database_url=f"sqlite:///{target}")
    client = TestClient(create_app(restored))
    signed = client.post(
        "/api/auth/sign-in",
        json={"username": "keeper", "password": "a long synthetic test password"},
    )
    assert signed.status_code == 200
    client.headers["X-CSRF-Token"] = signed.json()["csrf_token"]
    case = client.get("/api/caseload").json()["rows"][0]
    stored = client.get(f"/api/cases/{case['case_id']}").json()["latest_assessment"]
    assert stored["probability"] == probability


def test_admin_commands_check_and_back_up(settings, tmp_path, monkeypatch, capsys):
    from webapp.app.admin import main

    _one_assessed_case(settings)
    monkeypatch.setenv("ANTENATAL_DATABASE_URL", settings.database_url)
    assert main(["check-database"]) == 0
    assert json.loads(capsys.readouterr().out)["rows"]["users"] == 1
    target = tmp_path / "copy.sqlite3"
    assert main(["backup", str(target)]) == 0
    assert "synthetic_cases: 1 rows" in capsys.readouterr().out and target.exists()
