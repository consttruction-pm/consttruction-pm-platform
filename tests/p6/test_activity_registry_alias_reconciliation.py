import json
from pathlib import Path


def test_activity_registry_alias_reconciliation_uses_only_release_26_candidates():
    artifact = json.loads(
        Path(
            "docs/architecture/P6_ACTIVITY_REGISTRY_ALIAS_RECONCILIATION_2026-10-02.json"
        ).read_text(encoding="utf-8")
    )

    entries = artifact["entries"]
    assert len(entries) == 9
    assert {entry["registry_name"] for entry in entries} == {
        "ActivityId",
        "ActivityName",
        "ActivityOwner",
        "ActivityStatus",
        "ActivityType",
        "Calendar",
        "RemainingStartDate",
        "RemainingFinishDate",
        "UpdateUser",
    }
    assert all(entry["legacy_name_in_activity_export"] is False for entry in entries)
    assert all(entry["candidate_export_names"] for entry in entries)
    assert all(entry["mapping_status"] in {"candidate_alias", "unresolved"} for entry in entries)

    unresolved = {
        entry["registry_name"]
        for entry in entries
        if entry["mapping_status"] == "unresolved"
    }
    assert unresolved == {"ActivityOwner", "Calendar", "RemainingFinishDate"}

    by_name = {entry["registry_name"]: entry for entry in entries}
    assert by_name["ActivityId"]["official_p6_candidates"] == ["Id"]
    assert by_name["ActivityName"]["official_p6_candidates"] == ["Name"]
    assert by_name["ActivityStatus"]["official_p6_candidates"] == ["Status"]
    assert by_name["ActivityType"]["official_p6_candidates"] == ["Type"]
    assert by_name["RemainingStartDate"]["official_p6_candidates"] == ["RemainingEarlyStartDate"]
    assert by_name["UpdateUser"]["official_p6_candidates"] == ["LastUpdateUser"]
    assert by_name["ActivityOwner"]["official_p6_candidates"] == [
        "ActivityOwnerUserId",
        "OwnerIDArray",
        "OwnerNamesArray",
    ]
    assert by_name["Calendar"]["official_p6_candidates"] == [
        "CalendarName",
        "CalendarObjectId",
    ]
    assert by_name["RemainingFinishDate"]["official_p6_candidates"] == [
        "RemainingEarlyFinishDate",
        "RemainingLateFinishDate",
    ]
