from decimal import Decimal

from construction_pm.resources.idempotency import assignment_fingerprint, resource_fingerprint
from construction_pm.resources.models import Resource, ResourceAssignment, ResourceType


def resource() -> Resource:
    return Resource("R-1", "LAB-01", "Labor", ResourceType.LABOR, "hour", (), None, True)


def assignment() -> ResourceAssignment:
    return ResourceAssignment("A-1", "R-1", Decimal("10"), Decimal("2"))


def test_resource_fingerprint_binds_expected_revision():
    assert resource_fingerprint(resource(), 1) != resource_fingerprint(resource(), 2)
    assert resource_fingerprint(resource(), None) != resource_fingerprint(resource(), 1)


def test_assignment_fingerprint_binds_expected_revision():
    assert assignment_fingerprint(assignment(), 1) != assignment_fingerprint(assignment(), 2)
    assert assignment_fingerprint(assignment(), None) != assignment_fingerprint(assignment(), 1)
