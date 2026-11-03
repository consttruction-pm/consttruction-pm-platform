from __future__ import annotations

import sqlite3
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.backend_p0.transactions import SQLiteTransactionManager
from construction_pm.p6_resource_rate_repository import (
    P6ResourceRateApplicationService,
    P6ResourceRateRecord,
    P6ResourceRateRepositoryError,
    SQLiteP6ResourceRateRepository,
    plan_rate_supersession,
)
from construction_pm.resources.models import CostBasis, Resource, ResourceType
from construction_pm.resources.rate_facts import (
    ResourceRateFact,
    ResourceRateFactError,
    ResourceRateProfile,
    compute_rate_identity,
)

SCOPE = BackendScope("t1", "p1", 3)


def _fact(
    *,
    resource_id: str = "LAB-1",
    rate: str = "85.50",
    basis: CostBasis = CostBasis.PER_HOUR,
    currency: str = "USD",
    unit: str = "hour",
    start: date = date(2026, 10, 1),
    end: date | None = None,
    source: str = "manual-entry",
) -> ResourceRateFact:
    return ResourceRateFact.create(
        resource_id=resource_id,
        rate=Decimal(rate),
        basis=basis,
        currency=currency,
        unit=unit,
        effective_from=start,
        effective_to=end,
        source=source,
    )


def _service(
    connection: sqlite3.Connection | None = None,
) -> tuple[
    P6ResourceRateApplicationService,
    SQLiteP6ResourceRateRepository,
    sqlite3.Connection,
]:
    connection = connection or sqlite3.connect(":memory:")
    repository = SQLiteP6ResourceRateRepository(connection)
    service = P6ResourceRateApplicationService(
        repository, SQLiteTransactionManager(connection)
    )
    return service, repository, connection


def test_rate_identity_is_content_addressed_and_version_independent() -> None:
    fact = _fact()
    assert fact.identity == compute_rate_identity(
        resource_id="LAB-1",
        rate=Decimal("85.50"),
        basis=CostBasis.PER_HOUR,
        currency="USD",
        unit="hour",
        effective_from=date(2026, 10, 1),
        effective_to=None,
        source="manual-entry",
    )
    # Numerically equal rates hash identically regardless of decimal scale.
    assert _fact(rate="85.5").identity == fact.identity
    # Any priced content difference produces a different identity.
    assert _fact(rate="85.51").identity != fact.identity
    assert _fact(currency="EUR").identity != fact.identity
    assert _fact(basis=CostBasis.PER_DAY).identity != fact.identity
    assert _fact(unit="day").identity != fact.identity
    assert _fact(source="import").identity != fact.identity
    assert _fact(end=date(2026, 12, 31)).identity != fact.identity
    # The stored identity round-trips into a validated immutable fact.
    reconstructed = ResourceRateFact(
        resource_id=fact.resource_id,
        rate=fact.rate,
        basis=fact.basis,
        currency=fact.currency,
        unit=fact.unit,
        effective_from=fact.effective_from,
        effective_to=fact.effective_to,
        source=fact.source,
        identity=fact.identity,
    )
    assert reconstructed == fact


@pytest.mark.parametrize(
    ("kwargs", "code"),
    [
        ({"rate": Decimal("NaN")}, "INVALID_RATE_VALUE"),
        ({"rate": Decimal("-1")}, "INVALID_RATE_VALUE"),
        ({"currency": "  "}, "INVALID_RATE_CURRENCY"),
        ({"unit": ""}, "INVALID_RATE_UNIT"),
        ({"source": ""}, "INVALID_RATE_SOURCE"),
        ({"start": datetime(2026, 10, 1, 8, 0)}, "INVALID_RATE_EFFECTIVE_FROM"),
        (
            {
                "start": date(2026, 10, 10),
                "end": date(2026, 10, 1),
            },
            "INVALID_RATE_INTERVAL",
        ),
    ],
)
def test_rate_fact_rejects_invalid_content(kwargs, code) -> None:
    with pytest.raises(ResourceRateFactError, match=code):
        _fact(**kwargs)


def test_rate_identity_mismatch_is_rejected() -> None:
    fact = _fact()
    with pytest.raises(ResourceRateFactError, match="RATE_IDENTITY_MISMATCH"):
        ResourceRateFact(
            resource_id=fact.resource_id,
            rate=Decimal("90"),
            basis=fact.basis,
            currency=fact.currency,
            unit=fact.unit,
            effective_from=fact.effective_from,
            effective_to=fact.effective_to,
            source=fact.source,
            identity=fact.identity,
        )


def test_rate_profile_resolves_exactly_one_effective_fact() -> None:
    first = _fact(start=date(2026, 10, 1), end=date(2026, 10, 31), rate="80")
    second = _fact(start=date(2026, 11, 1), rate="95", source="approved-change")
    profile = ResourceRateProfile("LAB-1", (second, first))

    assert profile.facts == (first, second)
    assert profile.fact_on(date(2026, 10, 15)) == first
    assert profile.fact_on(date(2026, 11, 1)) == second
    with pytest.raises(ResourceRateFactError, match="RATE_NOT_EFFECTIVE"):
        profile.fact_on(date(2026, 9, 30))

    overlapping = _fact(start=date(2026, 10, 31), rate="81")
    with pytest.raises(ResourceRateFactError, match="RATE_INTERVALS_OVERLAP"):
        ResourceRateProfile("LAB-1", (first, overlapping))
    with pytest.raises(ResourceRateFactError, match="RATE_RESOURCE_MISMATCH"):
        ResourceRateProfile("LAB-1", (_fact(resource_id="LAB-2"),))


def test_rate_fact_projects_into_the_shared_resource_model() -> None:
    first = _fact(start=date(2026, 10, 1), rate="80", end=date(2026, 10, 31))
    second = _fact(start=date(2026, 11, 1), rate="95", end=None, source="approved")
    fallback = _fact(start=date(2025, 1, 1), rate="70", end=date(2025, 12, 31))
    profile = ResourceRateProfile("LAB-1", (first, fallback, second))
    resource = Resource(
        id="LAB-1",
        code="LAB-1",
        name="Labor crew",
        resource_type=ResourceType.LABOR,
        unit="hour",
        rates=[fact.to_resource_rate(version=index + 1) for index, fact in enumerate(profile.facts)],
    )
    assert resource.rate_on(date(2026, 11, 2)).rate == Decimal("95")
    assert resource.rate_on(date(2025, 6, 1)).rate == Decimal("70")


def test_rate_facts_persist_effective_dates_and_scope(tmp_path) -> None:
    database = tmp_path / "rates.sqlite"
    first = _fact(start=date(2026, 10, 1), end=date(2026, 10, 14), rate="80")
    second = _fact(start=date(2026, 10, 15), rate="95", source="approved-change")
    service, _repository, connection = _service(sqlite3.connect(database))
    service.save(P6ResourceRateRecord(SCOPE, first))
    service.save(P6ResourceRateRecord(SCOPE, second))
    connection.close()

    reopened, _repository, connection = _service(sqlite3.connect(database))
    records = reopened.list(SCOPE, "LAB-1")
    assert [record.fact.rate for record in records] == [
        Decimal("80"),
        Decimal("95"),
    ]
    profile = reopened.profile(SCOPE, "LAB-1")
    assert profile.fact_on(date(2026, 10, 14)).rate == Decimal("80")
    assert profile.fact_on(date(2026, 10, 15)).rate == Decimal("95")
    with pytest.raises(ResourceRateFactError, match="RATE_NOT_EFFECTIVE"):
        profile.fact_on(date(2026, 9, 30))
    connection.close()


def test_rate_repository_rejects_overlap_stale_revision_and_cross_scope() -> None:
    service, repository, connection = _service()
    first = _fact(start=date(2026, 10, 1), end=date(2026, 10, 14))
    service.save(P6ResourceRateRecord(SCOPE, first))
    overlapping = _fact(start=date(2026, 10, 14), rate="90")
    with pytest.raises(ResourceRateFactError, match="RATE_INTERVALS_OVERLAP"):
        service.save(P6ResourceRateRecord(SCOPE, overlapping))

    stale_scope = BackendScope("t1", "p1", 2)
    with pytest.raises(P6ResourceRateRepositoryError, match="REVISION_CONFLICT"):
        repository.upsert(P6ResourceRateRecord(stale_scope, first))

    other_scope = BackendScope("t2", "p1", 3)
    assert repository.list(other_scope, "LAB-1") == ()
    with pytest.raises(ResourceRateFactError, match="RATE_NOT_EFFECTIVE"):
        repository.profile(other_scope, "LAB-1").fact_on(date(2026, 10, 5))
    connection.close()


def test_rate_replay_is_idempotent_but_divergent_content_is_immutable() -> None:
    service, repository, connection = _service()
    fact = _fact()
    record = P6ResourceRateRecord(SCOPE, fact)
    assert service.save(record) == record
    assert service.save(record) == record
    assert repository.get(SCOPE, "LAB-1", fact.identity) == record

    tampered = ResourceRateFact(
        resource_id=fact.resource_id,
        rate=Decimal("85.5"),
        basis=fact.basis,
        currency=fact.currency,
        unit=fact.unit,
        effective_from=fact.effective_from,
        effective_to=fact.effective_to,
        source=fact.source,
        identity=fact.identity,
    )
    # Numerically equal content is the same stored fact.
    assert service.save(P6ResourceRateRecord(SCOPE, tampered)).fact == tampered

    # The identity is content-addressed, so a divergent body cannot reuse an
    # existing identity: construction itself fails closed.
    with pytest.raises(ResourceRateFactError, match="RATE_IDENTITY_MISMATCH"):
        ResourceRateFact(
            resource_id=fact.resource_id,
            rate=Decimal("85.51"),
            basis=fact.basis,
            currency=fact.currency,
            unit=fact.unit,
            effective_from=fact.effective_from,
            effective_to=fact.effective_to,
            source=fact.source,
            identity=fact.identity,
        )
    connection.close()


def test_effective_rate_change_closes_the_open_fact_append_only() -> None:
    service, repository, connection = _service()
    original = _fact(start=date(2026, 10, 1), end=None, source="manual-entry:user-1")
    service.save(P6ResourceRateRecord(SCOPE, original))
    change = _fact(
        rate="92.25",
        start=date(2026, 10, 15),
        end=None,
        source="manual-entry:user-1",
    )

    result = service.save_effective_change(
        P6ResourceRateRecord(SCOPE, change),
        close_open_segment=True,
        recorded_at=datetime(2026, 10, 26, 9, 30, tzinfo=timezone.utc),
    )

    assert result.superseded_identity == original.identity
    assert result.closed_fact is not None
    assert result.closed_fact.effective_to == date(2026, 10, 14)
    assert result.closed_fact.identity != original.identity
    assert result.closed_fact.rate == original.rate
    assert result.record.fact.identity == change.identity

    active = service.list(SCOPE, "LAB-1")
    assert [
        (item.fact.rate, item.fact.effective_from, item.fact.effective_to)
        for item in active
    ] == [
        (Decimal("85.50"), date(2026, 10, 1), date(2026, 10, 14)),
        (Decimal("92.25"), date(2026, 10, 15), None),
    ]
    profile = service.profile(SCOPE, "LAB-1")
    assert profile.fact_on(date(2026, 10, 14)).rate == Decimal("85.50")
    assert profile.fact_on(date(2026, 10, 15)).rate == Decimal("92.25")

    stored = connection.execute(
        "SELECT COUNT(*) FROM p6_resource_rate_fact "
        "WHERE tenant_id='t1' AND project_id='p1' AND resource_id='LAB-1'"
    ).fetchone()
    assert stored is not None and int(stored[0]) == 3
    supersessions = connection.execute(
        "SELECT identity,superseded_by_identity,recorded_at "
        "FROM p6_resource_rate_supersession"
    ).fetchall()
    assert supersessions == [
        (
            original.identity,
            result.closed_fact.identity,
            "2026-10-26T09:30:00+00:00",
        )
    ]
    assert repository.get(SCOPE, "LAB-1", original.identity) is None
    connection.close()


def test_effective_rate_change_is_idempotent_and_rejects_bounded_replacement() -> None:
    service, repository, connection = _service()
    original = _fact(start=date(2026, 10, 1), end=None, source="manual")
    service.save(P6ResourceRateRecord(SCOPE, original))
    change = _fact(rate="92.25", start=date(2026, 10, 15), end=None, source="manual")
    first = service.save_effective_change(
        P6ResourceRateRecord(SCOPE, change),
        close_open_segment=True,
        recorded_at=datetime(2026, 10, 26, tzinfo=timezone.utc),
    )
    second = service.save_effective_change(
        P6ResourceRateRecord(SCOPE, change),
        close_open_segment=True,
        recorded_at=datetime(2026, 10, 26, tzinfo=timezone.utc),
    )
    assert second.record.fact.identity == first.record.fact.identity
    assert second.superseded_identity is None
    assert len(service.list(SCOPE, "LAB-1")) == 2

    bounded = _fact(
        rate="99",
        start=date(2026, 11, 1),
        end=date(2026, 11, 10),
        source="manual",
    )
    with pytest.raises(
        P6ResourceRateRepositoryError,
        match="RATE_REPLACEMENT_REQUIRES_OPEN_RANGE",
    ):
        service.save_effective_change(
            P6ResourceRateRecord(SCOPE, bounded),
            close_open_segment=True,
            recorded_at=datetime(2026, 10, 26, tzinfo=timezone.utc),
        )

    # A change that starts on or before the open fact cannot shorten it
    # without a previously closed interval; it must be refused.
    same_start = _fact(rate="77", start=date(2026, 10, 1), end=None, source="manual")
    with pytest.raises(
        P6ResourceRateRepositoryError,
        match="RATE_REPLACEMENT_NOT_APPLICABLE|RATE_INTERVALS_OVERLAP",
    ):
        service.save_effective_change(
            P6ResourceRateRecord(SCOPE, same_start),
            close_open_segment=True,
            recorded_at=datetime(2026, 10, 26, tzinfo=timezone.utc),
        )
    assert len(service.list(SCOPE, "LAB-1")) == 2
    assert repository.get(SCOPE, "LAB-1", original.identity) is None
    connection.close()


def test_plan_rate_supersession_requires_open_prior_fact() -> None:
    closed = _fact(start=date(2026, 10, 1), end=date(2026, 10, 10))
    candidate = _fact(start=date(2026, 10, 5), end=None)
    with pytest.raises(P6ResourceRateRepositoryError, match="RATE_INTERVALS_OVERLAP"):
        plan_rate_supersession((closed,), candidate)

    open_fact = _fact(start=date(2026, 10, 1), end=None)
    replacement = plan_rate_supersession(
        (open_fact,), _fact(start=date(2026, 10, 15), end=None)
    )
    assert replacement is not None
    assert replacement.effective_to == date(2026, 10, 14)
    assert plan_rate_supersession(
        (open_fact,), _fact(start=date(2026, 11, 1), end=None)
    ).effective_to == date(2026, 10, 31)  # type: ignore[union-attr]
