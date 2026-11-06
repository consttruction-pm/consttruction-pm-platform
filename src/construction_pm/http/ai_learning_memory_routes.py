from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from urllib.parse import unquote, urlsplit

from ..ai_learning_memory import (
    AILearningMemoryRecord,
    LearningScope,
    LearningSignalKind,
    LearningStatus,
)
from ..ai_learning_memory_application import (
    AILearningMemoryApplicationError,
    AILearningMemoryApplicationService,
)
from ..application.project_lifecycle import ProjectLifecycleError, SessionError
from ..application.project_lifecycle_api import ProjectLifecycleAPI


class AILearningMemoryHttpRoutes:
    """Session-bound HTTP routes for append-only, privacy-scoped learning records."""

    BASE_SUFFIX = "/ai/learning-memory"
    _USER_SIGNAL_KINDS = {
        LearningSignalKind.USER_CORRECTION,
        LearningSignalKind.USER_FEEDBACK,
        LearningSignalKind.OBSERVED_OUTCOME,
        LearningSignalKind.ASSISTANT_MISUNDERSTANDING,
    }
    _INPUT_FIELDS = {
        "record_id",
        "record_version",
        "scope",
        "status",
        "signal_kind",
        "lesson",
        "conditions",
        "limitations",
        "evidence_refs",
        "supersedes_record_id",
        "consent_for_generalization",
    }

    def __init__(
        self,
        lifecycle_api: ProjectLifecycleAPI,
        service: AILearningMemoryApplicationService,
    ) -> None:
        self._lifecycle_api = lifecycle_api
        self._service = service

    def handle(
        self,
        method: str,
        path: str,
        *,
        session_id: str,
        now: datetime,
        body: bytes = b"",
    ) -> tuple[int, dict[str, str], bytes] | None:
        clean_path = urlsplit(path).path
        marker = self.BASE_SUFFIX
        if marker not in clean_path:
            return None
        prefix, suffix = clean_path.split(marker, 1)
        if not prefix.startswith("/api/projects/"):
            return None
        project_id = prefix[len("/api/projects/"):]
        if not project_id or "/" in project_id or (suffix and not suffix.startswith("/")):
            return self._error(400, "AI_LEARNING_ROUTE_INVALID")

        try:
            project = self._lifecycle_api.open_project(session_id, project_id, now=now)
            session = self._lifecycle_api.get_session(session_id, now=now)
            auth = project.context.authorization_context(session.roles)
            if suffix in ("", "/") and method == "GET":
                records = self._service.list_retrievable(auth)
                return self._json(200, {
                    "contract_version": "cubi-ai-learning-memory.v1",
                    "records": [self._record_dto(item) for item in records],
                })
            if suffix in ("", "/") and method == "POST":
                record = self._parse_record(body, auth, now)
                stored = self._service.append(record, auth)
                return self._json(201, {
                    "contract_version": "cubi-ai-learning-memory.v1",
                    "record": self._record_dto(stored),
                })
            if method == "GET":
                parts = [unquote(part) for part in suffix.strip("/").split("/") if part]
                if len(parts) == 2:
                    record_version = int(parts[1])
                    record = self._service.get(parts[0], record_version, auth)
                    if record is None:
                        return self._error(404, "AI_LEARNING_RECORD_NOT_FOUND")
                    return self._json(200, {
                        "contract_version": "cubi-ai-learning-memory.v1",
                        "record": self._record_dto(record),
                    })
            return self._error(405, "AI_LEARNING_METHOD_NOT_ALLOWED")
        except SessionError as exc:
            return self._error(401, str(exc) or "SESSION_REQUIRED")
        except ProjectLifecycleError as exc:
            return self._error(403, str(exc) or "PROJECT_NOT_AUTHORIZED")
        except AILearningMemoryApplicationError as exc:
            code = str(exc)
            if code in {
                "AI_LEARNING_AUDIT_PERSISTENCE_FAILED",
                "AI_LEARNING_PERSISTENCE_FAILED",
            }:
                return self._error(503, code)
            if "PERMISSION" in code or code.endswith("NOT_AUTHORIZED"):
                return self._error(403, code)
            if code == "INVALID_AI_LEARNING_RECORD":
                return self._error(400, code)
            return self._error(400, code)
        except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError):
            return self._error(400, "AI_LEARNING_REQUEST_INVALID")

    def _parse_record(self, body: bytes, auth: Any, now: datetime) -> AILearningMemoryRecord:
        try:
            payload = json.loads(body.decode("utf-8") or "{}")
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("AI_LEARNING_REQUEST_INVALID") from exc
        if not isinstance(payload, dict) or set(payload) - self._INPUT_FIELDS:
            raise ValueError("AI_LEARNING_REQUEST_INVALID")

        try:
            scope = LearningScope(payload.get("scope"))
            status = LearningStatus(payload.get("status", LearningStatus.CANDIDATE.value))
            signal_kind = LearningSignalKind(payload.get("signal_kind"))
        except (TypeError, ValueError) as exc:
            raise ValueError("AI_LEARNING_REQUEST_INVALID") from exc
        if status not in {LearningStatus.CAPTURED, LearningStatus.CANDIDATE}:
            raise ValueError("AI_LEARNING_STATUS_REQUIRES_REVIEW_WORKFLOW")
        if signal_kind not in self._USER_SIGNAL_KINDS:
            raise ValueError("AI_LEARNING_SIGNAL_KIND_NOT_CLIENT_WRITABLE")

        evidence_refs = payload.get("evidence_refs")
        if not isinstance(evidence_refs, list) or not evidence_refs or any(
            not isinstance(item, str) or not item.strip() for item in evidence_refs
        ):
            raise ValueError("AI_LEARNING_EVIDENCE_REQUIRED")

        lesson = payload.get("lesson")
        conditions = payload.get("conditions")
        limitations = payload.get("limitations")
        if any(not isinstance(value, str) or not value.strip() for value in (
            lesson, conditions, limitations
        )):
            raise ValueError("AI_LEARNING_CONTENT_REQUIRED")

        record_id = payload.get("record_id")
        record_version = payload.get("record_version")
        if not isinstance(record_id, str) or not record_id.strip():
            raise ValueError("AI_LEARNING_RECORD_ID_REQUIRED")
        if (
            isinstance(record_version, bool)
            or not isinstance(record_version, int)
            or record_version < 1
        ):
            raise ValueError("AI_LEARNING_RECORD_VERSION_INVALID")

        consent = payload.get("consent_for_generalization", False)
        if not isinstance(consent, bool):
            raise ValueError("AI_LEARNING_CONSENT_INVALID")
        if scope is LearningScope.GENERAL_CANDIDATE and not consent:
            raise ValueError("AI_LEARNING_GENERALIZATION_CONSENT_REQUIRED")
        if scope is LearningScope.GENERAL_PUBLISHED:
            raise ValueError("AI_LEARNING_GENERAL_PUBLISH_REQUIRES_REVIEW_WORKFLOW")

        if scope is LearningScope.USER_PRIVATE:
            owner_user_id, tenant_id, scoped_project_id = auth.user_id, None, None
        elif scope is LearningScope.PROJECT_PRIVATE:
            owner_user_id, tenant_id, scoped_project_id = (
                auth.user_id, auth.tenant_id, auth.project_id
            )
        elif scope is LearningScope.TENANT_SHARED:
            owner_user_id, tenant_id, scoped_project_id = None, auth.tenant_id, None
        elif scope is LearningScope.GENERAL_CANDIDATE:
            owner_user_id, tenant_id, scoped_project_id = None, None, None
        else:
            raise ValueError("AI_LEARNING_SCOPE_NOT_CLIENT_WRITABLE")

        supersedes = payload.get("supersedes_record_id")
        if supersedes is not None and (
            not isinstance(supersedes, str) or not supersedes.strip()
        ):
            raise ValueError("AI_LEARNING_SUPERSEDES_REFERENCE_INVALID")

        return AILearningMemoryRecord(
            record_id=record_id,
            record_version=record_version,
            scope=scope,
            status=status,
            signal_kind=signal_kind,
            lesson=lesson.strip(),
            conditions=conditions.strip(),
            limitations=limitations.strip(),
            evidence_refs=tuple(evidence_refs),
            captured_at=now,
            updated_at=now,
            owner_user_id=owner_user_id,
            tenant_id=tenant_id,
            project_id=scoped_project_id,
            consent_for_generalization=consent,
            supersedes_record_id=supersedes,
        )

    @staticmethod
    def _record_dto(record: AILearningMemoryRecord) -> dict[str, object]:
        return {
            "record_id": record.record_id,
            "record_version": record.record_version,
            "schema_version": record.schema_version,
            "scope": record.scope.value,
            "status": record.status.value,
            "signal_kind": record.signal_kind.value,
            "lesson": record.lesson,
            "conditions": record.conditions,
            "limitations": record.limitations,
            "evidence_refs": list(record.evidence_refs),
            "captured_at": record.captured_at.isoformat(),
            "updated_at": record.updated_at.isoformat(),
            "consent_for_generalization": record.consent_for_generalization,
            "supersedes_record_id": record.supersedes_record_id,
        }

    @staticmethod
    def _json(status: int, payload: dict[str, object]) -> tuple[int, dict[str, str], bytes]:
        return (
            status,
            {"Content-Type": "application/json; charset=utf-8"},
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
        )

    @classmethod
    def _error(cls, status: int, code: str) -> tuple[int, dict[str, str], bytes]:
        return cls._json(status, {"code": code})


__all__ = ["AILearningMemoryHttpRoutes"]
