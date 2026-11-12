from __future__ import annotations

from decimal import Decimal

import pytest

from construction_pm.knowledge.plan import (
    MasterDataPlanPort,
    PlanContext,
    ProjectPlanError,
    RealScheduleSettingsWriter,
    UnavailableProjectPlanPort,
)


class FakeWBSAPI:
    def __init__(self) -> None:
        self.rows: dict[str, dict[str, object]] = {}

    def get(self, scope, wbs_id, *, auth_context=None):
        row = self.rows.get(wbs_id)
        return None if row is None else {"wbs": dict(row)}

    def create(self, master, *, auth_context=None):
        self.rows[master.wbs_id] = {
            "wbs_id": master.wbs_id,
            "code": master.code,
            "name": master.name,
            "parent_wbs_id": master.parent_wbs_id,
            "record_revision": 0,
        }

    def update(self, master, *, expected_revision, auth_context=None):
        row = self.rows[master.wbs_id]
        assert int(expected_revision) == int(row["record_revision"])
        row.update(
            code=master.code,
            name=master.name,
            parent_wbs_id=master.parent_wbs_id,
            record_revision=int(expected_revision) + 1,
        )

    def list(self, scope, *, auth_context=None):
        return [{"wbs": dict(row)} for row in self.rows.values()]


class FakeActivityAPI:
    def __init__(self) -> None:
        self.rows: dict[str, dict[str, object]] = {}

    def create(self, master, *, auth_context=None):
        self.rows[master.activity_id] = {
            "activity_id": master.activity_id,
            "name": master.name,
            "wbs_id": master.wbs_id,
            "duration_value": master.duration_value,
            "record_revision": 0,
        }

    def update(self, master, *, expected_revision, auth_context=None):
        row = self.rows[master.activity_id]
        assert int(expected_revision) == int(row["record_revision"])
        row.update(
            name=master.name,
            wbs_id=master.wbs_id,
            duration_value=master.duration_value,
            record_revision=int(expected_revision) + 1,
        )

    def list(self, scope, *, auth_context=None):
        return [{"activity": dict(row)} for row in self.rows.values()]


class FakeRelationshipAPI:
    def __init__(self) -> None:
        self.rows: dict[str, dict[str, object]] = {}

    def create(self, master, *, auth_context=None, expected_revision=0):
        self.rows[master.relationship_id] = {
            "relationship_id": master.relationship_id,
            "predecessor_id": master.predecessor_id,
            "successor_id": master.successor_id,
            "relationship_type": master.relationship_type.value,
            "lag_value": master.lag_value,
            "lag_unit": master.lag_unit.value,
            "record_revision": 0,
        }

    def list(self, scope, *, auth_context=None):
        return [{"relationship": dict(row)} for row in self.rows.values()]


class FakeSettingsPort:
    def __init__(self) -> None:
        self.applied: list[dict[str, object]] = []

    def apply(self, context, *, data_date, calendar):
        self.applied.append({"data_date": data_date, "calendar": dict(calendar)})
        return {"data_date": data_date, "calendar_id": calendar["calendar_id"]}

    def verify(self, context, *, data_date, calendar):
        return {"verified": bool(self.applied) and self.applied[-1]["data_date"] == data_date}


@pytest.fixture()
def context() -> PlanContext:
    return PlanContext(
        tenant_id="tenant-1",
        project_id="PRJ-1",
        project_revision=1,
        user_id="planner-1",
        roles=frozenset({"planner"}),
    )


@pytest.fixture()
def apis():
    return FakeWBSAPI(), FakeActivityAPI(), FakeRelationshipAPI(), FakeSettingsPort()


def _nodes():
    return [
        {"wbs_id": "W1", "code": "1", "name": "Root"},
        {"wbs_id": "W2", "code": "1.1", "name": "Child", "parent_wbs_id": "W1"},
    ]


def _activities():
    return [
        {"activity_id": "A1", "name": "Design", "wbs_id": "W1", "duration_days": 5},
        {"activity_id": "A2", "name": "Review", "wbs_id": "W2", "duration_days": 2},
    ]


def test_wbs_apply_is_idempotent_and_updates_changes(apis, context) -> None:
    wbs, activities, relationships, settings = apis
    port = MasterDataPlanPort(wbs, activities, relationships, settings)

    first = port.apply_wbs(context, _nodes(), idempotency_key="run-1")
    assert (first["created"], first["updated"], first["unchanged"]) == (2, 0, 0)

    second = port.apply_wbs(context, _nodes(), idempotency_key="run-1")
    assert (second["created"], second["updated"], second["unchanged"]) == (0, 0, 2)

    changed = _nodes()
    changed[1]["name"] = "Child renamed"
    third = port.apply_wbs(context, changed, idempotency_key="run-1")
    assert (third["created"], third["updated"], third["unchanged"]) == (0, 1, 1)
    assert wbs.rows["W2"]["record_revision"] == 1


def test_wbs_rejects_unknown_parent_duplicates_and_invalid_fields(apis, context) -> None:
    wbs, activities, relationships, settings = apis
    port = MasterDataPlanPort(wbs, activities, relationships, settings)

    with pytest.raises(ProjectPlanError, match="WBS_PARENT_UNKNOWN"):
        port.apply_wbs(
            context,
            [{"wbs_id": "W2", "code": "1.1", "name": "Child", "parent_wbs_id": "W9"}],
            idempotency_key="run-1",
        )

    with pytest.raises(ProjectPlanError, match="WBS_ID_DUPLICATE"):
        port.apply_wbs(
            context,
            [
                {"wbs_id": "W1", "code": "1", "name": "Root"},
                {"wbs_id": "W1", "code": "2", "name": "Again"},
            ],
            idempotency_key="run-1",
        )

    with pytest.raises(ProjectPlanError, match="WBS_NAME_INVALID"):
        port.apply_wbs(
            context, [{"wbs_id": "W1", "code": "1", "name": "   "}], idempotency_key="run-1"
        )


def test_activities_require_existing_wbs(apis, context) -> None:
    wbs, activities, relationships, settings = apis
    port = MasterDataPlanPort(wbs, activities, relationships, settings)
    port.apply_wbs(context, _nodes(), idempotency_key="run-1")

    with pytest.raises(ProjectPlanError, match="ACTIVITY_WBS_UNKNOWN"):
        port.apply_activities(
            context,
            [{"activity_id": "A9", "name": "Ghost", "wbs_id": "W9", "duration_days": 1}],
            idempotency_key="run-1",
        )

    with pytest.raises(ProjectPlanError, match="MILESTONE_DURATION_INVALID"):
        port.apply_activities(
            context,
            [
                {
                    "activity_id": "A9",
                    "name": "Milestone",
                    "wbs_id": "W1",
                    "milestone": True,
                    "duration_days": 2,
                }
            ],
            idempotency_key="run-1",
        )

    with pytest.raises(ProjectPlanError, match="ACTIVITY_DURATION_INVALID"):
        port.apply_activities(
            context,
            [{"activity_id": "A9", "name": "No duration", "wbs_id": "W1"}],
            idempotency_key="run-1",
        )


def test_activities_apply_is_idempotent(apis, context) -> None:
    wbs, activities, relationships, settings = apis
    port = MasterDataPlanPort(wbs, activities, relationships, settings)
    port.apply_wbs(context, _nodes(), idempotency_key="run-1")

    first = port.apply_activities(context, _activities(), idempotency_key="run-1")
    assert (first["created"], first["updated"], first["unchanged"]) == (2, 0, 0)
    second = port.apply_activities(context, _activities(), idempotency_key="run-1")
    assert (second["created"], second["updated"], second["unchanged"]) == (0, 0, 2)

    changed = _activities()
    changed[0]["duration_days"] = 8
    third = port.apply_activities(context, changed, idempotency_key="run-1")
    assert (third["created"], third["updated"], third["unchanged"]) == (0, 1, 1)


def test_schedule_requires_settings_port(apis, context) -> None:
    wbs, activities, relationships, settings = apis
    port = MasterDataPlanPort(wbs, activities, relationships)
    port.apply_wbs(context, _nodes(), idempotency_key="run-1")
    port.apply_activities(context, _activities(), idempotency_key="run-1")

    with pytest.raises(ProjectPlanError, match="SCHEDULE_SETTINGS_UNAVAILABLE"):
        port.apply_schedule(
            context,
            [],
            data_date="2026-03-01",
            calendar={"calendar_id": "CAL-1", "working_weekdays": [0, 1, 2, 3, 4]},
            idempotency_key="run-1",
        )


def test_schedule_validates_relationships_and_is_idempotent(apis, context) -> None:
    wbs, activities, relationships, settings = apis
    port = MasterDataPlanPort(wbs, activities, relationships, settings)
    port.apply_wbs(context, _nodes(), idempotency_key="run-1")
    port.apply_activities(context, _activities(), idempotency_key="run-1")

    with pytest.raises(ProjectPlanError, match="PREDECESSOR_UNKNOWN"):
        port.apply_schedule(
            context,
            [{"predecessor_id": "A9", "successor_id": "A2"}],
            data_date="2026-03-01",
            calendar={"calendar_id": "CAL-1"},
            idempotency_key="run-1",
        )
    with pytest.raises(ProjectPlanError, match="SELF_RELATIONSHIP"):
        port.apply_schedule(
            context,
            [{"predecessor_id": "A1", "successor_id": "A1"}],
            data_date="2026-03-01",
            calendar={"calendar_id": "CAL-1"},
            idempotency_key="run-1",
        )
    with pytest.raises(ProjectPlanError, match="RELATIONSHIP_CYCLE"):
        port.apply_schedule(
            context,
            [
                {"predecessor_id": "A1", "successor_id": "A2"},
                {"predecessor_id": "A2", "successor_id": "A1"},
            ],
            data_date="2026-03-01",
            calendar={"calendar_id": "CAL-1"},
            idempotency_key="run-1",
        )
    with pytest.raises(ProjectPlanError, match="RELATIONSHIP_TYPE_INVALID"):
        port.apply_schedule(
            context,
            [
                {
                    "predecessor_id": "A1",
                    "successor_id": "A2",
                    "relationship_type": "XX",
                }
            ],
            data_date="2026-03-01",
            calendar={"calendar_id": "CAL-1"},
            idempotency_key="run-1",
        )

    edges = [
        {"predecessor_id": "A1", "successor_id": "A2", "relationship_type": "FS", "lag_days": 2}
    ]
    calendar = {"calendar_id": "CAL-1", "working_weekdays": [0, 1, 2, 3, 4]}
    first = port.apply_schedule(
        context, edges, data_date="2026-03-01", calendar=calendar, idempotency_key="run-1"
    )
    assert first["created"] == 1
    assert first["data_date"] == "2026-03-01"
    assert settings.applied[-1]["calendar"]["calendar_id"] == "CAL-1"

    second = port.apply_schedule(
        context, edges, data_date="2026-03-01", calendar=calendar, idempotency_key="run-1"
    )
    assert second["created"] == 0
    assert second["unchanged"] == 1

    relationships.rows["R-A1-A2-FS"]["lag_value"] = Decimal(9)
    with pytest.raises(ProjectPlanError, match="RELATIONSHIP_CONFLICT"):
        port.apply_schedule(
            context, edges, data_date="2026-03-01", calendar=calendar, idempotency_key="run-1"
        )


def test_relationship_types_lag_and_lead_reach_authoritative_records(apis, context) -> None:
    """FS/SS/FF/SF, lag and lead survive the port with working-day units."""

    wbs, activities, relationships, settings = apis
    port = MasterDataPlanPort(wbs, activities, relationships, settings)
    port.apply_wbs(context, _nodes(), idempotency_key="run-1")
    port.apply_activities(context, _activities(), idempotency_key="run-1")

    edges = [
        {"predecessor_id": "A1", "successor_id": "A2", "relationship_type": "FS"},
        {"predecessor_id": "A1", "successor_id": "A2", "relationship_type": "ss", "lag_days": 3},
        {"predecessor_id": "A1", "successor_id": "A2", "relationship_type": "FF", "lag_days": -2},
        {"predecessor_id": "A1", "successor_id": "A2", "relationship_type": "SF", "lag_days": 5},
    ]
    calendar = {
        "calendar_id": "CAL-1",
        "calendar_version": "2",
        "working_weekdays": [6, 0, 1, 2, 3],
    }
    result = port.apply_schedule(
        context, edges, data_date="2026-03-21", calendar=calendar, idempotency_key="run-1"
    )

    assert result["created"] == 4
    assert [row["relationship_type"] for row in result["relationships"]] == [
        "FS",
        "SS",
        "FF",
        "SF",
    ]
    assert [row["lag_days"] for row in result["relationships"]] == [0, 3, -2, 5]

    for relationship_type, lag in (("FS", 0), ("SS", 3), ("FF", -2), ("SF", 5)):
        row = relationships.rows[f"R-A1-A2-{relationship_type}"]
        assert row["predecessor_id"] == "A1"
        assert row["successor_id"] == "A2"
        assert row["relationship_type"] == relationship_type
        assert row["lag_value"] == Decimal(lag)
        # Lag and lead are expressed in working days, never calendar days.
        assert row["lag_unit"] == "working-day"

    # The schedule settings and calendar actually reach the persistence port.
    assert settings.applied[-1]["data_date"] == "2026-03-21"
    assert settings.applied[-1]["calendar"]["calendar_id"] == "CAL-1"
    assert settings.applied[-1]["calendar"]["working_weekdays"] == [6, 0, 1, 2, 3]

    replay = port.apply_schedule(
        context, edges, data_date="2026-03-21", calendar=calendar, idempotency_key="run-1"
    )
    assert (replay["created"], replay["unchanged"]) == (0, 4)

    for bad in ({"lag_days": 366}, {"lag_days": -366}, {"lag_days": True}, {"lag_days": 1.5}):
        with pytest.raises(ProjectPlanError, match="PROJECT_PLAN_LAG_INVALID"):
            port.apply_schedule(
                context,
                [{"predecessor_id": "A1", "successor_id": "A2", **bad}],
                data_date="2026-03-21",
                calendar=calendar,
                idempotency_key="run-1",
            )


def test_verify_reports_missing_records(apis, context) -> None:
    wbs, activities, relationships, settings = apis
    port = MasterDataPlanPort(wbs, activities, relationships, settings)
    port.apply_wbs(context, _nodes(), idempotency_key="run-1")
    port.apply_activities(context, _activities(), idempotency_key="run-1")
    port.apply_schedule(
        context,
        [{"predecessor_id": "A1", "successor_id": "A2"}],
        data_date="2026-03-01",
        calendar={"calendar_id": "CAL-1"},
        idempotency_key="run-1",
    )

    verified = port.verify(
        context,
        {
            "wbs_ids": ["W1", "W2"],
            "activity_ids": ["A1", "A2"],
            "relationship_ids": ["R-A1-A2-FS"],
            "data_date": "2026-03-01",
            "calendar": {"calendar_id": "CAL-1"},
        },
    )
    assert verified["verified"] is True
    assert verified["missing"] == []

    missing = port.verify(
        context,
        {
            "wbs_ids": ["W1", "W9"],
            "activity_ids": ["A1"],
            "relationship_ids": [],
            "data_date": "2026-03-01",
            "calendar": {"calendar_id": "CAL-1"},
        },
    )
    assert missing["verified"] is False
    assert missing["missing"] == ["W9"]


def test_unavailable_port_fails_closed(context) -> None:
    port = UnavailableProjectPlanPort()
    for call in (
        lambda: port.apply_wbs(context, [], idempotency_key="x"),
        lambda: port.apply_activities(context, [], idempotency_key="x"),
        lambda: port.apply_schedule(
            context, [], data_date="2026-03-01", calendar={}, idempotency_key="x"
        ),
        lambda: port.verify(context, {}),
    ):
        with pytest.raises(ProjectPlanError, match="PROJECT_PLAN_PORT_UNAVAILABLE"):
            call()


def test_plan_context_requires_trusted_identity() -> None:
    with pytest.raises(ProjectPlanError):
        PlanContext(
            tenant_id="",
            project_id="PRJ-1",
            project_revision=0,
            user_id="planner-1",
            roles=frozenset({"planner"}),
        ).validate()
    with pytest.raises(ProjectPlanError):
        PlanContext(
            tenant_id="tenant-1",
            project_id="PRJ-1",
            project_revision=0,
            user_id="planner-1",
            roles=frozenset(),
        ).validate()


class _SettingsRepository:
    def __init__(self) -> None:
        self.stored = None

    def get(self, scope):
        return self.stored


class _PublicationAPI:
    def __init__(self, repository: _SettingsRepository) -> None:
        self.repository = repository
        self.calls: list[dict[str, object]] = []

    def save_settings(self, scope, *, settings, expected_revision, auth_context):
        self.calls.append(
            {
                "scope": scope,
                "settings": settings,
                "expected_revision": expected_revision,
            }
        )
        self.repository.stored = settings
        return {"record_revision": expected_revision + 1}


class _CalendarRepository:
    def get(self, scope, calendar_id, calendar_version):
        return object()

    def save(self, master, *, expected_revision=0):
        raise AssertionError("an existing calendar must not be recreated")


class _CalendarSnapshotRepository:
    def get(self, master):
        return object()

    def save(self, master, calendar):
        raise AssertionError("an existing calendar snapshot must not be recreated")


def test_real_schedule_settings_writer_persists_and_verifies(context) -> None:
    repository = _SettingsRepository()
    publication = _PublicationAPI(repository)
    writer = RealScheduleSettingsWriter(
        publication_api=publication,
        calendar_repository=_CalendarRepository(),
        calendar_snapshot_repository=_CalendarSnapshotRepository(),
        settings_repository=repository,
    )
    calendar = {
        "calendar_id": "CAL-1",
        "calendar_version": "1",
        "calendar_system": "gregorian",
        "working_weekdays": [0, 1, 2, 3, 4],
    }

    applied = writer.apply(context, data_date="2026-03-01", calendar=calendar)

    assert applied["calendar_id"] == "CAL-1"
    assert applied["data_date"] == "2026-03-01"
    assert publication.calls[0]["expected_revision"] == 0
    assert repository.stored is not None
    verified = writer.verify(context, data_date="2026-03-01", calendar=calendar)
    assert verified == {"verified": True, "data_date": "2026-03-01"}
