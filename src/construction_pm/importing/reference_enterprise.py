"""Persist the Enterprise-owned rows of the reference bundle.

Engineering owns the schedule, resources, baselines, progress and cost facts.
The Enterprise layer owns the register and governance records: risks, issues,
documents, tasks, approvals, workflows, contracts, procurement, teams,
responsibilities, forms, timesheets, milestones and communication.

This module writes those rows into the same stores the product uses:

* risks           -> ``SQLiteRiskStore`` (project risk register)
* issues          -> ``SQLiteP6IssueRepository`` (project issue register)
* documents       -> ``SQLiteDocumentStore`` (document register)
* tasks           -> ``SQLiteEnterpriseTaskRepository`` (Enterprise task store)
* every other row -> ``EnterpriseWorkbenchStore`` (generic revisioned register)

Nothing here computes a schedule, a float, a cost or an earned value. Each row
is a fact from the frozen bundle; derived analytics stay with the canonical
services.

Idempotency: every record keeps the workbook identity and is inserted only when
it is absent, so a restart never duplicates a row and never overwrites an
operator edit. A per-project marker row records completion and counts.

Honest gaps (recorded, not dropped):

* ``timesheets`` are per-resource weekly rows (resource_id / week_ending /
  regular+overtime hours). The Enterprise timesheet contract is per user and
  per work date, and the workbook carries no user identity, so the rows are
  kept with their own fields and no ``user_id`` is invented.
* ``commitments``, ``actual_costs`` and ``cost_periods`` have no canonical
  entity in the preview stores; they stay in the bundle and are reported as
  unsupported rather than forced into an unrelated table.
* ``document_register`` rows have no file bytes. The document store requires a
  storage reference and a content hash, so the hash is computed over the
  canonical register payload and the reference is marked ``reference://``; no
  binary drawing is claimed to exist.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from typing import Mapping, Protocol, Sequence

from construction_pm.backend_p0.models import BackendScope
from construction_pm.document_persistence import DocumentRecord
from construction_pm.enterprise_task import (
    EnterpriseTask,
    EnterpriseTaskPriority,
    EnterpriseTaskReference,
    EnterpriseTaskReferenceType,
    EnterpriseTaskStatus,
)
from construction_pm.enterprise_task_sqlite_repository import (
    SQLiteEnterpriseTaskRepository,
)
from construction_pm.enterprise_workbench_http import EnterpriseWorkbenchStore
from construction_pm.p6_issue_repository import P6Issue
from construction_pm.risk_persistence import Risk

from .reference_persistence import (
    REFERENCE_CLOCK,
    _decimal,
    _rows,
    _text,
    load_bundle,
)

ENTERPRISE_CONTRACT = "cubi-reference-enterprise.v1"
DATA_DATE = date(2026, 11, 22)
STATE_DATE = date(2026, 11, 22)

_RISK_CATEGORY = {
    "procurement": "commercial",
    "interface": "other",
    "schedule": "schedule",
    "engineering": "technical",
    "resources": "resource",
    "cost": "cost",
    "external": "external",
    "permits": "external",
    "quality": "quality",
    "hse": "safety",
    "operations": "other",
    "commissioning": "technical",
    "technical": "technical",
}

_DOC_STATUS = {
    "Approved": "approved",
    "IFC": "approved",
    "IFA": "submitted",
    "In Progress": "draft",
    "Rejected": "rejected",
    "Superseded": "superseded",
}

_ISSUE_STATUS = {
    "Open": "open",
    "In Progress": "in_progress",
    "Resolved": "resolved",
    "Closed": "closed",
}

_ISSUE_PRIORITY = {
    "Low": "low",
    "Medium": "normal",
    "High": "high",
    "Critical": "critical",
}

_TASK_STATUS = {
    "Open": "open",
    "In Progress": "in_progress",
    "Blocked": "blocked",
    "Completed": "completed",
    "Cancelled": "cancelled",
}

# Rows with no canonical entity in the preview stores. Kept explicit so the
# report can state exactly what is not connected instead of hiding it. These
# rows stay in the frozen bundle and are reported, never silently dropped.
UNSUPPORTED_SHEETS: Mapping[str, str] = {
    "commitments": "no canonical commitment entity in the preview stores",
    "actual_costs": "derived into period actuals; the standalone register has no entity",
    "cost_periods": "cost calendar is published from settings; the register has no entity",
}


class EnterpriseStoreSet(Protocol):
    risks: object
    issues: object
    documents: object


@dataclass(frozen=True)
class EnterpriseImportResult:
    project_id: str
    created: Mapping[str, int]
    present: Mapping[str, int]
    missing: Mapping[str, int]
    unsupported: tuple[str, ...]
    status: str


def ensure_reference_enterprise(
    connection,
    repositories: EnterpriseStoreSet,
    enterprise_store: EnterpriseWorkbenchStore,
    *,
    tenant_id: str,
    actor_id: str = "preview-admin",
    clock: datetime = REFERENCE_CLOCK,
    bundle: Mapping[str, object] | None = None,
    tasks_repository: object | None = None,
    dialect: str = "sqlite",
) -> tuple[EnterpriseImportResult, ...]:
    """Insert every Enterprise register row that is not present yet.

    The same rows are written for both adapters; ``dialect`` only selects the
    placeholder and JSON operator used by the state marker and presence
    counts, and ``tasks_repository`` lets the production caller pass the
    PostgreSQL task store instead of the SQLite one.
    """

    document = bundle if bundle is not None else load_bundle()
    projects = document.get("projects")
    if not isinstance(projects, Mapping):
        raise ValueError("REFERENCE_BUNDLE_HAS_NO_PROJECTS")
    _ensure_state_table(connection, dialect)

    results: list[EnterpriseImportResult] = []
    for project_id in sorted(projects):
        entry = projects[project_id]
        if not isinstance(entry, Mapping):
            continue
        revision = _revision(entry)
        scope = BackendScope(tenant_id, str(project_id), revision)
        created = _ensure_project_records(
            connection,
            repositories,
            enterprise_store,
            tenant_id=tenant_id,
            project_id=str(project_id),
            entry=entry,
            actor_id=actor_id,
            clock=clock,
            tasks_repository=tasks_repository,
        )
        expected = _expected_counts(entry)
        present = _present_counts(
            connection,
            repositories,
            tenant_id,
            str(project_id),
            scope,
            tasks_repository=tasks_repository,
            dialect=dialect,
        )
        missing = {
            key: total - present.get(key, 0)
            for key, total in expected.items()
            if total > present.get(key, 0)
        }
        unsupported = tuple(
            sheet for sheet in UNSUPPORTED_SHEETS if entry.get(sheet)
        )
        # ``missing`` means a representable source row is absent from the
        # stores; unsupported sheets are reported separately because there is
        # no canonical entity to hold them yet.
        status = "COMPLETE" if not missing else "PARTIAL"
        _record_state(
            connection,
            tenant_id,
            str(project_id),
            status,
            {"created": created, "present": present, "missing": missing, "unsupported": list(unsupported)},
            clock,
            dialect=dialect,
        )
        results.append(
            EnterpriseImportResult(
                project_id=str(project_id),
                created=dict(created),
                present=dict(present),
                missing=dict(missing),
                unsupported=unsupported,
                status=status,
            )
        )
    if dialect == "sqlite":
        connection.commit()
    return tuple(results)


# --------------------------------------------------------------------------
# per-project orchestration
# --------------------------------------------------------------------------


def _ensure_project_records(
    connection,
    repositories: EnterpriseStoreSet,
    enterprise_store: EnterpriseWorkbenchStore,
    *,
    tenant_id: str,
    project_id: str,
    entry: Mapping[str, object],
    actor_id: str,
    clock: datetime,
    tasks_repository: object | None = None,
) -> dict[str, int]:
    revision = _revision(entry)
    scope = BackendScope(tenant_id, project_id, revision)
    created: dict[str, int] = {}

    created["risks"] = _ensure_risks(repositories, scope, entry, actor_id=actor_id, clock=clock)
    created["issues"] = _ensure_issues(repositories, scope, entry, actor_id=actor_id, clock=clock)
    created["documents"] = _ensure_documents(repositories, scope, entry, actor_id=actor_id, clock=clock)
    created["tasks"] = _ensure_tasks(
        connection,
        entry,
        tenant_id=tenant_id,
        actor_id=actor_id,
        clock=clock,
        tasks_repository=tasks_repository,
    )

    kind_rows = _enterprise_kind_rows(entry, project_id)
    for kind, rows in kind_rows.items():
        written = 0
        for record_id, payload in rows:
            if enterprise_store.ensure_record(
                tenant_id, kind, record_id, payload, actor_id=actor_id
            ):
                written += 1
        created[kind] = written
    return created


def _revision(entry: Mapping[str, object]) -> int:
    project = entry.get("project")
    if isinstance(project, Mapping):
        value = project.get("project_revision")
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
            return value
    return 1


def _expected_counts(entry: Mapping[str, object]) -> dict[str, int]:
    counts = {
        "risks": len(_rows(entry, "risk_register")),
        "issues": len(_rows(entry, "issue_register")),
        "documents": len(_rows(entry, "document_register")),
        "tasks": len(_rows(entry, "team_tasks")),
    }
    counts.update({kind: len(rows) for kind, rows in _enterprise_kind_rows(entry, "").items()})
    return counts


def _present_counts(
    connection,
    repositories: EnterpriseStoreSet,
    tenant_id: str,
    project_id: str,
    scope: BackendScope,
    *,
    tasks_repository: object | None = None,
    dialect: str = "sqlite",
) -> dict[str, int]:
    """Count what is actually stored, never what was merely attempted."""

    tasks = tasks_repository or SQLiteEnterpriseTaskRepository(connection)

    counts = {
        "risks": len(repositories.risks.list_risks(tenant_id, project_id)),
        "issues": len(repositories.issues.list(scope)),
        "documents": len(
            repositories.documents.list_all(tenant_id=tenant_id, project_id=project_id)
        ),
        "tasks": len(
            tasks.list_for_tenant(tenant_id, limit=500, project_id=project_id)
        ),
    }
    if dialect == "postgres":
        rows = connection.execute(
            "SELECT kind, COUNT(*) FROM enterprise_records "
            "WHERE tenant_id=%s AND (payload_json::jsonb ->> 'project_id')=%s "
            "GROUP BY kind",
            (tenant_id, project_id),
        ).fetchall()
    else:
        rows = connection.execute(
            "SELECT kind, COUNT(*) FROM enterprise_records "
            "WHERE tenant_id=? AND json_extract(payload_json, '$.project_id')=? "
            "GROUP BY kind",
            (tenant_id, project_id),
        ).fetchall()
    for kind, total in rows:
        counts[str(kind)] = int(total)
    return counts


# --------------------------------------------------------------------------
# project risk register
# --------------------------------------------------------------------------


def _ensure_risks(repositories, scope: BackendScope, entry, *, actor_id, clock) -> int:
    existing = {
        stored.risk.risk_id
        for stored in repositories.risks.list_risks(scope.tenant_id, scope.project_id)
    }
    responses: dict[str, list[Mapping[str, object]]] = {}
    for row in _rows(entry, "risk_responses"):
        responses.setdefault(str(row.get("risk_id")), []).append(row)

    written = 0
    for row in _rows(entry, "risk_register"):
        risk_id = str(row.get("risk_id"))
        if risk_id in existing:
            continue
        category = _RISK_CATEGORY.get(
            str(row.get("category") or "").strip().lower(), "other"
        )
        response_rows = responses.get(risk_id, [])
        risk = Risk(
            tenant_id=scope.tenant_id,
            project_id=scope.project_id,
            risk_id=risk_id,
            title=str(row.get("risk_title") or risk_id),
            description=_risk_description(row, category, response_rows),
            category=category,
            status="open",
            probability=int(row.get("probability_1_5") or 1),
            impact=int(row.get("impact_1_5") or 1),
            response_strategy="mitigate",
            owner=str(row.get("owner_obs_id") or "unassigned"),
            date_identified=STATE_DATE.isoformat(),
            response_owner=_text(response_rows[0].get("action_owner")) if response_rows else None,
            response_due_date=_text(response_rows[0].get("due_date")) if response_rows else None,
        )
        repositories.risks.create_risk(
            risk,
            idempotency_key=f"cubi-reference:{risk_id}",
            actor_id=actor_id,
            occurred_at=clock,
        )
        written += 1
    return written


def _risk_description(row, category: str, responses: Sequence[Mapping[str, object]]) -> str:
    """Keep every source field the canonical risk model has no column for.

    The register has no description, so the title is the subject and the
    remaining columns are appended as labelled facts; responses are folded in
    because the store has a single risk row.
    """
    parts = [
        f"Source category: {row.get('category')} (mapped to {category}).",
        f"Source risk level label: {row.get('risk_level')}; source score {row.get('risk_score')}.",
        f"WBS: {row.get('wbs_id')}. Owner OBS: {row.get('owner_obs_id')}.",
    ]
    for item in responses:
        parts.append(
            "Response "
            f"{item.get('response_id')}: {item.get('response_strategy')} — "
            f"{item.get('response_action')} "
            f"(owner {item.get('action_owner')}, due {item.get('due_date')}, "
            f"status {item.get('status')})."
        )
    return " ".join(parts)


# --------------------------------------------------------------------------
# issue register
# --------------------------------------------------------------------------


def _ensure_issues(repositories, scope: BackendScope, entry, *, actor_id, clock) -> int:
    existing = {issue.issue_id for issue in repositories.issues.list(scope)}
    written = 0
    for row in _rows(entry, "issue_register"):
        issue_id = str(row.get("issue_id"))
        if issue_id in existing:
            continue
        issue = P6Issue(
            scope=scope,
            issue_id=issue_id,
            title=str(row.get("issue_title") or issue_id),
            description="",
            issue_type="other",
            status=_ISSUE_STATUS.get(str(row.get("status")), "open"),
            priority=_ISSUE_PRIORITY.get(str(row.get("priority")), "normal"),
            owner=str(row.get("owner_obs_id") or "unassigned"),
            date_identified=_text(row.get("date_raised")) or "",
            activity_id=_text(row.get("related_activity_id")),
        )
        repositories.issues.create(
            issue, actor_id=actor_id, occurred_at=clock.isoformat()
        )
        written += 1
    return written


# --------------------------------------------------------------------------
# document register
# --------------------------------------------------------------------------


def _ensure_documents(repositories, scope: BackendScope, entry, *, actor_id, clock) -> int:
    existing = {
        stored.document.document_id
        for stored in repositories.documents.list_all(
            tenant_id=scope.tenant_id, project_id=scope.project_id
        )
    }
    revisions: dict[str, list[Mapping[str, object]]] = {}
    for row in _rows(entry, "document_revisions"):
        revisions.setdefault(str(row.get("document_id")), []).append(row)
    activity_links: dict[str, list[str]] = {}
    for row in _rows(entry, "activity_documents"):
        activity_links.setdefault(str(row.get("document_id")), []).append(
            str(row.get("activity_id"))
        )

    written = 0
    for row in _rows(entry, "document_register"):
        document_id = str(row.get("document_id"))
        if document_id in existing:
            continue
        revision_rows = revisions.get(document_id, [])
        payload = {
            "register": dict(row),
            "revisions": [dict(item) for item in revision_rows],
        }
        content_hash = "sha256:" + hashlib.sha256(
            json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
        ).hexdigest()
        linked = tuple(activity_links.get(document_id, ()))
        document = DocumentRecord(
            document_id=document_id,
            tenant_id=scope.tenant_id,
            project_id=scope.project_id,
            resource_type=_document_type(str(row.get("document_title") or "")),
            title=str(row.get("document_title") or document_id),
            status=_DOC_STATUS.get(str(row.get("document_status")), "draft"),
            storage_ref=(
                f"reference://{scope.project_id}/{document_id}/"
                f"rev-{row.get('current_revision') or 'A'}"
            ),
            content_hash=content_hash,
            linked_entity_refs=linked,
        )
        repositories.documents.persist(
            document,
            idempotency_key=f"cubi-reference:{document_id}",
            actor_id=actor_id,
            occurred_at=clock,
        )
        written += 1
    return written


def _document_type(title: str) -> str:
    lowered = title.lower()
    if any(word in lowered for word in ("pfd", "p&id", "plot plan", "arrangement")):
        return "drawing"
    return "submittal"


# --------------------------------------------------------------------------
# Enterprise task store
# --------------------------------------------------------------------------


def _ensure_tasks(
    connection,
    entry,
    *,
    tenant_id: str,
    actor_id: str,
    clock,
    tasks_repository: object | None = None,
) -> int:
    repository = tasks_repository or SQLiteEnterpriseTaskRepository(connection)
    repository.initialize()
    project_id = _text(entry.get("project", {}).get("project_id")) or ""
    existing = {
        stored.task.task_id
        for stored in repository.list_for_tenant(
            tenant_id, limit=500, project_id=project_id
        )
    }
    written = 0
    for row in _rows(entry, "team_tasks"):
        task_id = str(row.get("team_task_id"))
        if task_id in existing:
            continue
        due = _due_at(row.get("due_date"))
        references = ()
        activity_id = _text(row.get("related_activity_id"))
        if activity_id:
            references = (
                EnterpriseTaskReference(
                    reference_type=EnterpriseTaskReferenceType.ENGINEERING_ACTIVITY,
                    reference_id=activity_id,
                ),
            )
        task = EnterpriseTask(
            task_id=task_id,
            tenant_id=tenant_id,
            title=str(row.get("task_title") or task_id),
            created_by_user_id=actor_id,
            created_at=clock,
            status=EnterpriseTaskStatus(
                _TASK_STATUS.get(str(row.get("status")), "open")
            ),
            priority=EnterpriseTaskPriority.NORMAL,
            description=(
                f"Assigned role: {row.get('assigned_role')}. "
                + (
                    "Shared in-progress project task record."
                    if project_id == "CUBI-DAM-001"
                    else "DEMO/SYNTHETIC reference team task."
                )
            ),
            project_id=project_id or None,
            due_at=due,
            related_refs=references,
        )
        repository.create(
            task,
            idempotency_key=f"cubi-reference:{task_id}",
            actor_id=actor_id,
            occurred_at=clock,
        )
        written += 1
    return written


def _due_at(value: object) -> datetime | None:
    """Due dates are calendar dates in the workbook; month end is 17:00 UTC."""
    text = _text(value)
    if not text:
        return None
    try:
        parsed = date.fromisoformat(text)
    except ValueError:
        return None
    return datetime.combine(parsed, time(17, 0), tzinfo=timezone.utc)


# --------------------------------------------------------------------------
# generic Enterprise register rows
# --------------------------------------------------------------------------


def _enterprise_kind_rows(
    entry: Mapping[str, object], project_id: str
) -> dict[str, list[tuple[str, dict[str, object]]]]:
    """Return ``{kind: [(record_id, payload)]}`` for the generic register."""

    project = project_id or str(entry.get("project", {}).get("project_id") or "")
    rows: dict[str, list[tuple[str, dict[str, object]]]] = {}

    def add(kind: str, record_id: object, payload: dict[str, object]) -> None:
        if not record_id:
            return
        body = {
            **payload,
            "project_id": project,
            "demo": project != "CUBI-DAM-001",
        }
        rows.setdefault(kind, []).append((str(record_id), body))

    for row in _rows(entry, "organization"):
        add(
            "organizations",
            row.get("organization_id"),
            {
                "name": row.get("organization_name"),
                "parent_organization_id": row.get("parent_organization_id"),
                "department_head_role": row.get("department_head_role"),
                "status": "active",
            },
        )
    for row in _rows(entry, "project_teams"):
        add(
            "teams",
            row.get("team_id"),
            {
                "name": row.get("team_name"),
                "organization_id": row.get("organization_id"),
                "team_lead_role": row.get("team_lead_role"),
                "status": "active",
            },
        )
    for row in _rows(entry, "responsibility_assignments"):
        add(
            "responsibilities",
            row.get("responsibility_id"),
            {
                "obs_id": row.get("obs_id"),
                "role": row.get("role"),
                "raci": row.get("raci"),
                "responsibility": row.get("responsibility"),
            },
        )
    for row in _rows(entry, "contracts"):
        add("contracts", row.get("contract_id"), dict(row))
    for row in _rows(entry, "contract_packages"):
        add("contract_packages", row.get("package_id"), dict(row))
    for row in _rows(entry, "procurement_register"):
        add("procurement", row.get("procurement_id"), dict(row))
    for row in _rows(entry, "vendor_register"):
        add("vendors", row.get("vendor_id"), dict(row))
    for row in _rows(entry, "change_requests"):
        add("change_requests", row.get("change_request_id"), dict(row))
    for row in _rows(entry, "communication_log"):
        add("communication", row.get("communication_id"), dict(row))
    for row in _rows(entry, "approval_records"):
        add(
            "approvals",
            row.get("approval_id"),
            {
                "title": f"{row.get('object_type')} approval: {row.get('object_id')}",
                "object_type": row.get("object_type"),
                "object_id": row.get("object_id"),
                "decision": row.get("decision"),
                "decision_date": row.get("decision_date"),
                "approver_role": row.get("approver_role"),
                "comment": row.get("comment"),
                "status": "approved" if "approved" in str(row.get("decision", "")).lower() else "pending",
            },
        )
    for row in _rows(entry, "forms_register"):
        add(
            "forms",
            row.get("form_id"),
            {
                "name": row.get("form_name"),
                "fields": [],
                "form_type": row.get("form_type"),
                "version": row.get("version"),
                "status": row.get("status"),
            },
        )
    for row in _rows(entry, "project_milestones"):
        add(
            "milestones",
            row.get("milestone_id"),
            {
                "milestone_name": row.get("milestone_name"),
                "activity_id": row.get("activity_id"),
                "baseline_date": row.get("baseline_date"),
                "forecast_date": row.get("forecast_date"),
                "milestone_status": row.get("milestone_status"),
            },
        )

    # Workflows: one record per template; instances are nested because the
    # store has a single workflow entity and every instance row must survive.
    instances: dict[str, list[dict[str, object]]] = {}
    for row in _rows(entry, "workflow_instances"):
        instances.setdefault(str(row.get("workflow_template_id")), []).append(dict(row))
    for row in _rows(entry, "workflow_templates"):
        template_id = str(row.get("workflow_template_id"))
        steps = [
            step.strip()
            for step in str(row.get("steps") or "").split(">")
            if step.strip()
        ]
        add(
            "workflows",
            template_id,
            {
                "name": row.get("template_name"),
                "steps": steps,
                "version": row.get("version"),
                "active": bool(row.get("active")),
                "instances": instances.get(template_id, []),
                "status": "published" if row.get("active") else "draft",
            },
        )
    for row in _rows(entry, "timesheets"):
        add(
            "timesheets",
            row.get("timesheet_id"),
            {
                # Source row is per resource and per week. ``user_id`` and
                # ``work_date`` are deliberately absent: the workbook carries
                # no user identity and no single work date.
                "resource_id": row.get("resource_id"),
                "week_ending": row.get("week_ending"),
                "regular_hours": row.get("regular_hours"),
                "overtime_hours": row.get("overtime_hours"),
                "hours": _decimal(row.get("regular_hours")) + _decimal(row.get("overtime_hours")),
                "approval_status": row.get("approval_status"),
                "source": (
                    "Initial project timesheet data"
                    if project == "CUBI-DAM-001"
                    else "workbook"
                ),
            },
        )
    return rows


# --------------------------------------------------------------------------
# state marker
# --------------------------------------------------------------------------


def _ensure_state_table(connection, dialect: str = "sqlite") -> None:
    connection.execute(
        """CREATE TABLE IF NOT EXISTS cubi_reference_enterprise (
            tenant_id TEXT NOT NULL,
            project_id TEXT NOT NULL,
            status TEXT NOT NULL,
            imported_at TEXT NOT NULL,
            counts_json TEXT NOT NULL,
            PRIMARY KEY (tenant_id, project_id)
        )"""
    )


def _record_state(
    connection,
    tenant_id: str,
    project_id: str,
    status: str,
    counts: Mapping[str, int],
    clock: datetime,
    *,
    dialect: str = "sqlite",
) -> None:
    marker = "%s" if dialect == "postgres" else "?"
    connection.execute(
        "INSERT INTO cubi_reference_enterprise "
        "(tenant_id, project_id, status, imported_at, counts_json) "
        f"VALUES ({marker},{marker},{marker},{marker},{marker}) "
        "ON CONFLICT (tenant_id, project_id) DO UPDATE SET "
        "status=excluded.status, imported_at=excluded.imported_at, "
        "counts_json=excluded.counts_json",
        (
            tenant_id,
            project_id,
            status,
            clock.isoformat(),
            json.dumps(dict(sorted(counts.items())), sort_keys=True),
        ),
    )


def read_enterprise_state(
    connection, tenant_id: str, *, dialect: str = "sqlite"
) -> tuple[dict[str, object], ...]:
    marker = "%s" if dialect == "postgres" else "?"
    rows = connection.execute(
        "SELECT project_id, status, imported_at, counts_json "
        f"FROM cubi_reference_enterprise WHERE tenant_id={marker} ORDER BY project_id",
        (tenant_id,),
    ).fetchall()
    return tuple(
        {
            "project_id": row[0],
            "status": row[1],
            "imported_at": row[2],
            "counts": json.loads(row[3]),
        }
        for row in rows
    )
