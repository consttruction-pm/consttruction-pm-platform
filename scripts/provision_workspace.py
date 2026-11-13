#!/usr/bin/env python3
"""Provision a real CUBI tenant, user and project in PostgreSQL.

This is the only supported way to create the first production account. It
requires the database connection string and reads the password from stdin or
an environment variable; neither value is ever printed, logged or committed.

Examples
--------
    export CONSTRUCTION_PM_DATABASE_URL=postgresql://...
    python scripts/provision_workspace.py init
    python scripts/provision_workspace.py user \
        --tenant acme --email owner@acme.example --roles project_admin \
        --display-name "Owner" --password-stdin
    python scripts/provision_workspace.py project \
        --tenant acme --project-id head-office \
        --name "Head Office" --member owner@acme.example --seed-presentation
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import re
import sys
from datetime import date
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))

from construction_pm.deployment.schema import initialize_production_schema
from construction_pm.identity_session import (
    IdentityUser,
    PostgresIdentityStore,
    hash_password,
    normalize_email,
    password_policy_error,
    validate_role_tokens,
)
from construction_pm.p6_field_registry_repository import (
    PersistedP6Field,
    PostgresP6FieldRegistryRepository,
)
from construction_pm.p6_layout_definition_repository import (
    LayoutColumn,
    PersistedP6Layout,
    PostgresP6LayoutRepository,
)
from construction_pm.preview.fixtures import (
    CURATED_FIELD_IDS,
    LAYOUT_COLUMNS,
    LAYOUT_SCOPE,
    LAYOUT_VIEW,
    REGISTRY_VERSION,
)
from construction_pm.p6_field_registry import get_field
from construction_pm.backend_p0.models import BackendScope

PROJECT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{1,63}$")
TENANT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{1,63}$")


def _dsn(args: argparse.Namespace) -> str:
    dsn = (args.dsn or os.environ.get("CONSTRUCTION_PM_DATABASE_URL", "")).strip()
    if not dsn.startswith(("postgresql://", "postgres://")):
        raise SystemExit("CONSTRUCTION_PM_DATABASE_URL must be a PostgreSQL URL")
    return dsn


def _connect(args: argparse.Namespace):
    import psycopg

    return psycopg.connect(_dsn(args), autocommit=False, connect_timeout=15)


def _password(args: argparse.Namespace) -> str:
    if args.password_stdin:
        value = sys.stdin.readline().rstrip("\n")
    else:
        value = os.environ.get("CUBI_PROVISION_PASSWORD", "")
        if not value:
            if not sys.stdin.isatty():
                raise SystemExit(
                    "Provide --password-stdin or CUBI_PROVISION_PASSWORD"
                )
            value = getpass.getpass("Password: ")
            confirm = getpass.getpass("Repeat password: ")
            if value != confirm:
                raise SystemExit("Passwords do not match")
    code = password_policy_error(value)
    if code:
        raise SystemExit(f"Password rejected: {code}")
    return value


def command_init(args: argparse.Namespace) -> None:
    with _connect(args) as connection:
        initialize_production_schema(connection)
        connection.commit()
    print("schema ready")


def command_user(args: argparse.Namespace) -> None:
    tenant = args.tenant.strip()
    if not TENANT_ID.match(tenant):
        raise SystemExit("tenant id must match [A-Za-z0-9][A-Za-z0-9._-]{1,63}")
    try:
        email = normalize_email(args.email)
        roles = validate_role_tokens(args.roles.split(","))
    except Exception as error:
        raise SystemExit(str(error)) from None
    password = _password(args)
    user_id = args.user_id.strip() or f"user-{email.split('@')[0][:32]}"
    with _connect(args) as connection:
        initialize_production_schema(connection)
        PostgresIdentityStore(connection).upsert_user(
            IdentityUser(
                user_id=user_id,
                tenant_id=tenant,
                email=email,
                display_name=args.display_name.strip(),
                roles=roles,
                password_hash=hash_password(password),
                active=not args.inactive,
            )
        )
        connection.commit()
    print(json.dumps({
        "user_id": user_id,
        "tenant_id": tenant,
        "email": email,
        "roles": sorted(roles),
        "active": not args.inactive,
    }, sort_keys=True))


def _seed_presentation(connection, scope: BackendScope) -> None:
    fields = PostgresP6FieldRegistryRepository(connection)
    if fields.list_fields(scope, REGISTRY_VERSION):
        return
    for field_id in CURATED_FIELD_IDS:
        fields.upsert_field(PersistedP6Field(scope, REGISTRY_VERSION, get_field(field_id)))
    layouts = PostgresP6LayoutRepository(connection)
    columns = tuple(
        LayoutColumn(
            field_id=column.field_id,
            visible=column.visible,
            order=index,
            label=column.label,
            width=column.width,
            alignment=column.alignment,
            pinned=False,
            frozen=False,
        )
        for index, column in enumerate(LAYOUT_COLUMNS)
    )
    layouts.upsert(
        PersistedP6Layout(
            scope=scope,
            layout_scope=LAYOUT_SCOPE,
            view_id=LAYOUT_VIEW,
            revision=1,
            columns=columns,
            metadata={"source": "cubi-production-provisioning", "layoutName": "Classic Schedule Layout"},
        )
    )


def command_project(args: argparse.Namespace) -> None:
    tenant = args.tenant.strip()
    project_id = args.project_id.strip()
    if not TENANT_ID.match(tenant):
        raise SystemExit("tenant id must match [A-Za-z0-9][A-Za-z0-9._-]{1,63}")
    if not PROJECT_ID.match(project_id):
        raise SystemExit("project id must match [A-Za-z0-9][A-Za-z0-9._-]{1,63}")
    try:
        member = normalize_email(args.member)
    except Exception as error:
        raise SystemExit(str(error)) from None
    if args.start_date:
        try:
            if date.fromisoformat(args.start_date).isoformat() != args.start_date:
                raise ValueError
        except ValueError:
            raise SystemExit("--start-date must be YYYY-MM-DD") from None
    with _connect(args) as connection:
        initialize_production_schema(connection)
        user = connection.execute(
            "SELECT user_id, tenant_id FROM identity_users WHERE lower(email)=%s",
            (member,),
        ).fetchone()
        if user is None or str(user[1]) != tenant:
            raise SystemExit("member must be an existing user in the same tenant")
        connection.execute(
            "INSERT INTO project_lifecycle_projects "
            "(tenant_id, project_id, name, revision, description, start_date, "
            "date_system, primary_calendar_id, settings_revision, status, business_domain) "
            "VALUES (%s, %s, %s, 0, %s, %s, %s, NULL, 0, %s, %s) "
            "ON CONFLICT (tenant_id, project_id) DO NOTHING",
            (
                tenant,
                project_id,
                args.name.strip(),
                args.description.strip(),
                args.start_date,
                args.date_system,
                args.status,
                args.business_domain,
            ),
        )
        connection.execute(
            "INSERT INTO project_lifecycle_memberships (tenant_id, project_id, user_id) "
            "VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
            (tenant, project_id, str(user[0])),
        )
        if args.seed_presentation:
            _seed_presentation(
                connection, BackendScope(tenant, project_id, 0)
            )
        connection.commit()
    print(json.dumps({
        "tenant_id": tenant,
        "project_id": project_id,
        "member": member,
        "seeded_presentation": bool(args.seed_presentation),
    }, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dsn", default="", help="PostgreSQL URL (prefer the environment variable)")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="create the production schema")
    init.set_defaults(handler=command_init)

    user = sub.add_parser("user", help="create or update a real user")
    user.add_argument("--tenant", required=True)
    user.add_argument("--email", required=True)
    user.add_argument("--roles", default="project_admin")
    user.add_argument("--user-id", default="")
    user.add_argument("--display-name", default="")
    user.add_argument("--password-stdin", action="store_true")
    user.add_argument("--inactive", action="store_true")
    user.set_defaults(handler=command_user)

    project = sub.add_parser("project", help="create a project and membership")
    project.add_argument("--tenant", required=True)
    project.add_argument("--project-id", required=True)
    project.add_argument("--name", required=True)
    project.add_argument("--member", required=True)
    project.add_argument("--description", default="")
    project.add_argument("--start-date", default=None)
    project.add_argument("--date-system", default="gregorian", choices=("gregorian", "jalali"))
    project.add_argument("--status", default="active", choices=("active", "inactive", "planned", "what_if"))
    project.add_argument("--business-domain", default="", choices=("", "construction", "oil_gas", "infrastructure", "industrial", "energy", "other"))
    project.add_argument("--seed-presentation", action="store_true")
    project.set_defaults(handler=command_project)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.handler(args)


if __name__ == "__main__":
    main()
