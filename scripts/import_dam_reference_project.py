#!/usr/bin/env python3
"""Preflight and, when explicitly permitted, import the shared dam QA project.

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
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from construction_pm.importing.dam_reference_project import (
    PROJECT_ID,
    PROJECT_NAME,
    build_dam_reference_bundle,
)
from construction_pm.importing.reference_postgres import (
    ensure_reference_projects_postgres,
    read_import_manifests,
)

def _dsn(value: str | None) -> str:
    dsn = (value or os.environ.get("CONSTRUCTION_PM_DATABASE_URL")
           or os.environ.get("POSTGRES_URL_NON_POOLING") or "").strip()
    if not dsn.startswith(("postgresql://", "postgres://")):
        raise SystemExit("A PostgreSQL DSN must be supplied through the environment or --dsn.")
    return dsn

def _connect(dsn: str):
    import psycopg
    return psycopg.connect(dsn, autocommit=False, connect_timeout=15)

def _preflight(connection) -> dict[str, object]:
    rows = connection.execute(
        "SELECT c.relname, c.relrowsecurity "
        "FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
        "WHERE n.nspname='public' AND c.relkind IN ('r','p') ORDER BY c.relname"
    ).fetchall()
    unprotected = [str(name) for name, enabled in rows if not bool(enabled)]
    missing = connection.execute(
        "SELECT required.table_name FROM (VALUES "
        "('project_lifecycle_projects'),('cubi_reference_project'),"
        "('wbs_master'),('activity_master'),('activity_wbs_assignment'),"
        "('relationship_master'),('project_schedule_settings'),"
        "('schedule_input_snapshot'),('schedule_calculation_context'),"
        "('p6_resource_master'),('p6_resource_assignment'),"
        "('p6_resource_rate'),('p6_resource_capacity'),"
        "('p6_calendar_master'),('p6_calendar_snapshot'),"
        "('p6_baseline'),('p6_baseline_activity'),"
        "('cubi_reference_import'),('cubi_reference_schedule_run')"
        ") AS required(table_name) "
        "WHERE NOT EXISTS (SELECT 1 FROM information_schema.tables t "
        "WHERE t.table_schema='public' AND t.table_name=required.table_name)"
    ).fetchall()
    exists = connection.execute(
        "SELECT 1 FROM public.project_lifecycle_projects "
        "WHERE tenant_id=%s AND project_id=%s",
        ("cubi-platform", PROJECT_ID),
    ).fetchone()
    return {
        "public_table_count": len(rows),
        "rls_disabled_tables": unprotected,
        "missing_required_tables": [str(row[0]) for row in missing],
        "project_already_exists": exists is not None,
        "ready": not unprotected and not missing,
    }

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tenant", default="cubi-platform")
    parser.add_argument("--dsn")
    parser.add_argument("--preflight-only", action="store_true", default=True)
    parser.add_argument("--apply", action="store_true",
                        help="persist only after all read-only preflight gates pass")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    connection = _connect(_dsn(args.dsn))
    try:
        audit = _preflight(connection)
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
        if audit["project_already_exists"]:
            manifests = read_import_manifests(connection, args.tenant)
            existing = next((item for item in manifests if item["project_id"] == PROJECT_ID), None)
            if existing and existing["status"] == "SUCCESS":
                connection.rollback()
                print(json.dumps({"project_id": PROJECT_ID, "status": "ALREADY_IMPORTED",
                                  "manifest": existing}, indent=2, default=str))
                return 0
            raise RuntimeError("PROJECT_ID_COLLISION_OR_PARTIAL_IMPORT_REQUIRES_MANUAL_REVIEW")

        outcome = ensure_reference_projects_postgres(
            connection,
            tenant_id=args.tenant,
            member_user_ids=(),
            bundle=build_dam_reference_bundle(),
            initialize_schema=False,
        )
        imported = next((item for item in outcome.projects if item.project_id == PROJECT_ID), None)
        if imported is None:
            raise RuntimeError("DAM_PROJECT_IMPORT_NOT_CONFIRMED")
        # Canonical importer commits only after schedule snapshot and engine
        # success; verify the project is registered and its run is successful.
        manifest = next((item for item in outcome.manifests if item["project_id"] == PROJECT_ID), None)
        if manifest is None or manifest["status"] != "SUCCESS":
            raise RuntimeError("DAM_PROJECT_IMPORT_MANIFEST_NOT_SUCCESSFUL")
        print(json.dumps({
            "project_id": imported.project_id,
            "project_revision": imported.project_revision,
            "snapshot_id": imported.snapshot.snapshot_id,
            "schedule_status": imported.manifest.status,
            "counts": dict(imported.counts),
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
