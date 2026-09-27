from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping


class ProjectPortabilityError(ValueError):
    """Raised when a project portability snapshot is incomplete or invalid."""


@dataclass(frozen=True)
class ProjectPortabilitySnapshot:
    SUPPORTED_SCHEMA_VERSION = "project-portability.v1"

    schema_version: str
    tenant_id: str
    project_id: str
    project_revision: int
    calendar_context: Mapping[str, Any]
    scheduling_settings: Mapping[str, Any]
    calculation_settings: Mapping[str, Any]
    resource_cost_config: Mapping[str, Any]
    module_refs: Mapping[str, Any]

    def validate(self) -> None:
        if self.schema_version != self.SUPPORTED_SCHEMA_VERSION:
            raise ProjectPortabilityError("UNSUPPORTED_SCHEMA_VERSION")
        for name, value in (("tenant_id", self.tenant_id), ("project_id", self.project_id)):
            if not isinstance(value, str) or not value.strip():
                raise ProjectPortabilityError(f"INVALID_{name.upper()}")
        if isinstance(self.project_revision, bool) or not isinstance(self.project_revision, int) or self.project_revision < 0:
            raise ProjectPortabilityError("INVALID_PROJECT_REVISION")
        for name, value in (
            ("calendar_context", self.calendar_context),
            ("scheduling_settings", self.scheduling_settings),
            ("calculation_settings", self.calculation_settings),
            ("resource_cost_config", self.resource_cost_config),
            ("module_refs", self.module_refs),
        ):
            if not isinstance(value, Mapping):
                raise ProjectPortabilityError(f"INVALID_{name.upper()}")

    def to_payload(self) -> dict[str, Any]:
        self.validate()
        return {
            "schema_version": self.schema_version,
            "tenant_id": self.tenant_id,
            "project_id": self.project_id,
            "project_revision": self.project_revision,
            "calendar_context": _plain(self.calendar_context),
            "scheduling_settings": _plain(self.scheduling_settings),
            "calculation_settings": _plain(self.calculation_settings),
            "resource_cost_config": _plain(self.resource_cost_config),
            "module_refs": _plain(self.module_refs),
        }


def export_project(snapshot: ProjectPortabilitySnapshot) -> bytes:
    """Serialize portability context deterministically; no domain calculations occur here."""
    return json.dumps(
        snapshot.to_payload(),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def import_project(data: bytes | str) -> ProjectPortabilitySnapshot:
    try:
        payload = json.loads(
            data.decode("utf-8") if isinstance(data, bytes) else data,
            parse_constant=_reject_non_standard_json_number,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ProjectPortabilityError("INVALID_PROJECT_EXPORT") from exc
    if not isinstance(payload, dict):
        raise ProjectPortabilityError("INVALID_PROJECT_EXPORT")
    required = (
        "schema_version", "tenant_id", "project_id", "project_revision",
        "calendar_context", "scheduling_settings", "calculation_settings",
        "resource_cost_config", "module_refs",
    )
    missing = set(required).difference(payload)
    if missing:
        raise ProjectPortabilityError("MISSING_PORTABILITY_CONTEXT")
    unexpected = set(payload).difference(required)
    if unexpected:
        raise ProjectPortabilityError("UNEXPECTED_PORTABILITY_CONTEXT")
    snapshot = ProjectPortabilitySnapshot(
        schema_version=payload["schema_version"],
        tenant_id=payload["tenant_id"],
        project_id=payload["project_id"],
        project_revision=payload["project_revision"],
        calendar_context=payload["calendar_context"],
        scheduling_settings=payload["scheduling_settings"],
        calculation_settings=payload["calculation_settings"],
        resource_cost_config=payload["resource_cost_config"],
        module_refs=payload["module_refs"],
    )
    snapshot.validate()
    return snapshot


def portability_fingerprint(snapshot: ProjectPortabilitySnapshot) -> str:
    return hashlib.sha256(export_project(snapshot)).hexdigest()


def _plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


def _reject_non_standard_json_number(value: str) -> None:
    raise ValueError(f"non-standard JSON number: {value}")
