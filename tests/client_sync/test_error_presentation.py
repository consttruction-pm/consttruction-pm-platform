from construction_pm.client_sync.errors import ClientErrorPresentation, present_stable_error


def error_payload(message="Validation failed"):
    return {
        "error": {
            "category": "validation",
            "code": "INVALID_ACTIVITY",
            "message": message,
            "retryable": False,
        }
    }


def test_presents_stable_error_without_message_dependency():
    first = present_stable_error(error_payload("Validation failed"))
    second = present_stable_error(error_payload("نام فعالیت نامعتبر است"))

    assert first is not None
    assert second is not None
    assert first.identity == second.identity == ("validation", "INVALID_ACTIVITY")
    assert first.retryable is False
    assert second.retryable is False
    assert first.message != second.message


def test_retryable_is_preserved_as_transport_semantics():
    payload = {
        "error": {
            "category": "persistence",
            "code": "TEMPORARY_STORE_FAILURE",
            "message": "temporary failure",
            "retryable": True,
        }
    }

    presentation = present_stable_error(payload)

    assert presentation == ClientErrorPresentation(
        category="persistence",
        code="TEMPORARY_STORE_FAILURE",
        message="temporary failure",
        retryable=True,
    )


def test_unknown_category_is_rejected():
    payload = error_payload()
    payload["error"]["category"] = "unknown"

    try:
        present_stable_error(payload)
    except ValueError as exc:
        assert "unsupported application error category" in str(exc)
    else:
        raise AssertionError("unknown category must be rejected")


def test_malformed_payload_is_not_presented():
    assert present_stable_error({"error": {"category": "validation"}}) is None
