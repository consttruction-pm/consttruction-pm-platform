"""PostgreSQL EPS hierarchy and project responsibility assignments.

P6 V26 assigns an OBS responsible manager to EPS nodes. Projects inherit the
nearest responsible OBS along their EPS branch unless the project has its own
responsible OBS. This repository keeps EPS and OBS as separate hierarchies.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Any


class P6EPSError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class P6EPSNode:
    tenant_id: str
    eps_id: str
    name: str
    parent_eps_id: str | None = None
    responsible_obs_id: str = ""
    sequence_number: int = 0

    def validate(self) -> None:
        for value, code, limit in (
            (self.tenant_id, "P6_EPS_TENANT_INVALID", 120),
            (self.eps_id, "P6_EPS_ID_INVALID", 120),
            (self.name, "P6_EPS_NAME_INVALID", 200),
        ):
            if not isinstance(value, str) or not value.strip() or len(value) > limit:
                raise P6EPSError(code)
        if self.parent_eps_id is not None and (
            not isinstance(self.parent_eps_id, str)
            or not self.parent_eps_id.strip()
            or self.parent_eps_id == self.eps_id
        ):
            raise P6EPSError("P6_EPS_PARENT_INVALID")
        if not isinstance(self.responsible_obs_id, str) or len(self.responsible_obs_id) > 120:
            raise P6EPSError("P6_EPS_RESPONSIBLE_OBS_INVALID")
        if isinstance(self.sequence_number, bool) or not isinstance(self.sequence_number, int) or self.sequence_number < 0:
            raise P6EPSError("P6_EPS_SEQUENCE_INVALID")


class PostgresP6EPSRepository:
    def __init__(self, connection: Any) -> None:
        self.connection = connection

    def initialize(self) -> None:
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS p6_eps_node (
                tenant_id TEXT NOT NULL,
                eps_id TEXT NOT NULL,
                parent_eps_id TEXT,
                name TEXT NOT NULL,
                responsible_obs_id TEXT NOT NULL DEFAULT '',
                sequence_number INTEGER NOT NULL DEFAULT 0 CHECK (sequence_number >= 0),
                revision BIGINT NOT NULL DEFAULT 1 CHECK (revision >= 1),
                PRIMARY KEY (tenant_id, eps_id),
                FOREIGN KEY (tenant_id, parent_eps_id)
                    REFERENCES p6_eps_node(tenant_id, eps_id) ON DELETE RESTRICT
            )"""
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS p6_eps_parent_order "
            "ON p6_eps_node(tenant_id,parent_eps_id,sequence_number,eps_id)"
        )
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS p6_project_eps_assignment (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                eps_id TEXT NOT NULL,
                revision BIGINT NOT NULL DEFAULT 1 CHECK (revision >= 1),
                updated_by TEXT NOT NULL,
                updated_at TIMESTAMPTZ NOT NULL,
                PRIMARY KEY (tenant_id, project_id),
                FOREIGN KEY (tenant_id, project_id)
                    REFERENCES project_lifecycle_projects(tenant_id, project_id) ON DELETE CASCADE,
                FOREIGN KEY (tenant_id, eps_id)
                    REFERENCES p6_eps_node(tenant_id, eps_id) ON DELETE RESTRICT
            )"""
        )
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS p6_wbs_obs_responsibility (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                wbs_id TEXT NOT NULL,
                responsible_obs_id TEXT NOT NULL,
                revision BIGINT NOT NULL DEFAULT 1 CHECK (revision >= 1),
                updated_by TEXT NOT NULL,
                updated_at TIMESTAMPTZ NOT NULL,
                PRIMARY KEY (tenant_id, project_id, wbs_id),
                FOREIGN KEY (tenant_id, project_id)
                    REFERENCES project_lifecycle_projects(tenant_id, project_id) ON DELETE CASCADE,
                FOREIGN KEY (tenant_id, responsible_obs_id)
                    REFERENCES p6_obs_node(tenant_id, obs_id) ON DELETE RESTRICT
            )"""
        )
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS p6_wbs_obs_responsibility_audit (
                audit_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                wbs_id TEXT NOT NULL,
                actor_user_id TEXT NOT NULL,
                action TEXT NOT NULL CHECK (action='responsible_obs_changed'),
                before_state JSONB,
                after_state JSONB NOT NULL,
                occurred_at TIMESTAMPTZ NOT NULL
            )"""
        )
        self.connection.execute(
            """CREATE OR REPLACE FUNCTION cubi_p6_wbs_obs_audit_immutable()
            RETURNS trigger LANGUAGE plpgsql AS $
            BEGIN
                RAISE EXCEPTION 'P6_WBS_OBS_AUDIT_APPEND_ONLY';
            END;
            $"""
        )
        self.connection.execute(
            "DROP TRIGGER IF EXISTS p6_wbs_obs_audit_immutable "
            "ON p6_wbs_obs_responsibility_audit"
        )
        self.connection.execute(
            """CREATE TRIGGER p6_wbs_obs_audit_immutable
            BEFORE UPDATE OR DELETE ON p6_wbs_obs_responsibility_audit
            FOR EACH ROW EXECUTE FUNCTION cubi_p6_wbs_obs_audit_immutable()"""
        )

    def save_node(self, node: P6EPSNode, *, expected_revision: int | None = None) -> P6EPSNode:
        node.validate()
        if node.responsible_obs_id and self.connection.execute(
            "SELECT 1 FROM p6_obs_node WHERE tenant_id=%s AND obs_id=%s",
            (node.tenant_id, node.responsible_obs_id),
        ).fetchone() is None:
            raise P6EPSError("P6_EPS_RESPONSIBLE_OBS_NOT_FOUND")
        if node.parent_eps_id:
            if self.connection.execute(
                "SELECT 1 FROM p6_eps_node WHERE tenant_id=%s AND eps_id=%s",
                (node.tenant_id, node.parent_eps_id),
            ).fetchone() is None:
                raise P6EPSError("P6_EPS_PARENT_NOT_FOUND")
            current = node.parent_eps_id
            seen = {node.eps_id}
            while current:
                if current in seen:
                    raise P6EPSError("P6_EPS_HIERARCHY_CYCLE")
                seen.add(current)
                row = self.connection.execute(
                    "SELECT parent_eps_id FROM p6_eps_node WHERE tenant_id=%s AND eps_id=%s",
                    (node.tenant_id, current),
                ).fetchone()
                if row is None:
                    raise P6EPSError("P6_EPS_PARENT_NOT_FOUND")
                current = None if row[0] is None else str(row[0])
        row = self.connection.execute(
            "SELECT revision FROM p6_eps_node WHERE tenant_id=%s AND eps_id=%s FOR UPDATE",
            (node.tenant_id, node.eps_id),
        ).fetchone()
        if row is None:
            if expected_revision not in (None, 0):
                raise P6EPSError("P6_EPS_REVISION_CONFLICT")
            revision = 1
            self.connection.execute(
                "INSERT INTO p6_eps_node "
                "(tenant_id,eps_id,parent_eps_id,name,responsible_obs_id,sequence_number,revision) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s)",
                (node.tenant_id,node.eps_id,node.parent_eps_id,node.name,
                 node.responsible_obs_id,node.sequence_number,revision),
            )
        else:
            if expected_revision is None or int(row[0]) != expected_revision:
                raise P6EPSError("P6_EPS_REVISION_CONFLICT")
            revision = expected_revision + 1
            self.connection.execute(
                "UPDATE p6_eps_node SET parent_eps_id=%s,name=%s,responsible_obs_id=%s,"
                "sequence_number=%s,revision=%s WHERE tenant_id=%s AND eps_id=%s",
                (node.parent_eps_id,node.name,node.responsible_obs_id,node.sequence_number,
                 revision,node.tenant_id,node.eps_id),
            )
        return P6EPSNode(node.tenant_id,node.eps_id,node.name,node.parent_eps_id,
                         node.responsible_obs_id,node.sequence_number)

    def assign_project(
        self, tenant_id: str, project_id: str, eps_id: str, *,
        actor_user_id: str, occurred_at: Any, expected_revision: int | None = None,
    ) -> int:
        if self.connection.execute(
            "SELECT 1 FROM p6_eps_node WHERE tenant_id=%s AND eps_id=%s",
            (tenant_id, eps_id),
        ).fetchone() is None:
            raise P6EPSError("P6_EPS_NOT_FOUND")
        row = self.connection.execute(
            "SELECT revision FROM p6_project_eps_assignment "
            "WHERE tenant_id=%s AND project_id=%s FOR UPDATE",
            (tenant_id, project_id),
        ).fetchone()
        if row is None:
            if expected_revision not in (None, 0):
                raise P6EPSError("P6_EPS_REVISION_CONFLICT")
            revision = 1
            self.connection.execute(
                "INSERT INTO p6_project_eps_assignment "
                "(tenant_id,project_id,eps_id,revision,updated_by,updated_at) "
                "VALUES (%s,%s,%s,%s,%s,%s)",
                (tenant_id,project_id,eps_id,revision,actor_user_id,occurred_at),
            )
        else:
            if expected_revision is None or int(row[0]) != expected_revision:
                raise P6EPSError("P6_EPS_REVISION_CONFLICT")
            revision = expected_revision + 1
            self.connection.execute(
                "UPDATE p6_project_eps_assignment SET eps_id=%s,revision=%s,updated_by=%s,updated_at=%s "
                "WHERE tenant_id=%s AND project_id=%s",
                (eps_id,revision,actor_user_id,occurred_at,tenant_id,project_id),
            )
        return revision

    def list_nodes(self, tenant_id: str) -> tuple[P6EPSNode, ...]:
        rows = self.connection.execute(
            "SELECT eps_id,name,parent_eps_id,responsible_obs_id,sequence_number "
            "FROM p6_eps_node WHERE tenant_id=%s ORDER BY sequence_number,eps_id",
            (tenant_id,),
        ).fetchall()
        return tuple(P6EPSNode(tenant_id,str(r[0]),str(r[1]),None if r[2] is None else str(r[2]),
                               str(r[3]),int(r[4])) for r in rows)

    def assign_wbs_responsibility(
        self, tenant_id: str, project_id: str, wbs_id: str, responsible_obs_id: str, *,
        actor_user_id: str, occurred_at: Any, expected_revision: int | None = None,
    ) -> int:
        if self.connection.execute(
            "SELECT 1 FROM p6_obs_node WHERE tenant_id=%s AND obs_id=%s",
            (tenant_id, responsible_obs_id),
        ).fetchone() is None:
            raise P6EPSError("P6_WBS_RESPONSIBLE_OBS_NOT_FOUND")
        if self.connection.execute(
            "SELECT 1 FROM wbs_master WHERE tenant_id=%s AND project_id=%s AND wbs_id=%s",
            (tenant_id, project_id, wbs_id),
        ).fetchone() is None:
            raise P6EPSError("P6_WBS_NOT_FOUND")
        row = self.connection.execute(
            "SELECT responsible_obs_id,revision FROM p6_wbs_obs_responsibility "
            "WHERE tenant_id=%s AND project_id=%s AND wbs_id=%s FOR UPDATE",
            (tenant_id, project_id, wbs_id),
        ).fetchone()
        if row is None:
            if expected_revision not in (None, 0):
                raise P6EPSError("P6_WBS_RESPONSIBILITY_REVISION_CONFLICT")
            revision = 1
            self.connection.execute(
                "INSERT INTO p6_wbs_obs_responsibility "
                "(tenant_id,project_id,wbs_id,responsible_obs_id,revision,updated_by,updated_at) "
                "VALUES (%s,%s,%s,%s,1,%s,%s)",
                (tenant_id,project_id,wbs_id,responsible_obs_id,actor_user_id,occurred_at),
            )
        else:
            if expected_revision is None or int(row[1]) != expected_revision:
                raise P6EPSError("P6_WBS_RESPONSIBILITY_REVISION_CONFLICT")
            revision = expected_revision + 1
            self.connection.execute(
                "UPDATE p6_wbs_obs_responsibility SET responsible_obs_id=%s,revision=%s,"
                "updated_by=%s,updated_at=%s WHERE tenant_id=%s AND project_id=%s AND wbs_id=%s",
                (responsible_obs_id,revision,actor_user_id,occurred_at,tenant_id,project_id,wbs_id),
            )
        self.connection.execute(
            "INSERT INTO p6_wbs_obs_responsibility_audit "
            "(audit_id,tenant_id,project_id,wbs_id,actor_user_id,action,before_state,after_state,occurred_at) "
            "VALUES (%s,%s,%s,%s,%s,'responsible_obs_changed',%s::jsonb,%s::jsonb,%s)",
            (
                str(uuid.uuid4()),tenant_id,project_id,wbs_id,actor_user_id,
                None if row is None else json.dumps({
                    "responsible_obs_id":str(row[0]),"revision":int(row[1])
                }),
                json.dumps({"responsible_obs_id":responsible_obs_id,"revision":revision}),
                occurred_at,
            ),
        )
        return revision

    def get_wbs_responsibility(
        self, tenant_id: str, project_id: str, wbs_id: str,
    ) -> tuple[str, int] | None:
        row = self.connection.execute(
            "SELECT responsible_obs_id,revision FROM p6_wbs_obs_responsibility "
            "WHERE tenant_id=%s AND project_id=%s AND wbs_id=%s",
            (tenant_id,project_id,wbs_id),
        ).fetchone()
        return None if row is None else (str(row[0]),int(row[1]))
