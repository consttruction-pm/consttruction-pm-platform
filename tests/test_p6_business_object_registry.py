import json


def test_p6_business_object_registry_is_versioned_and_unique():
    data = json.load(open("shared/contracts/p6-business-object-registry.v1.json", encoding="utf-8"))
    assert data["registry_version"] == "p6-business-object-registry.v1"
    assert data["reference_version"] == "P6 Professional Version 26 / P6 EPPM 26.4"
    assert data["status"] == "inventory"
    objects = data["objects"]
    assert data["object_count"] == 136
    assert len(objects) == 136
    assert len(objects) == len(set(objects))
    assert {"Activity", "Calendar", "Project", "Resource", "ResourceAssignment", "ScheduleOptions", "UDFType", "WBS", "WbsReviewers"} <= set(objects)
