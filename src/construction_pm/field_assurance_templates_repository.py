from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Mapping

from .backend_p0.models import BackendScope, MAX_SAFE_REVISION
from .backend_p0.transactions import SQLiteTransactionManager
from .field_assurance_templates import (
    FieldAssuranceTemplate,
    FieldAssuranceTemplateError,
    FieldAssuranceTemplateInputType,
    FieldAssuranceTemplateItem,
    FieldAssuranceTemplateType,
)


class FieldAssuranceTemplatePersistenceError(ValueError):
    pass


@dataclass(frozen=True)
class FieldAssuranceExecution:
    execution_id: str
    template_id: str
    template_version: int
    scope: BackendScope
    answers: tuple[tuple[str, object], ...]
    executed_by: str
    executed_at: datetime

    def validate(self, template: FieldAssuranceTemplate) -> None:
        if self.template_id != template.template_id or self.template_version != template.template_version:
            raise FieldAssuranceTemplatePersistenceError("TEMPLATE_VERSION_MISMATCH")
        if self.scope != template.scope:
            raise FieldAssuranceTemplatePersistenceError("TEMPLATE_SCOPE_MISMATCH")
        if not isinstance(self.execution_id, str) or not self.execution_id.strip():
            raise FieldAssuranceTemplatePersistenceError("INVALID_EXECUTION_ID")
        if not isinstance(self.executed_by, str) or not self.executed_by.strip():
            raise FieldAssuranceTemplatePersistenceError("INVALID_EXECUTED_BY")
        if self.executed_at.tzinfo is None or self.executed_at.utcoffset() is None:
            raise FieldAssuranceTemplatePersistenceError("EXECUTED_AT_MUST_BE_TIMEZONE_AWARE")

        expected = {item.item_id: item for item in template.items}
        seen: set[str] = set()
        for item_id, value in self.answers:
            if item_id in seen:
                raise FieldAssuranceTemplatePersistenceError("DUPLICATE_EXECUTION_ANSWER")
            seen.add(item_id)
            item = expected.get(item_id)
            if item is None:
                raise FieldAssuranceTemplatePersistenceError("UNKNOWN_EXECUTION_ITEM")
            if item.input_type is FieldAssuranceTemplateInputType.BOOLEAN and not isinstance(value, bool):
                raise FieldAssuranceTemplatePersistenceError("INVALID_BOOLEAN_ANSWER")
            if item.input_type is FieldAssuranceTemplateInputType.SELECT and (
                not isinstance(value, str) or value not in item.options
            ):
                raise FieldAssuranceTemplatePersistenceError("INVALID_SELECT_ANSWER")
            if item.input_type is FieldAssuranceTemplateInputType.TEXT and (
                not isinstance(value, str) or not value.strip()
            ):
                raise FieldAssuranceTemplatePersistenceError("INVALID_TEXT_ANSWER")
            if item.input_type is FieldAssuranceTemplateInputType.NUMBER:
                try:
                    Decimal(str(value))
                except Exception as exc:
                    raise FieldAssuranceTemplatePersistenceError("INVALID_NUMBER_ANSWER") from exc

        if any(item.required and item.item_id not in seen for item in template.items):
            raise FieldAssuranceTemplatePersistenceError("MISSING_REQUIRED_ANSWER")

    def as_dict(self) -> dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "template_id": self.template_id,
            "template_version": self.template_version,
            "scope": {
                "tenant_id": self.scope.tenant_id,
                "project_id": self.scope.project_id,
                "project_revision": self.scope.project_revision,
            },
            "answers": {item_id: value for item_id, value in self.answers},
            "executed_by": self.executed_by,
            "executed_at": self.executed_at.isoformat(),
        }


class SQLiteFieldAssuranceTemplateRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA busy_timeout = 5000")
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS field_assurance_templates (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                project_revision INTEGER NOT NULL,
                template_id TEXT NOT NULL,
                template_version INTEGER NOT NULL,
                contract_version TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                PRIMARY KEY (tenant_id, project_id, template_id, template_version)
            );
            CREATE TABLE IF NOT EXISTS field_assurance_executions (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                project_revision INTEGER NOT NULL,
                execution_id TEXT NOT NULL,
                template_id TEXT NOT NULL,
                template_version INTEGER NOT NULL,
                payload_json TEXT NOT NULL,
                PRIMARY KEY (tenant_id, project_id, execution_id),
                FOREIGN KEY (tenant_id, project_id, template_id, template_version)
                    REFERENCES field_assurance_templates (
                        tenant_id, project_id, template_id, template_version
                    )
            );
            CREATE INDEX IF NOT EXISTS idx_field_assurance_template_versions
                ON field_assurance_templates (tenant_id, project_id, template_id, template_version);
            """
        )
        self.connection.commit()

    def create_template(self, template: FieldAssuranceTemplate) -> FieldAssuranceTemplate:
        template.validate()
        payload = json.dumps(template.as_dict(), sort_keys=True, separators=(",", ":"))
        row = self.connection.execute(
            """SELECT payload_json FROM field_assurance_templates
               WHERE tenant_id=? AND project_id=? AND template_id=? AND template_version=?""",
            (template.scope.tenant_id, template.scope.project_id, template.template_id, template.template_version),
        ).fetchone()
        if row is not None:
            if row[0] != payload:
                raise FieldAssuranceTemplatePersistenceError("IMMUTABLE_TEMPLATE_VERSION")
            return template
        self.connection.execute(
            """INSERT INTO field_assurance_templates
               (tenant_id, project_id, project_revision, template_id, template_version, contract_version, payload_json)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                template.scope.tenant_id, template.scope.project_id, template.scope.project_revision,
                template.template_id, template.template_version, template.contract_version, payload,
            ),
        )
        return template

    def get_template(self, scope: BackendScope, template_id: str, template_version: int) -> FieldAssuranceTemplate | None:
        scope.validate()
        if not isinstance(template_id, str) or not template_id.strip():
            raise FieldAssuranceTemplatePersistenceError("INVALID_TEMPLATE_ID")
        if isinstance(template_version, bool) or not isinstance(template_version, int) or not 1 <= template_version <= MAX_SAFE_REVISION:
            raise FieldAssuranceTemplatePersistenceError("INVALID_TEMPLATE_VERSION")
        row = self.connection.execute(
            """SELECT payload_json FROM field_assurance_templates
               WHERE tenant_id=? AND project_id=? AND template_id=? AND template_version=?""",
            (scope.tenant_id, scope.project_id, template_id, template_version),
        ).fetchone()
        return None if row is None else _template_from_dict(json.loads(row[0]))

    def create_execution(self, execution: FieldAssuranceExecution) -> FieldAssuranceExecution:
        template = self.get_template(execution.scope, execution.template_id, execution.template_version)
        if template is None:
            raise FieldAssuranceTemplatePersistenceError("TEMPLATE_NOT_FOUND")
        execution.validate(template)
        payload = json.dumps(execution.as_dict(), sort_keys=True, separators=(",", ":"), default=_json_default)
        row = self.connection.execute(
            """SELECT payload_json FROM field_assurance_executions
               WHERE tenant_id=? AND project_id=? AND execution_id=?""",
            (execution.scope.tenant_id, execution.scope.project_id, execution.execution_id),
        ).fetchone()
        if row is not None:
            if row[0] != payload:
                raise FieldAssuranceTemplatePersistenceError("EXECUTION_ID_CONFLICT")
            return execution
        self.connection.execute(
            """INSERT INTO field_assurance_executions
               (tenant_id, project_id, project_revision, execution_id, template_id, template_version, payload_json)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                execution.scope.tenant_id, execution.scope.project_id, execution.scope.project_revision,
                execution.execution_id, execution.template_id, execution.template_version, payload,
            ),
        )
        return execution

    def get_execution(self, scope: BackendScope, execution_id: str) -> FieldAssuranceExecution | None:
        scope.validate()
        row = self.connection.execute(
            """SELECT payload_json FROM field_assurance_executions
               WHERE tenant_id=? AND project_id=? AND execution_id=?""",
            (scope.tenant_id, scope.project_id, execution_id),
        ).fetchone()
        return None if row is None else _execution_from_dict(json.loads(row[0]))


@dataclass(frozen=True)
class FieldAssuranceTemplateApplicationService:
    repository: SQLiteFieldAssuranceTemplateRepository
    transaction_manager: SQLiteTransactionManager

    def create_template(self, template: FieldAssuranceTemplate) -> FieldAssuranceTemplate:
        with self.transaction_manager.transaction():
            return self.repository.create_template(template)

    def execute(self, execution: FieldAssuranceExecution) -> FieldAssuranceExecution:
        with self.transaction_manager.transaction():
            return self.repository.create_execution(execution)

    def read_template(self, scope: BackendScope, template_id: str, template_version: int) -> FieldAssuranceTemplate | None:
        with self.transaction_manager.transaction():
            return self.repository.get_template(scope, template_id, template_version)


def _template_from_dict(payload: Mapping[str, Any]) -> FieldAssuranceTemplate:
    try:
        scope_data = payload["scope"]
        scope = BackendScope(str(scope_data["tenant_id"]), str(scope_data["project_id"]), int(scope_data["project_revision"]))
        items = tuple(
            FieldAssuranceTemplateItem(
                item_id=str(item["item_id"]),
                order=int(item["order"]),
                criterion_key=str(item["criterion_key"]),
                input_type=FieldAssuranceTemplateInputType(str(item["input_type"])),
                required=bool(item["required"]),
                options=tuple(str(option) for option in item.get("options", [])),
            )
            for item in payload["items"]
        )
        value = FieldAssuranceTemplate(
            template_id=str(payload["template_id"]),
            scope=scope,
            template_version=int(payload["template_version"]),
            template_type=FieldAssuranceTemplateType(str(payload["template_type"])),
            title_key=str(payload["title_key"]),
            items=items,
            contract_version=str(payload["contract_version"]),
        )
        value.validate()
        return value
    except (KeyError, TypeError, ValueError, FieldAssuranceTemplateError) as exc:
        raise FieldAssuranceTemplatePersistenceError("INVALID_STORED_TEMPLATE") from exc


def _execution_from_dict(payload: Mapping[str, Any]) -> FieldAssuranceExecution:
    scope_data = payload["scope"]
    return FieldAssuranceExecution(
        execution_id=str(payload["execution_id"]),
        template_id=str(payload["template_id"]),
        template_version=int(payload["template_version"]),
        scope=BackendScope(str(scope_data["tenant_id"]), str(scope_data["project_id"]), int(scope_data["project_revision"])),
        answers=tuple(payload.get("answers", {}).items()),
        executed_by=str(payload["executed_by"]),
        executed_at=datetime.fromisoformat(str(payload["executed_at"])),
    )


def _json_default(value: object) -> object:
    if isinstance(value, Decimal):
        return str(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")
