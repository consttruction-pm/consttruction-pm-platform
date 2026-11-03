"""Import -> persist -> schedule -> export across real modules.

The round-trip verifier proves each codec preserves typed canonical values in
isolation. This test proves the same document can cross the persistence and
scheduling boundaries without losing identity or dates: an XLSX document is
imported, stored through the SQLite activity repository, scheduled by the
shared core, and exported again.
"""
from datetime import date
from decimal import Decimal
import sqlite3

from construction_pm.activity_master_repository import (
    ActivityMaster,
    SQLiteActivityMasterRepository,
)
from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_interchange_adapter import P6InterchangeAdapter
from construction_pm.p6_interchange_mapping import P6InterchangeMapper
from construction_pm.p6_mapping_registry import (
    P6MappingDefinition,
    P6MappingFormat,
    P6MappingStatus,
    PersistedP6Mapping,
)
from construction_pm.p6_xlsx_codec import P6XlsxCodec
from construction_pm.scheduling.activity import Activity
from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.schedule import schedule
from construction_pm.scheduling.time_duration import DurationUnit


_SCOPE = BackendScope("T-1", "P-1", 4)
_SHEET = {"p6.xlsx.sheet": "Activities"}


def _adapter(source_fields: tuple[tuple[str, str, str | None], ...]) -> P6InterchangeAdapter:
    mappings = tuple(
        PersistedP6Mapping(
            scope=_SCOPE,
            definition=P6MappingDefinition(
                mapping_id=f"integration.{index}",
                registry_version="p6-field-registry.v1",
                format=P6MappingFormat.XLSX,
                subject_area="Activity",
                source_field=source,
                canonical_field=canonical,
                status=P6MappingStatus.SUPPORTED,
                canonical_type=canonical_type,
            ),
        )
        for index, (source, canonical, canonical_type) in enumerate(source_fields)
    )
    return P6InterchangeAdapter(
        mapper=P6InterchangeMapper(mappings),
        codec=P6XlsxCodec(),
    )


def test_import_persist_schedule_and_export_preserves_activity_dates():
    resolver = WorkingTimeResolver(WorkingCalendar())
    imported_adapter = _adapter(
        (
            ("Activity ID", "activity.activity_id", "string"),
            ("Start Date", "activity.planned_start", "date"),
            ("Finish Date", "activity.planned_finish", "date"),
        )
    )

    # A source document is written by the same codec, imported back, and then
    # carried into persistence. Dates stay typed through both directions.
    document = imported_adapter.export_document(
        (
            {
                "activity.activity_id": "A-1",
                "activity.planned_start": date(2026, 11, 2),
                "activity.planned_finish": date(2026, 11, 3),
            },
        ),
        scope=_SCOPE,
        extensions=(_SHEET,),
    )
    (imported,) = imported_adapter.import_document(document, scope=_SCOPE)
    assert imported.values == {
        "activity.activity_id": "A-1",
        "activity.planned_start": date(2026, 11, 2),
        "activity.planned_finish": date(2026, 11, 3),
    }
    assert imported.extensions == _SHEET

    duration = resolver.calculate_duration(
        imported.values["activity.planned_start"],
        imported.values["activity.planned_finish"],
    )
    assert duration == 2

    connection = sqlite3.connect(":memory:")
    try:
        repository = SQLiteActivityMasterRepository(connection)
        stored = repository.save(
            ActivityMaster(
                _SCOPE,
                imported.values["activity.activity_id"],
                Decimal(duration),
                DurationUnit.WORKING_DAY,
                remaining_duration=duration,
                planned_finish=imported.values["activity.planned_finish"],
            )
        )
        assert repository.get(_SCOPE, "A-1") == stored

        # The persisted duration drives the shared scheduling core, not a
        # caller-side date copy.
        scheduled = schedule(
            (Activity(stored.activity_id, int(stored.duration_value)),),
            (),
            imported.values["activity.planned_start"],
            resolver,
        )
        early = scheduled.activities["A-1"]
        assert (early.start, early.finish) == (
            date(2026, 11, 2),
            date(2026, 11, 3),
        )
    finally:
        connection.close()

    export_adapter = _adapter(
        (
            ("Scheduled Start", "activity.planned_start", "date"),
            ("Scheduled Finish", "activity.planned_finish", "date"),
        )
    )
    exported_document = export_adapter.export_document(
        (
            {
                "activity.planned_start": early.start,
                "activity.planned_finish": early.finish,
            },
        ),
        scope=_SCOPE,
        extensions=(_SHEET,),
    )
    (exported,) = export_adapter.import_document(exported_document, scope=_SCOPE)
    assert exported.values == {
        "activity.planned_start": date(2026, 11, 2),
        "activity.planned_finish": date(2026, 11, 3),
    }
