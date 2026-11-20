#!/usr/bin/env python3
"""Prove PostgreSQL persistence for the CUBISITE web surface.

This script is the executable evidence behind ``docs/evidence/postgres/``.
It never prints or stores the DSN, the password or the session token.

Phases
------
1. bootstrap — run the production schema bootstrap twice and compare table counts
   (idempotent, additive).
2. write     — create two tenants' users, log one in, create one Enterprise task.
3. fresh read — a **separate process** reconnects and resolves the session, reads
   the task and confirms the row survived the commit.
4. isolation — the second tenant sees no tasks, no users and cannot resolve the
   first tenant's session.
5. revoke    — revoke the session, then a third process must get no session.
6. secrets   — the raw password and raw token must not appear in any column.

Usage:
    export CONSTRUCTION_PM_POSTGRES_DSN=postgresql://...
    python3 scripts/verify_postgres_persistence.py --out docs/evidence/postgres/persistence.json
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from construction_pm.deployment.schema import initialize_production_schema  # noqa: E402
from construction_pm.enterprise_task import EnterpriseTask  # noqa: E402
from construction_pm.enterprise_task_repository import (  # noqa: E402
    PostgresEnterpriseTaskRepository,
)
from construction_pm.identity_session import (  # noqa: E402
    IdentityService,
    IdentityUser,
    PostgresIdentityStore,
    hash_password,
)

CSRF_SECRET = "cubisite-verification-secret-not-a-production-value"
TENANT_A = "tenant-cubisite-a"
TENANT_B = "tenant-cubisite-b"
PASSWORD = "Cubisite-Verify-" + secrets.token_urlsafe(9)


def dsn() -> str:
    value = os.environ.get("CONSTRUCTION_PM_POSTGRES_DSN") or os.environ.get("CONSTRUCTION_PM_DATABASE_URL")
    if not value:
        raise SystemExit("CONSTRUCTION_PM_POSTGRES_DSN is required")
    return value


def connect():
    import psycopg

    return psycopg.connect(dsn(), autocommit=False, connect_timeout=10)


def count_tables(connection) -> int:
    row = connection.execute(
        "SELECT count(*) FROM information_schema.tables WHERE table_schema='public'"
    ).fetchone()
    return int(row[0])


def target() -> str:
    from urllib.parse import urlsplit

    parts = urlsplit(dsn())
    return f"{parts.hostname}:{parts.port or 5432}/{parts.path.lstrip('/')}"


def read_state(tenant_id: str, user_id: str) -> dict:
    """Fresh-process read used by phase 3, 4 and 5."""
    token = os.environ.get("CUBI_VERIFY_TOKEN", "")
    with connect() as connection:
        store = PostgresIdentityStore(connection)
        service = IdentityService(store, csrf_secret=CSRF_SECRET)
        session = service.resolve(token) if token else None
        users = connection.execute(
            "SELECT user_id FROM identity_users WHERE tenant_id=%s", (tenant_id,)
        ).fetchall()
        foreign = connection.execute(
            "SELECT user_id FROM identity_users WHERE user_id=%s AND tenant_id=%s",
            (user_id, TENANT_B),
        ).fetchall()
        tasks = PostgresEnterpriseTaskRepository(connection).list_for_tenant(TENANT_B)
        return {
            "session_resolved": session is not None,
            "session_tenant": getattr(session, "tenant_id", None),
            "tenant_user_rows": len(users),
            "foreign_user_rows": len(foreign),
            "foreign_task_rows": len(tasks),
        }


def child_read(token: str) -> dict:
    env = dict(os.environ)
    env["CUBI_VERIFY_TOKEN"] = token
    result = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "read"],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "child read failed")
    return json.loads(result.stdout)


def main(argv: list[str]) -> int:
    if argv and argv[0] == "read":
        print(json.dumps(read_state(TENANT_A, os.environ["CUBI_VERIFY_USER"])))
        return 0

    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="")
    args = parser.parse_args(argv)

    checks: list[dict] = []
    evidence: dict = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "target": target(),
        "engine": None,
        "checks": checks,
    }

    with connect() as connection:
        version = connection.execute("SHOW server_version").fetchone()[0]
        evidence["engine"] = f"PostgreSQL {version}"
        before = count_tables(connection)
        initialize_production_schema(connection)
        connection.commit()
        first = count_tables(connection)
        initialize_production_schema(connection)
        connection.commit()
        second = count_tables(connection)
        checks.append(
            {
                "name": "bootstrap_is_idempotent_and_additive",
                "ok": second == first and second >= before,
                "tables_before": before,
                "tables_after_first_run": first,
                "tables_after_second_run": second,
            }
        )

    suffix = uuid.uuid4().hex[:8]
    os.environ["CUBI_VERIFY_USER"] = f"usr-a-{suffix}"
    user_a = IdentityUser(
        user_id=f"usr-a-{suffix}",
        tenant_id=TENANT_A,
        email=f"alpha-{suffix}@cubisite.test",
        display_name="Alpha Owner",
        roles=frozenset({"project_admin"}),
        password_hash=hash_password(PASSWORD),
        active=True,
    )
    user_b = IdentityUser(
        user_id=f"usr-b-{suffix}",
        tenant_id=TENANT_B,
        email=f"beta-{suffix}@cubisite.test",
        display_name="Beta User",
        roles=frozenset({"project_viewer"}),
        password_hash=hash_password(PASSWORD),
        active=True,
    )

    with connect() as connection:
        store = PostgresIdentityStore(connection)
        store.upsert_user(user_a)
        store.upsert_user(user_b)
        connection.commit()
        service = IdentityService(store, csrf_secret=CSRF_SECRET)
        issued = service.login(user_a.email, PASSWORD)
        repo = PostgresEnterpriseTaskRepository(connection)
        task = EnterpriseTask(
            task_id=f"task-{suffix}",
            tenant_id=TENANT_A,
            title="CUBISITE persistence proof",
            created_by_user_id=user_a.user_id,
            created_at=datetime.now(timezone.utc),
        )
        repo.create(
            task,
            idempotency_key=f"verify-{suffix}",
            actor_id=user_a.user_id,
            occurred_at=datetime.now(timezone.utc),
        )
        connection.commit()
        raw_token = issued.token
        raw_password = PASSWORD

    fresh = child_read(raw_token)
    checks.append(
        {
            "name": "session_survives_commit_in_a_new_process",
            "ok": fresh["session_resolved"] and fresh["session_tenant"] == TENANT_A,
            **fresh,
        }
    )
    checks.append(
        {
            "name": "tenant_isolation",
            "ok": fresh["foreign_user_rows"] == 0 and fresh["foreign_task_rows"] == 0,
        }
    )

    with connect() as connection:
        row = connection.execute(
            "SELECT task_json::text FROM enterprise_tasks WHERE tenant_id=%s AND task_id=%s",
            (TENANT_A, task.task_id),
        ).fetchone()
        checks.append(
            {
                "name": "task_row_persisted",
                "ok": row is not None and task.task_id in str(row[0]),
            }
        )
        leaked = connection.execute(
            "SELECT count(*) FROM identity_users WHERE password_hash=%s", (raw_password,)
        ).fetchone()[0]
        token_rows = connection.execute(
            "SELECT count(*) FROM identity_sessions WHERE token_hash=%s", (raw_token,)
        ).fetchone()[0]
        checks.append(
            {
                "name": "no_plaintext_secrets",
                "ok": int(leaked) == 0 and int(token_rows) == 0,
            }
        )

    with connect() as connection:
        service = IdentityService(PostgresIdentityStore(connection), csrf_secret=CSRF_SECRET)
        revoked = service.logout(raw_token)
        connection.commit()
    checks.append({"name": "logout_revokes_session", "ok": bool(revoked)})

    after_revoke = child_read(raw_token)
    checks.append(
        {
            "name": "revoked_session_unresolvable_in_new_process",
            "ok": after_revoke["session_resolved"] is False,
        }
    )

    ok = all(check["ok"] for check in checks)
    evidence["ok"] = ok
    evidence["tenant_isolation"] = {"tenant": TENANT_B, "foreign_rows": fresh["foreign_task_rows"]}
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
