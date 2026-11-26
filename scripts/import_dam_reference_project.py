#!/usr/bin/env python3
"""Preflight and, when explicitly permitted, import the shared dam build workspace.

This command never runs migrations or changes authentication, sessions,
memberships, roles, or the three frozen CUBI-REF projects. It imports one
in-memory structured bundle through the canonical PostgreSQL repositories and
shared scheduling engine. The generated bundle is not persisted as a workbook.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Mapping
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from construction_pm.importing.dam_reference_project import (
    PROJECT_ID,
    PROJECT_NAME,
    build_dam_reference_bundle,
)
from construction_pm.importing.reference_journal import IMPORT_STATUS_COMPLETE
from construction_pm.importing.reference_postgres import (
    ensure_reference_projects_postgres,
    read_import_manifests,
)

def _import_is_complete(manifest: object) -> bool:
    """A recorded import is complete only at the journal's canonical status."""

    return isinstance(manifest, Mapping) and manifest.get("status") == IMPORT_STATUS_COMPLETE

def _dsn(value: str | None) -> str:
    dsn = (value or os.environ.get("CONSTRUCTION_PM_DATABASE_URL")
           or os.environ.get("POSTGRES_URL_NON_POOLING") or "").strip()
    if not dsn.startswith(("postgresql://", "postgres://")):
        raise SystemExit("A PostgreSQL DSN must be supplied through the environment or --dsn.")
    return dsn

def _connect(dsn: str):
    import psycopg
    return psycopg.connect(dsn, autocommit=False, connect_timeout=15)

def _preflight(connection, tenant_id: str) -> dict[str, object]:
    rows = connection.execute(
        "SELECT c.relname, c.relrowsecurity, "
        "EXISTS (SELECT 1 FROM pg_policy p WHERE p.polrelid=c.oid "
        "AND p.polname='cubi_block_direct_api_clients'), "
        "has_table_privilege('anon', c.oid, 'SELECT'), "
        "has_table_privilege('anon', c.oid, 'INSERT'), "
        "has_table_privilege('anon', c.oid, 'UPDATE'), "
        "has_table_privilege('anon', c.oid, 'DELETE'), "
        "has_table_privilege('authenticated', c.oid, 'SELECT'), "
        "has_table_privilege('authenticated', c.oid, 'INSERT'), "
        "has_table_privilege('authenticated', c.oid, 'UPDATE'), "
        "has_table_privilege('authenticated', c.oid, 'DELETE') "
        "FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
        "WHERE n.nspname='public' AND c.relkind IN ('r','p') ORDER BY c.relname"
    ).fetchall()
    unprotected = [
        str(row[0]) for row in rows if not bool(row[1]) or not bool(row[2])
    ]
    direct_client_access = [
        str(row[0]) for row in rows if any(bool(value) for value in row[3:])
    ]
    missing = connection.execute(
        "SELECT required.table_name FROM (VALUES "
        "('project_lifecycle_projects'),('cubi_reference_project'),"
        "('wbs_master'),('activity_master'),('activity_wbs_assignment'),"
        "('relationship_master'),('project_schedule_settings'),"
        "('schedule_input_snapshot'),('schedule_calculation_context'),"
        "('p6_resource_master'),('p6_resource_assignment'),"
        "('p6_resource_assignment_period_value'),('p6_resource_rate_fact'),"
        "('p6_resource_rate_supersession'),('p6_resource_capacity_segment'),"
        "('p6_resource_capacity_supersession'),('calendar_master'),"
        "('calendar_master_snapshot'),('calendar_exception'),"
        "('calendar_work_hour_rule'),('activity_calendar_assignment'),"
        "('relationship_lag_calendar_assignment'),('p6_baseline'),"
        "('p6_baseline_activity'),('p6_activity_period_actual'),"
        "('p6_expense'),('p6_financial_period'),('p6_role'),"
        "('p6_cost_account'),('p6_obs_node'),"
        "('p6_issue'),('p6_issue_event'),('project_risk'),('project_risk_audit'),"
        "('project_documents'),('project_document_audit'),('enterprise_records'),"
        "('enterprise_tasks'),('enterprise_task_idempotency'),"
        "('enterprise_task_dependencies'),('enterprise_task_audit'),"
        "('enterprise_idempotency'),('enterprise_audit'),"
        "('enterprise_approval_decisions'),('project_budget_line'),"
        "('project_budget_change'),('project_budget_funding'),"
        "('project_budget_audit'),('cubi_reference_enterprise'),"
        "('cubi_reference_import'),('cubi_reference_schedule_run')"
        ") AS required(table_name) "
        "WHERE NOT EXISTS (SELECT 1 FROM information_schema.tables t "
        "WHERE t.table_schema='public' AND t.table_name=required.table_name)"
    ).fetchall()
    exists = connection.execute(
        "SELECT 1 FROM public.project_lifecycle_projects "
        "WHERE tenant_id=%s AND project_id=%s",
        (tenant_id, PROJECT_ID),
    ).fetchone()
    return {
        "public_table_count": len(rows),
        "rls_or_policy_missing_tables": unprotected,
        "direct_client_privilege_tables": direct_client_access,
        "missing_required_tables": [str(row[0]) for row in missing],
        "project_already_exists": exists is not None,
        "ready": not unprotected and not direct_client_access and not missing,
    }

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tenant", default="cubi-platform")
    parser.add_argument("--dsn")
    parser.add_argument("--apply", action="store_true",
                        help="persist only after all read-only preflight gates pass")
    args = parser.parse_args(argv)

    connection = _connect(_dsn(args.dsn))
    try:
        audit = _preflight(connection, args.tenant)
        if args.tenant != "cubi-platform":
            # The current canonical owner tenant was verified during the
            # read-only account audit. A different tenant needs explicit review.
            audit["tenant_review_required"] = True
            audit["ready"] = False
        if not audit["ready"]:
            connection.rollback()
            output = {"project_id": PROJECT_ID, "project_name": PROJECT_NAME,
                      "status": "BLOCKED", "preflight": audit}
            print(json.dumps(output, indent=2))
            return 2
        if not args.apply:
            connection.rollback()
            output = {"project_id": PROJECT_ID, "project_name": PROJECT_NAME,
                      "status": "PREFLIGHT_PASSED_NOT_IMPORTED", "preflight": audit}
            print(json.dumps(output, indent=2))
            return 0
        already_registered = False
        if audit["project_already_exists"]:
            manifests = read_import_manifests(connection, args.tenant)
            existing = next((item for item in manifests if item["project_id"] == PROJECT_ID), None)
            if not _import_is_complete(existing):
                raise RuntimeError("PROJECT_ID_COLLISION_OR_PARTIAL_IMPORT_REQUIRES_MANUAL_REVIEW")
            # Re-run the canonical idempotent importer even when Engineering
            # already exists: this also verifies/repairs any incomplete
            # Enterprise register rows before the project is called ready.
            already_registered = True

        outcome = ensure_reference_projects_postgres(
            connection,
            tenant_id=args.tenant,
            member_user_ids=(),
            bundle=build_dam_reference_bundle(),
            initialize_schema=False,
        )
        imported = next((item for item in outcome.projects if item.project_id == PROJECT_ID), None)
        if imported is None and not already_registered:
            # The importer skips an existing project without rebuilding its
            # in-memory result, so an absent entry is only a failure when this
            # command was not already told the project is registered.
            raise RuntimeError("DAM_PROJECT_IMPORT_NOT_CONFIRMED")
        enterprise = next(
            (item for item in outcome.enterprise if item.project_id == PROJECT_ID), None
        )
        if enterprise is None or enterprise.status != "COMPLETE" or enterprise.missing:
            raise RuntimeError("DAM_ENTERPRISE_IMPORT_NOT_COMPLETE")
        # Canonical importer commits only after schedule snapshot and engine
        # success; verify the project is registered and its run is successful.
        manifest = next((item for item in outcome.manifests if item["project_id"] == PROJECT_ID), None)
        if not _import_is_complete(manifest):
            raise RuntimeError("DAM_PROJECT_IMPORT_MANIFEST_NOT_SUCCESSFUL")
        if imported is not None:
            revision = imported.project_revision
            snapshot_id = imported.snapshot.snapshot_id
            counts = dict(imported.counts)
        else:
            revision_row = connection.execute(
                "SELECT project_revision FROM cubi_reference_project "
                "WHERE tenant_id=%s AND project_id=%s",
                (args.tenant, PROJECT_ID),
            ).fetchone()
            if revision_row is None:
                raise RuntimeError("DAM_PROJECT_REGISTRY_ROW_MISSING")
            revision = int(revision_row[0])
            snapshot_row = connection.execute(
                "SELECT snapshot_id FROM schedule_input_snapshot "
                "WHERE tenant_id=%s AND project_id=%s ORDER BY created_at DESC, snapshot_id DESC LIMIT 1",
                (args.tenant, PROJECT_ID),
            ).fetchone()
            snapshot_id = None if snapshot_row is None else str(snapshot_row[0])
            counts = dict(manifest["counts"])
        print(json.dumps({
            "project_id": PROJECT_ID,
            "status": "ALREADY_IMPORTED_AND_VERIFIED" if already_registered else "IMPORTED",
            "project_revision": revision,
            "snapshot_id": snapshot_id,
            "schedule_status": manifest["status"],
            "engineering_counts": counts,
            "enterprise_counts": dict(enterprise.present),
            "enterprise_status": enterprise.status,
            "manifest": manifest,
        }, indent=2, default=str))
        return 0
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

if __name__ == "__main__":
    raise SystemExit(main())
