from construction_pm.p6_field_registry import P6FieldType, get_field


EXPECTED = {
    "LastUpdateDate": (P6FieldType.DATETIME, False, False),
    "LastUpdateUser": (P6FieldType.STRING, False, False),
    "MaterialCostPercentComplete": (P6FieldType.DOUBLE, False, True),
    "MaximumDuration": (P6FieldType.DOUBLE, True, False),
    "MinimumDuration": (P6FieldType.DOUBLE, True, False),
    "MostLikelyDuration": (P6FieldType.DOUBLE, True, False),
    "Name": (P6FieldType.STRING, True, False),
    "NonLaborCostPercentComplete": (P6FieldType.DOUBLE, False, True),
    "NonLaborCostVariance": (P6FieldType.DOUBLE, False, True),
    "NonLaborUnits1Variance": (P6FieldType.DOUBLE, False, True),
    "NonLaborUnits2Variance": (P6FieldType.DOUBLE, False, True),
    "NonLaborUnits3Variance": (P6FieldType.DOUBLE, False, True),
    "NonLaborUnitsPercentComplete": (P6FieldType.DOUBLE, False, True),
    "NonLaborUnitsVariance": (P6FieldType.DOUBLE, False, True),
    "NotesToResources": (P6FieldType.STRING, True, False),
    "ObjectId": (P6FieldType.OBJECT_ID, False, False),
    "OwnerIDArray": (P6FieldType.STRING, True, False),
    "ReviewFinishDate": (P6FieldType.DATETIME, True, False),
    "ReviewRequired": (P6FieldType.BOOLEAN, True, False),
    "ReviewStatus": (P6FieldType.ENUM, True, False),
}


def test_release26_activity_tranche_20_is_typed_and_non_duplicated():
    for p6_field, (data_type, writable, computed) in EXPECTED.items():
        matches = [
            field
            for field in __import__("construction_pm.p6_field_registry", fromlist=["field_catalog"]).field_catalog()
            if field.subject_area == "Activity" and field.p6_field == p6_field
        ]
        assert len(matches) == 1, p6_field
        field = matches[0]
        assert field.data_type is data_type
        assert field.writable is writable
        assert field.computed is computed
        assert field.disposition == "seeded_not_certified"


def test_release26_activity_tranche_20_cannot_create_writable_computed_fields():
    for p6_field in EXPECTED:
        field = next(
            field
            for field in __import__("construction_pm.p6_field_registry", fromlist=["field_catalog"]).field_catalog()
            if field.subject_area == "Activity" and field.p6_field == p6_field
        )
        assert not (field.writable and field.computed)
