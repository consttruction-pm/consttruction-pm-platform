#!/usr/bin/env python3
"""Register the three frozen CUBI reference projects in the production database.

The three projects (CUBI-REF-001/002/003) are the shared, durable tenant data
the product pages read. This command applies the additive schema migrations and
runs the idempotent importer that writes every project, WBS element, activity,
relationship, baseline, resource assignment, progress/EVM input and Enterprise
register through the PostgreSQL repositories. Re-running it is a no-op.

It never imports calculated values: CPM dates, float, critical path and EVM are
produced by the canonical schedule engine and read model during the import.

Examples
--------
    export CONSTRUCTION_PM_DATABASE_URL=postgresql://...
    python scripts/import_reference_projects.py --tenant acme
    python scripts/import_reference_projects.py --tenant acme --json
    python scripts/import_reference_projects.py --tenant acme --list

The command prints only structural counts and identifiers; it never writes the
connection string or any credential to stdout.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))

from construction_pm.deployment.schema import initialize_production_schema
from construction_pm.importing.reference_postgres import (
    ensure_reference_projects_postgres,
    read_import_manifests,
)


def _dsn(args: argparse.Namespace) -> str:
    dsn = (
        args.dsn
        or os.environ.get("CONSTRUCTION_PM_DATABASE_URL")
        or os.environ.get("POSTGRES_URL_NON_POOLING")
        or ""
    ).strip()
    if not dsn.startswith(("postgresql://", "postgres://")):
        raise SystemExit("CONSTRUCTION_PM_DATABASE_URL must be a PostgreSQL URL")
    return dsn


def _connect(args: argparse.Namespace, *, autocommit: bool):
    import psycopg

    return psycopg.connect(_dsn(args), autocommit=autocommit, connect_timeout=15)


def _project_payload(project) -> dict[str, object]:
    return {
        "project_id": project.project_id,
        "revision": project.project_revision,
        "records": sum(project.counts.values()),
        "snapshot_id": project.snapshot.snapshot_id,
    }


def _enterprise_payload(result) -> dict[str, object]:
    payload: dict[str, object] = {"project_id": result.project_id}
    for name in ("status", "created", "present", "missing", "unsupported"):
        value = getattr(result, name, None)
        if value is not None:
            payload[name] = value
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tenant", required=True, help="tenant id that owns the projects")
    parser.add_argument("--dsn", default=None, help="PostgreSQL DSN (default: env)")
    parser.add_argument("--json", action="store_true", help="print a JSON summary")
    parser.add_argument(
        "--list",
        action="store_true",
        help="only list the existing durable import manifests",
    )
    parser.add_argument(
        "--no-migrate",
        action="store_true",
        help="skip applying pending schema migrations first",
    )
    args = parser.parse_args(argv)

    if args.list:
        connection = _connect(args, autocommit=True)
        try:
            manifests = read_import_manifests(connection, args.tenant)
        finally:
            connection.close()
        if args.json:
            print(json.dumps(manifests, indent=2, default=str))
        else:
            for manifest in manifests:
                print(
                    f"{manifest['project_id']} status={manifest['status']} "
                    f"source_sha256={manifest['source_sha256'][:12]} "
                    f"imported_at={manifest['imported_at']}"
                )
        return 0

    connection = _connect(args, autocommit=False)
    try:
        migration = None
        if not args.no_migrate:
            migration = initialize_production_schema(connection)
            connection.commit()
        outcome = ensure_reference_projects_postgres(
            connection, tenant_id=args.tenant
        )
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    summary = {
        "tenant_id": args.tenant,
        "migration_applied": [] if migration is None else [
            step.get("version") for step in migration.applied
        ],
        "migration_schema_hash": None if migration is None else migration.schema_hash,
        "migration_drift": None if migration is None else migration.drift,
        "projects": [_project_payload(p) for p in outcome.projects],
        "enterprise": [_enterprise_payload(e) for e in outcome.enterprise],
        "manifests": [
            {
                "project_id": m["project_id"],
                "status": m["status"],
                "source_sha256": m["source_sha256"],
                "imported_at": str(m["imported_at"]),
                "counts": m["counts"],
            }
            for m in outcome.manifests
        ],
    }
    if args.json:
        print(json.dumps(summary, indent=2, default=str))
    else:
        print(f"tenant: {args.tenant}")
        for project in summary["projects"]:
            print(
                f"  project {project['project_id']} revision={project['revision']} "
                f"records={project['records']}"
            )
        for enterprise in summary["enterprise"]:
            print(
                f"  enterprise {enterprise['project_id']} "
                f"status={enterprise.get('status')} "
                f"missing={enterprise.get('missing')} "
                f"unsupported={list(enterprise.get('unsupported') or ())}"
            )
        for manifest in summary["manifests"]:
            total = sum(
                value
                for value in manifest["counts"].values()
                if isinstance(value, int)
            )
            print(
                f"  manifest {manifest['project_id']} {manifest['status']} "
                f"records={total}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
