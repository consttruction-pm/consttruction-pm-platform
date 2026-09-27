import json


def test_p6_field_parity_inventory_is_typed_and_explicitly_unverified():
    with open("shared/contracts/p6-field-parity-inventory.v1.json", encoding="utf-8") as handle:
        data = json.load(handle)
    assert data["$schema"] == "constructionpm://contracts/p6-field-parity-entry/v1"
    assert data["registry_version"] == "p6-field-parity-inventory.v1"
    assert data["status"] == "seeded_not_certified"
    assert data["field_count"] == len(data["fields"])
    assert data["field_count"] == 118
    assert all(item["disposition"] == "seeded_not_certified" for item in data["fields"])
    assert all(item["evidence_url"] for item in data["fields"])


def test_schedule_options_are_present_in_parity_inventory():
    with open("shared/contracts/p6-field-parity-inventory.v1.json", encoding="utf-8") as handle:
        data = json.load(handle)
    schedule_options = {item["p6_field"] for item in data["fields"] if item["subject_area"] == "ScheduleOptions"}
    assert {
        "CalculateFloatBasedOnFinishDate",
        "ComputeTotalFloatType",
        "MultipleFloatPathsEnabled",
        "MultipleFloatPathsEndingActivityObjectId",
        "OutOfSequenceScheduleType",
        "RelationshipLagCalendar",
        "StartToStartLagCalculationType",
        "UseExpectedFinishDates",
    } <= schedule_options
