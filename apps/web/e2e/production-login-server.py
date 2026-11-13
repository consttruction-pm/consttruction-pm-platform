#!/usr/bin/env python3
"""Serve the exact production WSGI stack for local browser verification.

This is not a preview/demo server. It composes ``ProductionRuntime`` (the same
callable ``api/index.py`` exports on Vercel) against PostgreSQL, seeds one real
identity + project + curated presentation, and prints the bound port.

Environment:
    CONSTRUCTION_PM_POSTGRES_DSN   required
    CUBI_E2E_ORIGIN              default http://127.0.0.1:<port>
    CUBI_E2E_EMAIL               default e2e-owner@example.test
    CUBI_E2E_PASSWORD            default "correct horse battery staple"
    CUBI_E2E_TENANT              default cubi-e2e-tenant
    CUBI_E2E_PROJECT             default cubi-e2e-project
    CUBI_E2E_PORT                default 0 (ephemeral)
    CUBI_WEB_ROOT                default <repo>/public
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO))

from wsgiref.simple_server import WSGIRequestHandler, make_server  # noqa: E402

from construction_pm.backend_p0.models import BackendScope  # noqa: E402
from construction_pm.deployment.production_runtime import (  # noqa: E402
    ProductionRuntime,
    ProductionSettings,
)
from construction_pm.identity_session import (  # noqa: E402
    IdentityUser,
    PostgresIdentityStore,
    hash_password,
)
from scripts.provision_workspace import _seed_presentation  # noqa: E402

EMAIL = os.environ.get("CUBI_E2E_EMAIL", "e2e-owner@example.test")
PASSWORD = os.environ.get("CUBI_E2E_PASSWORD", "correct horse battery staple")
TENANT = os.environ.get("CUBI_E2E_TENANT", "cubi-e2e-tenant")
PROJECT = os.environ.get("CUBI_E2E_PROJECT", "cubi-e2e-project")
USER_ID = "e2e-owner"
SECRET = "cubi-local-e2e-session-secret-0123456789"


class QuietHandler(WSGIRequestHandler):
    def log_message(self, *args: object) -> None:  # noqa: D102
        pass


def seed(runtime: ProductionRuntime) -> None:
    connection = runtime.pool.acquire()
    try:
        PostgresIdentityStore(connection).upsert_user(
            IdentityUser(
                user_id=USER_ID,
                tenant_id=TENANT,
                email=EMAIL,
                display_name="E2E Owner",
                roles=frozenset({"project_admin"}),
                password_hash=hash_password(PASSWORD),
            )
        )
        connection.execute(
            "INSERT INTO project_lifecycle_projects "
            "(tenant_id, project_id, name) VALUES (%s, %s, %s) "
            "ON CONFLICT (tenant_id, project_id) DO NOTHING",
            (TENANT, PROJECT, "E2E Authorized Project"),
        )
        connection.execute(
            "INSERT INTO project_lifecycle_memberships "
            "(tenant_id, project_id, user_id) VALUES (%s, %s, %s) "
            "ON CONFLICT DO NOTHING",
            (TENANT, PROJECT, USER_ID),
        )
        _seed_presentation(connection, BackendScope(TENANT, PROJECT, 0))
        connection.commit()
    finally:
        runtime.pool.release(connection, healthy=True)


def main() -> None:
    dsn = os.environ["CONSTRUCTION_PM_POSTGRES_DSN"]
    port = int(os.environ.get("CUBI_E2E_PORT", "0") or 0)
    origin = os.environ.get("CUBI_E2E_ORIGIN", "").rstrip("/")
    if port == 0 and not origin:
        raise SystemExit("CUBI_E2E_ORIGIN is required with an ephemeral port")
    settings = ProductionSettings(
        database_url=dsn,
        session_secret=SECRET,
        public_origin=origin or "http://127.0.0.1:4180",
        secure_cookies=False,
        static_root=Path(os.environ.get("CUBI_WEB_ROOT", str(REPO / "public"))),
        max_pool_size=2,
    )
    runtime = ProductionRuntime(settings)
    runtime._initialize()
    seed(runtime)

    server = make_server("127.0.0.1", port, runtime, handler_class=QuietHandler)
    bound = server.server_address[1]
    print(f"CUBI_E2E_READY {bound}", flush=True)
    try:
        server.serve_forever()
    finally:
        runtime.close()


if __name__ == "__main__":
    main()
