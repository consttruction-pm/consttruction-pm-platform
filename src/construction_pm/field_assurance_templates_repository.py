from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Mapping, Protocol

from .backend_p0.models import BackendScope, MAX_SAFE_REVISION
from .backend_p0.transactions import SQLiteTransactionManager
from .field_assurance_execution import (
    FieldAssuranceExecution,
    FieldAssuranceExecutionAnswer,
    FieldAssuranceExecutionError,
)
from .field_assurance_templates import (
    FieldAssuranceTemplate,
    FieldAssuranceTemplateError,
    FieldAssuranceTemplateInputType,
    FieldAssuranceTemplateItem,
    FieldAssuranceTemplateType,
)


class FieldAssuranceTemplatePersistenceError(ValueError):
    pass


class FieldAssuranceTemplateRepository(Protocol):
    def create_template(self, template: FieldAssuranceTemplate) -> FieldAssuranceTemplate: ...
    def get_template(self, scope: BackendScope, template_id: str, template_version: int) -> FieldAssuranceTemplate | None: ...
    def create_execution(self, execution: FieldAssuranceExecution) -> FieldAssuranceExecution: ...
    def get_execution(self, scope: BackendScope, execution_id: str) -> FieldAssuranceExecution | None: ...


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
        execution.scope.validate()
        template = self.get_template(execution.scope, execution.template_id, execution.template_version)
        if template is None:
            existing = self.connection.execute(
                """SELECT 1 FROM field_assurance_templates
                   WHERE tenant_id=? AND project_id=? AND template_id=?
                   LIMIT 1""",
                (execution.scope.tenant_id, execution.scope.project_id, execution.template_id),
            ).fetchone()
            if existing is not None:
                raise FieldAssuranceTemplatePersistenceError("TEMPLATE_VERSION_MISMATCH")
            raise FieldAssuranceTemplatePersistenceError("TEMPLATE_NOT_FOUND")
        try:
            execution.validate_against(template)
        except FieldAssuranceExecutionError as exc:
            raise FieldAssuranceTemplatePersistenceError(str(exc)) from exc
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

    def execute(self, execution: FieldAssuranceExecution) -> FieldAssuranceExecution:
        return self.create_execution(execution)

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
    repository: FieldAssuranceTemplateRepository
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
        scope=BackendScope(str(scope_data["tenant_id"]), str(scope_data["project_id"]), int(scope_data["project_revision"])),
        template_id=str(payload["template_id"]),
        template_version=int(payload["template_version"]),
        answers=tuple(
            FieldAssuranceExecutionAnswer(item_id, value)
            for item_id, value in payload.get("answers", {}).items()
        ),
        executed_by=str(payload["executed_by"]),
        executed_at=datetime.fromisoformat(str(payload["executed_at"])),
    )


def _json_default(value: object) -> object:
    if isinstance(value, Decimal):
        return str(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")
