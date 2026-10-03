from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_interchange_mapping import P6InterchangeMapper, P6InterchangeRow
from construction_pm.p6_mapping_registry import (
    P6MappingDefinition,
    P6MappingFormat,
    P6MappingStatus,
    PersistedP6Mapping,
    PostgresP6MappingRegistryRepository,
)

pytestmark = pytest.mark.skipif(
    not os.getenv("CONSTRUCTION_PM_POSTGRES_DSN"),
    reason="CONSTRUCTION_PM_POSTGRES_DSN is not configured",
)

ARTIFACT = Path(
    "docs/architecture/P6_ACTIVITY_REGISTRY_ALIAS_RESOLUTION_20261003.json"
)


def connect():
    import psycopg

    return psycopg.connect(os.environ["CONSTRUCTION_PM_POSTGRES_DSN"])


def test_postgres_activity_alias_mappings_round_trip_from_persisted_registry():
    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    scope = BackendScope("tenant-activity-alias-pg", "project-activity-alias-pg", 1)

    with connect() as conn:
        repo = PostgresP6MappingRegistryRepository(conn)
        repo.initialize()

        records = tuple(
            PersistedP6Mapping(
                scope=scope,
                definition=P6MappingDefinition(
                    mapping_id=f"activity-alias-pg:{entry['registry_name']}",
                    registry_version="p6-field-registry.v1",
                    format=P6MappingFormat.XER_PROJECT,
                    subject_area="Activity",
                    source_field=entry["canonical_p6_field"],
                    canonical_field=entry["registry_name"],
                    status=P6MappingStatus.SUPPORTED,
                    notes="Release 26 alias identity evidence; certification remains separate.",
                ),
            )
            for entry in artifact["resolved_aliases"]
        )

        for record in records:
            assert repo.upsert_mapping(record) == record

        loaded = repo.list_mappings(
            scope,
            P6MappingFormat.XER_PROJECT,
            "Activity",
        )
        assert loaded == records
        assert {
            item.definition.canonical_field for item in loaded
        } == set(artifact["summary"]["resolved_names"])

        mapper = P6InterchangeMapper(loaded)
        source_values = {
            entry["canonical_p6_field"]: f"value-{entry['registry_name']}"
            for entry in artifact["resolved_aliases"]
        }
        imported = mapper.import_row(
            P6InterchangeRow(
                scope=scope,
                format=P6MappingFormat.XER_PROJECT,
                values=source_values,
            )
        )
        assert imported.values == {
            entry["registry_name"]: source_values[entry["canonical_p6_field"]]
            for entry in artifact["resolved_aliases"]
        }

        exported = mapper.export_row(
            P6InterchangeRow(
                scope=scope,
                format=P6MappingFormat.XER_PROJECT,
                values=imported.values,
            )
        )
        assert exported.values == source_values
        assert not exported.extensions
