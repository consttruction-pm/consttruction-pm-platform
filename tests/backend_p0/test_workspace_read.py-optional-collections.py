

@pytest.mark.parametrize(
    "key",
    [
        "change_notices",
        "change_cases",
        "claims",
        "change_claim_impacts",
        "documents",
        "procurement_rfqs",
        "procurement_quotes",
        "procurement_bid_comparisons",
        "purchase_orders",
        "procurement_commitments",
        "procurement_deliveries",
    ],
)
def test_workspace_read_service_rejects_malformed_optional_collection(key: str) -> None:
    value = snapshot()
    value[key] = {"invalid": True}
    service = service_with(value)

    with pytest.raises(Exception) as exc:
        service.read(BackendScope("tenant-1", "project-1", 7), auth_context=auth())

    assert getattr(exc.value, "code") == "INVALID_WORKSPACE_READ_COLLECTION"
