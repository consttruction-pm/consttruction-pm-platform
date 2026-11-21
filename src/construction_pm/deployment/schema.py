"""Idempotent PostgreSQL schema bootstrap for the production runtime.

The bootstrap is a versioned migration registry: every step is additive
(``CREATE ... IF NOT EXISTS`` and additive ``ALTER``), the applied versions are
recorded in ``cubi_schema_migration`` and a structural fingerprint detects a
database that no longer matches the code. It never drops, truncates or rewrites
a row, so provisioning an existing database is safe.

See :mod:`construction_pm.deployment.migrations` for the registry, the ledger
contract and the drift policy.
"""

from __future__ import annotations

from typing import Any

from .migrations import (
    MigrationReport,
    apply_migrations,
    current_state,
    schema_fingerprint,
)

__all__ = [
    "MigrationReport",
    "current_state",
    "initialize_production_schema",
    "schema_fingerprint",
]


def initialize_production_schema(connection: Any) -> MigrationReport:
    """Apply every pending migration and return what happened.

    The caller owns the surrounding transaction and must commit after a
    successful run; a failed step leaves the bootstrap unapplied.
    """

    return apply_migrations(connection)
