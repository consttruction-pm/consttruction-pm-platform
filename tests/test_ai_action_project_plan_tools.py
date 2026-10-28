from __future__ import annotations

import json
import sqlite3
from io import BytesIO
from pathlib import Path

import pytest

import construction_pm.preview.runtime as preview_runtime_module
from construction_pm.preview.runtime import open_preview_runtime
from construction_pm.preview.server import build_preview_application
from construction_pm.preview.storage import PREVIEW_TENANT_ID
from construction_pm.ai_action_project_plan_tools import _validated_plan


PLAN = {
    "project_id": "CUBI-TEST-001",
    "name": "Five-Story Office Building",
    "project_start": "2026-10-23",
    "calendar_system": "gregorian",
    # Python weekday numbers: Monday=0 ... Sunday=6. Friday (4) is off.
    "working_weekdays": [0, 1, 2, 3, 5, 6],
    "activities": [
        {
            "activity_id": "A001",
            "name": "Mobilization and site preparation",
            "wbs": "01 Mobilization",
            "duration_working_days": 2,
        },
        {
            "activity_id": "A002",
            "name": "Excavation",
            "wbs": "02 Substructure",
            "duration_working_days": 3,
        },
        {
            "activity_id": "A003",
            "name": "Foundation concrete",
            "wbs": "02 Substructure",
            "duration_working_days": 4,
        },
    ],
    "relationships": [
        {
            "relationship_id": "R001",
            "predecessor_id": "A001",
            "successor_id": "A002",
            "relationship_type": "FS",
            "lag_working_days": 0,
        },
        {
            "relationship_id": "R002",
            "predecessor_id": "A002",
            "successor_id": "A003",
            "relationship_type": "FS",
            "lag_working_days": 0,
        },
    ],
}


class FakePlanProvider:
    def __init__(self, payload: dict[str, object]):
        self.payload = payload
        self.calls: list[dict[str, object]] = []

    def complete_json(self, *, system_prompt, user_message, language, history=()):
        self.calls.append({
            "system_prompt": system_prompt,
            "user_message": user_message,
            "language": language,
            "history": history,
        })
        return {
            "kind": "action_proposal",
            "message": (
                "این یک برنامه اولیه با مدت‌های تخمینی است. پیش از تأیید، "
                "فعالیت‌ها، روابط و تقویم را بررسی کنید؛ برنامه مبنا ثبت نمی‌شود."
            ),
            "tool_name": "project.plan.create",
            "payload": self.payload,
        }


def _web_root(tmp_path: Path) -> Path:
    root = tmp_path / "web"
    source = root / "dist" / "web" / "src"
    source.mkdir(parents=True)
    (source / "landing-entry.js").write_text("export {};\n", encoding="utf-8")
    (root / "app.html").write_text(
        '<!doctype html><html><body><div id="app"></div></body></html>',
        encoding="utf-8",
    )
    (root / "styles.css").write_text("body { margin: 0; }\n", encoding="utf-8")
    return root


def _request(app, method: str, path: str, *, body: bytes = b"", cookie: str | None = None):
    environ: dict[str, object] = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "CONTENT_LENGTH": str(len(body)),
        "wsgi.input": BytesIO(body),
        "wsgi.url_scheme": "http",
    }
    if body:
        environ["CONTENT_TYPE"] = "application/json"
    if cookie:
        environ["HTTP_COOKIE"] = f"cp_session={cookie}"
    captured: dict[str, object] = {}

    def start_response(status, headers):
        captured["status"] = status
        captured["headers"] = headers

    response = b"".join(app(environ, start_response))
    status = int(str(captured["status"]).split(" ", 1)[0])
    headers = {str(k).lower(): str(v) for k, v in captured.get("headers", [])}
    return status, headers, response


def _cookie(headers: dict[str, str]) -> str:
    return headers["set-cookie"].split(";", 1)[0].split("=", 1)[1]


def test_project_plan_payload_rejects_dependency_cycles_and_unknown_activities():
    cyclic = json.loads(json.dumps(PLAN))
    cyclic["relationships"].append({
        "relationship_id": "R003",
        "predecessor_id": "A003",
        "successor_id": "A001",
        "relationship_type": "FS",
        "lag_working_days": 0,
    })
    with pytest.raises(ValueError, match="PROJECT_PLAN_RELATIONSHIPS_CONTAIN_CYCLE"):
        _validated_plan(cyclic)

    unknown = json.loads(json.dumps(PLAN))
    unknown["relationships"][0]["successor_id"] = "A404"
    with pytest.raises(ValueError, match="PROJECT_PLAN_RELATIONSHIP_ENDPOINT_UNKNOWN"):
        _validated_plan(unknown)


def test_real_preview_assistant_proposes_then_approves_creates_and_calculates_project(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    provider = FakePlanProvider(json.loads(json.dumps(PLAN)))

    class ProviderFactory:
        @staticmethod
        def from_environment():
            return provider

    monkeypatch.setenv("CUBI_AI_ENABLED", "true")
    # This test injects a fake local provider factory; model presence is still explicit.
    monkeypatch.setenv("CUBI_AI_LOCAL_MODEL", "test-local-model")
    monkeypatch.delenv("CUBI_PREVIEW_PUBLIC_DEMO", raising=False)
    monkeypatch.delenv("CUBI_PREVIEW_PRIVATE_ACCESS_TOKEN", raising=False)
    monkeypatch.setattr(
        preview_runtime_module,
        "build_ai_chat_provider_from_environment",
        ProviderFactory.from_environment,
    )

    runtime = open_preview_runtime(
        tmp_path / "preview.sqlite3",
        web_root=_web_root(tmp_path),
        reset=True,
    )
    try:
        app = build_preview_application(runtime)
        status, headers, _ = _request(
            app,
            "POST",
            "/preview/login",
            body=b"role=admin",
        )
        assert status == 303
        cookie = _cookie(headers)

        # Asking for a plan proposes it; no project is persisted before approval.
        status, _, body = _request(
            app,
            "POST",
            "/api/projects/preview-rps-01/ai/assistant/turn",
            cookie=cookie,
            body=json.dumps({
                "expected_revision": 7,
                "message": (
                    "برای پروژه CUBI-TEST-001 یک برنامه اولیه بساز. مدت‌ها تخمینی باشند، "
                    "تقویم شنبه تا پنجشنبه باشد و پیش از ذخیره از من تأیید بگیر."
                ),
                "language": "fa",
            }, ensure_ascii=False).encode("utf-8"),
        )
        assert status == 200, body.decode("utf-8")
        response = json.loads(body)
        assert response["kind"] == "action_proposal"
        proposal_id = response["proposal"]["proposal_id"]
        assert runtime.store.get_for_user(
            PREVIEW_TENANT_ID, "CUBI-TEST-001", "preview-admin"
        ) is None

        status, _, body = _request(
            app,
            "POST",
            f"/api/projects/preview-rps-01/ai/actions/proposals/{proposal_id}/decision",
            cookie=cookie,
            body=json.dumps({"expected_revision": 7, "approved": True}).encode("utf-8"),
        )
        assert status == 200, body.decode("utf-8")
        assert json.loads(body)["status"] == "approved"

        status, _, body = _request(
            app,
            "POST",
            f"/api/projects/preview-rps-01/ai/actions/proposals/{proposal_id}/execute",
            cookie=cookie,
            body=json.dumps({"expected_revision": 7}).encode("utf-8"),
        )
        assert status == 200, body.decode("utf-8")
        executed = json.loads(body)
        result = executed["result"]
        assert executed["status"] == "executed"
        assert result["project_id"] == "CUBI-TEST-001"
        assert result["activity_count"] == 3
        assert result["relationship_count"] == 2
        assert result["wbs_group_count"] == 2
        assert result["calculated_activity_count"] == 3
        assert result["schedule_calculation_verified"] is True
        assert result["persisted_readback_verified"] is True
        assert result["baseline_approved"] is False

        project = runtime.store.get_for_user(
            PREVIEW_TENANT_ID, "CUBI-TEST-001", "preview-admin"
        )
        assert project is not None
        assert runtime.store.counts(PREVIEW_TENANT_ID, "CUBI-TEST-001") == 3
        assert runtime.store.wbs_for(PREVIEW_TENANT_ID, "CUBI-TEST-001") == {
            "A001": "01 Mobilization",
            "A002": "02 Substructure",
            "A003": "02 Substructure",
        }
        relation_count = runtime.connection.execute(
            "SELECT COUNT(*) FROM relationship_master WHERE tenant_id=? AND project_id=?",
            (PREVIEW_TENANT_ID, "CUBI-TEST-001"),
        ).fetchone()[0]
        assert relation_count == 2
        assert runtime.connection.execute(
            "SELECT COUNT(*) FROM project_schedule_settings WHERE tenant_id=? AND project_id=?",
            (PREVIEW_TENANT_ID, "CUBI-TEST-001"),
        ).fetchone()[0] == 1
        assert provider.calls and "project.plan.create" in provider.calls[0]["system_prompt"]
    finally:
        runtime.close()


def test_public_demo_stays_viewer_only_while_private_owner_gate_can_create_admin_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.delenv("CUBI_AI_ENABLED", raising=False)
    monkeypatch.setenv("CUBI_PREVIEW_PUBLIC_DEMO", "true")
    monkeypatch.setenv("CUBI_PREVIEW_PRIVATE_ACCESS_TOKEN", "test-private-token")

    runtime = open_preview_runtime(
        tmp_path / "preview.sqlite3",
        web_root=_web_root(tmp_path),
        reset=True,
    )
    try:
        app = build_preview_application(runtime)
        status, _, _ = _request(
            app, "POST", "/preview/login", body=b"role=admin"
        )
        assert status == 403

        status, _, body = _request(
            app,
            "POST",
            "/preview/private-login",
            body=b"access_token=wrong",
        )
        assert status == 403

        status, headers, _ = _request(
            app,
            "POST",
            "/preview/private-login",
            body=b"access_token=test-private-token",
        )
        assert status == 303
        cookie = _cookie(headers)
        status, _, body = _request(app, "GET", "/api/session", cookie=cookie)
        assert status == 200
        assert json.loads(body)["roles"] == ["project_admin"]
    finally:
        runtime.close()


def test_preview_assistant_creates_and_persists_boq_only_after_approval(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    from construction_pm.backend_p0.models import BackendScope
    from construction_pm.quantity_takeoff import SQLiteQuantityTakeoffRepository

    class FakeTakeoffProvider:
        def complete_json(self, *, system_prompt, user_message, language, history=()):
            return {
                "kind": "action_proposal",
                "message": "این برآورد پیشنهادی است؛ پیش از ثبت نهایی، متره، پرت، نرخ و منبع آن را بررسی و تأیید کنید.",
                "tool_name": "quantity.takeoff.create",
                "payload": {
                    "estimate_id": "BOQ-PREVIEW-01",
                    "name": "برآورد بتن فونداسیون",
                    "lines": [{
                        "line_id": "CONC-01",
                        "description": "بتن کلاهک شمع",
                        "unit": "m3",
                        "base_quantity": 100,
                        "waste_percent": 20,
                        "measurement_status": "measured",
                        "measurement_basis": "طول × عرض × ضخامت از نقشه تأییدشده",
                        "source_ref": "drawing:S-101/pile-cap-PC01",
                        "classification_code": "03.30.00",
                        "unit_rate": 50.25,
                        "currency": "EUR",
                        "currency_minor_units": 2,
                        "rate_basis": "approved-quotation:Q-2026-104",
                    }],
                },
            }

    provider = FakeTakeoffProvider()

    class ProviderFactory:
        @staticmethod
        def from_environment():
            return provider

    monkeypatch.setenv("CUBI_AI_ENABLED", "true")
    monkeypatch.setenv("CUBI_AI_LOCAL_MODEL", "test-local-model")
    monkeypatch.delenv("CUBI_PREVIEW_PUBLIC_DEMO", raising=False)
    monkeypatch.delenv("CUBI_PREVIEW_PRIVATE_ACCESS_TOKEN", raising=False)
    monkeypatch.setattr(
        preview_runtime_module,
        "build_ai_chat_provider_from_environment",
        ProviderFactory.from_environment,
    )

    runtime = open_preview_runtime(
        tmp_path / "preview-boq.sqlite3",
        web_root=_web_root(tmp_path),
        reset=True,
    )
    try:
        app = build_preview_application(runtime)
        status, headers, _ = _request(app, "POST", "/preview/login", body=b"role=admin")
        assert status == 303
        cookie = _cookie(headers)

        status, _, body = _request(
            app,
            "POST",
            "/api/projects/preview-rps-01/ai/assistant/turn",
            cookie=cookie,
            body=json.dumps({
                "expected_revision": 7,
                "message": "یک برآورد متره برای بتن فونداسیون بساز، مقادیر را با منبع نشان بده و قبل از ثبت از من تأیید بگیر.",
                "language": "fa",
            }, ensure_ascii=False).encode("utf-8"),
        )
        assert status == 200, body.decode("utf-8")
        turn = json.loads(body)
        assert turn["kind"] == "action_proposal"
        proposal_id = turn["proposal"]["proposal_id"]

        repository = SQLiteQuantityTakeoffRepository(runtime.connection)
        persisted_scope = BackendScope(PREVIEW_TENANT_ID, "preview-rps-01", 7)
        assert repository.get(persisted_scope, "BOQ-PREVIEW-01") is None
        assert "quantity.takeoff.create" in runtime.ai_tool_names

        status, _, body = _request(
            app,
            "POST",
            f"/api/projects/preview-rps-01/ai/actions/proposals/{proposal_id}/decision",
            cookie=cookie,
            body=json.dumps({"expected_revision": 7, "approved": True}).encode("utf-8"),
        )
        assert status == 200, body.decode("utf-8")
        assert json.loads(body)["status"] == "approved"

        status, _, body = _request(
            app,
            "POST",
            f"/api/projects/preview-rps-01/ai/actions/proposals/{proposal_id}/execute",
            cookie=cookie,
            body=json.dumps({"expected_revision": 7}).encode("utf-8"),
        )
        assert status == 200, body.decode("utf-8")
        executed = json.loads(body)
        assert executed["status"] == "executed"
        result = executed["result"]
        assert result["summary"]["line_count"] == 1
        assert result["summary"]["cost_complete"] is True
        assert result["lines"][0]["billable_quantity"] == "120.0"
        assert result["lines"][0]["extended_cost"] == "6030.00"
        assert result["summary"]["totals_by_currency"] == [
            {"currency": "EUR", "minor_units": 2, "subtotal": "6030.00"}
        ]

        saved = repository.get(persisted_scope, "BOQ-PREVIEW-01")
        assert saved is not None
        assert saved.to_payload() == result
        assert runtime.connection.execute(
            "SELECT COUNT(*) FROM quantity_takeoff_estimates"
        ).fetchone()[0] == 1
    finally:
        runtime.close()
