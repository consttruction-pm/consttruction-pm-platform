"""Operator-only bootstrap for the first active P6 Admin Superuser.

Run with a database role permitted to provision the P6 security schema and
assignments. This command is intentionally not wired into the web runtime.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from getpass import getpass


def main() -> int:
    dsn = os.environ.get("CONSTRUCTION_PM_DATABASE_URL", "").strip()
    configured_token = os.environ.get("CUBI_P6_BOOTSTRAP_TOKEN", "")
    tenant_id = os.environ.get("CUBI_P6_BOOTSTRAP_TENANT_ID", "").strip()
    user_id = os.environ.get("CUBI_P6_BOOTSTRAP_USER_ID", "").strip()
    if not all((dsn, configured_token, tenant_id, user_id)):
        print(
            "Set CONSTRUCTION_PM_DATABASE_URL, CUBI_P6_BOOTSTRAP_TOKEN, "
            "CUBI_P6_BOOTSTRAP_TENANT_ID and CUBI_P6_BOOTSTRAP_USER_ID.",
            file=sys.stderr,
        )
        return 2

    supplied_token = getpass("One-time CUBI P6 bootstrap token: ")
    try:
        import psycopg

        from .security_profiles import bootstrap_first_admin_superuser

        with psycopg.connect(dsn) as connection:
            profile = bootstrap_first_admin_superuser(
                connection,
                tenant_id=tenant_id,
                user_id=user_id,
                supplied_token=supplied_token,
                configured_token=configured_token,
                occurred_at=datetime.now(timezone.utc),
            )
        print(
            f"Provisioned {profile.name} for user {user_id} in tenant {tenant_id}."
        )
        return 0
    except Exception as exc:  # noqa: BLE001 - CLI boundary, no secret output
        print(f"P6 Admin Superuser bootstrap failed: {type(exc).__name__}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
