import pytest

from construction_pm.api_errors import (
    APIError,
    APIErrorCategory,
    authorization_error,
    conflict_error,
    persistence_error,
    validation_error,
)


def test_error_categories_are_stable_and_machine_readable():
    error = conflict_error("STALE_REVISION", "revision is stale")
    error.validate()
    assert error.category.value == "conflict"
    assert error.retryable is False


def test_persistence_errors_default_to_retryable():
    error = persistence_error("DB_UNAVAILABLE", "database unavailable")
    assert error.retryable is True


@pytest.mark.parametrize("factory,category", [
    (validation_error, APIErrorCategory.VALIDATION),
    (authorization_error, APIErrorCategory.AUTHORIZATION),
])
def test_factories_preserve_category(factory, category):
    assert factory("E", "message").category is category


def test_invalid_error_contract_is_rejected():
    with pytest.raises(ValueError, match="INVALID_API_ERROR_CODE"):
        APIError(APIErrorCategory.CONTEXT, "", "message").validate()
