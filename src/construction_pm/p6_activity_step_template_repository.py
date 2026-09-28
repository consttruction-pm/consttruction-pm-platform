from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Protocol
from .backend_p0.models import BackendScope, MAX_SAFE_REVISION

class P6ActivityStepTemplatePersistenceError(ValueError):
    pass

@dataclass(frozen=True)
class P6ActivityStepTemplate:
    scope: BackendScope
    template_id: str
    name: str
    description: str | None = None
    udf_metadata: tuple[tuple[str, str], ...] = ()

    def validate(self) -> None:
        self.scope.validate()
        if not 0 <= self.scope.project_revision <= MAX_SAFE_REVISION:
            raise P6ActivityStepTemplatePersistenceError("INVALID_PROJECT_REVISION")
        for value, code in ((self.template_id, "TEMPLATE_ID"), (self.name, "NAME")):
            if not isinstance(value, str) or not value.strip():
                raise P6ActivityStepTemplatePersistenceError(f"INVALID_{code}")
        if self.description is not None and (not isinstance(self.description, str) or not self.description.strip()):
            raise P6ActivityStepTemplatePersistenceError("INVALID_DESCRIPTION")
        keys: set[str] = set()
        for key, value in self.udf_metadata:
            if not isinstance(key, str) or not key.strip() or key in keys or not isinstance(value, str):
                raise P6ActivityStepTemplatePersistenceError("INVALID_UDF_METADATA")
            keys.add(key)

class P6ActivityStepTemplateRepository(Protocol):
    def upsert(self, template: P6ActivityStepTemplate) -> P6ActivityStepTemplate: ...
    def get(self, scope: BackendScope, template_id: str) -> P6ActivityStepTemplate | None: ...
    def list(self, scope: BackendScope) -> tuple[P6ActivityStepTemplate, ...]: ...

def _payload(template: P6ActivityStepTemplate):
    return (template.name, template.description, tuple(template.udf_metadata))

def _from_row(scope, row):
    import json
    try:
        result = P6ActivityStepTemplate(scope, str(row[1]), str(row[2]), None if row[3] is None else str(row[3]), tuple((str(k), str(v)) for k, v in json.loads(row[4])))
        result.validate()
        return result
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise P6ActivityStepTemplatePersistenceError("INVALID_STORED_ACTIVITY_STEP_TEMPLATE") from exc

class SQLiteP6ActivityStepTemplateRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.connection.execute("PRAGMA busy_timeout = 5000")
        self.connection.execute("CREATE TABLE IF NOT EXISTS p6_activity_step_template (tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, project_revision INTEGER NOT NULL, template_id TEXT NOT NULL, name TEXT NOT NULL, description TEXT, udf_metadata_json TEXT NOT NULL, PRIMARY KEY (tenant_id, project_id, template_id))")
        self.connection.commit()

    def upsert(self, template):
        import json
        template.validate()
        row = self.connection.execute("SELECT project_revision,template_id,name,description,udf_metadata_json FROM p6_activity_step_template WHERE tenant_id=? AND project_id=? AND template_id=?", (template.scope.tenant_id, template.scope.project_id, template.template_id)).fetchone()
        encoded = json.dumps(list(template.udf_metadata), sort_keys=True, separators=(",", ":"))
        if row is not None:
            stored = (row[2], row[3], tuple(tuple(v) for v in json.loads(row[4])))
            if int(row[0]) != template.scope.project_revision:
                raise P6ActivityStepTemplatePersistenceError("REVISION_CONFLICT")
            if stored != _payload(template):
                raise P6ActivityStepTemplatePersistenceError("IMMUTABLE_ACTIVITY_STEP_TEMPLATE")
            return template
        self.connection.execute("INSERT INTO p6_activity_step_template (tenant_id,project_id,project_revision,template_id,name,description,udf_metadata_json) VALUES (?,?,?,?,?,?,?)", (template.scope.tenant_id, template.scope.project_id, template.scope.project_revision, template.template_id, template.name, template.description, encoded))
        return template

    def get(self, scope, template_id):
        scope.validate()
        if not isinstance(template_id, str) or not template_id.strip():
            raise P6ActivityStepTemplatePersistenceError("INVALID_TEMPLATE_ID")
        row = self.connection.execute("SELECT project_revision,template_id,name,description,udf_metadata_json FROM p6_activity_step_template WHERE tenant_id=? AND project_id=? AND template_id=?", (scope.tenant_id, scope.project_id, template_id)).fetchone()
        if row is None:
            return None
        if int(row[0]) != scope.project_revision:
            raise P6ActivityStepTemplatePersistenceError("REVISION_CONFLICT")
        return _from_row(scope, row)

    def list(self, scope):
        scope.validate()
        rows = self.connection.execute("SELECT project_revision,template_id,name,description,udf_metadata_json FROM p6_activity_step_template WHERE tenant_id=? AND project_id=? AND project_revision=? ORDER BY template_id", (scope.tenant_id, scope.project_id, scope.project_revision)).fetchall()
        return tuple(_from_row(scope, row) for row in rows)

class PostgresP6ActivityStepTemplateRepository:
    def __init__(self, connection: object) -> None:
        self.connection = connection

    def initialize(self) -> None:
        self.connection.execute("CREATE TABLE IF NOT EXISTS p6_activity_step_template (tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, project_revision BIGINT NOT NULL, template_id TEXT NOT NULL, name TEXT NOT NULL, description TEXT, udf_metadata_json TEXT NOT NULL, PRIMARY KEY (tenant_id, project_id, template_id))")

    def upsert(self, template):
        import json
        template.validate()
        row = self.connection.execute("SELECT project_revision,template_id,name,description,udf_metadata_json FROM p6_activity_step_template WHERE tenant_id=%s AND project_id=%s AND template_id=%s", (template.scope.tenant_id, template.scope.project_id, template.template_id)).fetchone()
        encoded = json.dumps(list(template.udf_metadata), sort_keys=True, separators=(",", ":"))
        if row is not None:
            stored = (row[2], row[3], tuple(tuple(v) for v in json.loads(row[4])))
            if int(row[0]) != template.scope.project_revision:
                raise P6ActivityStepTemplatePersistenceError("REVISION_CONFLICT")
            if stored != _payload(template):
                raise P6ActivityStepTemplatePersistenceError("IMMUTABLE_ACTIVITY_STEP_TEMPLATE")
            return template
        self.connection.execute("INSERT INTO p6_activity_step_template (tenant_id,project_id,project_revision,template_id,name,description,udf_metadata_json) VALUES (%s,%s,%s,%s,%s,%s,%s)", (template.scope.tenant_id, template.scope.project_id, template.scope.project_revision, template.template_id, template.name, template.description, encoded))
        return template

    def get(self, scope, template_id):
        scope.validate()
        row = self.connection.execute("SELECT project_revision,template_id,name,description,udf_metadata_json FROM p6_activity_step_template WHERE tenant_id=%s AND project_id=%s AND template_id=%s", (scope.tenant_id, scope.project_id, template_id)).fetchone()
        if row is None:
            return None
        if int(row[0]) != scope.project_revision:
            raise P6ActivityStepTemplatePersistenceError("REVISION_CONFLICT")
        return _from_row(scope, row)

    def list(self, scope):
        scope.validate()
        rows = self.connection.execute("SELECT project_revision,template_id,name,description,udf_metadata_json FROM p6_activity_step_template WHERE tenant_id=%s AND project_id=%s AND project_revision=%s ORDER BY template_id", (scope.tenant_id, scope.project_id, scope.project_revision)).fetchall()
        return tuple(_from_row(scope, row) for row in rows)

@dataclass(frozen=True)
class P6ActivityStepTemplateApplicationService:
    repository: P6ActivityStepTemplateRepository
    transaction_manager: object

    def save(self, template):
        template.validate()
        with self.transaction_manager.transaction():
            return self.repository.upsert(template)

    def read(self, scope, template_id):
        with self.transaction_manager.transaction():
            return self.repository.get(scope, template_id)

    def list(self, scope):
        with self.transaction_manager.transaction():
            return self.repository.list(scope)

__all__ = ["P6ActivityStepTemplate", "P6ActivityStepTemplateApplicationService", "P6ActivityStepTemplatePersistenceError", "P6ActivityStepTemplateRepository", "SQLiteP6ActivityStepTemplateRepository", "PostgresP6ActivityStepTemplateRepository"]
