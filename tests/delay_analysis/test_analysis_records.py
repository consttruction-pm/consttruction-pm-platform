from datetime import date, datetime, timezone
import sqlite3

import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.delay_analysis.analysis_records import (
    DelayAnalysisCase,
    DelayAnalysisRecordError,
    DelayAnalysisReview,
    DelayAnalysisRevision,
    SQLiteDelayAnalysisRecordRepository,
)


NOW = datetime(2026, 11, 18, 12, tzinfo=timezone.utc)
HASH_A = "a" * 64
HASH_B = "b" * 64
HASH_C = "c" * 64
SCOPE = BackendScope("TENANT-1", "PROJECT-1", 7)


def make_case():
    return DelayAnalysisCase(
        scope=SCOPE,
        case_id="DA-CASE-1",
        idempotency_key="request-1",
        request_hash=HASH_A,
        created_by="analyst-1",
        created_at=NOW,
    )


def make_revision(revision=1, *, key=None, current_date=date(2026, 11, 17)):
    return DelayAnalysisRevision(
        scope=SCOPE,
        case_id="DA-CASE-1",
        revision=revision,
        revision_key=key or f"revision-{revision}",
        method="P6_EPPM_STYLE_INSERTED_FRAGNET_WHAT_IF",
        baseline_snapshot_id="BASELINE-SNAPSHOT",
        baseline_snapshot_hash=HASH_A,
        baseline_data_date=date(2026, 11, 10),
        current_snapshot_id=f"CURRENT-SNAPSHOT-{revision}",
        current_snapshot_hash=HASH_B if revision == 1 else HASH_C,
        current_data_date=current_date,
        data_date_basis="APPROVED_CONTEMPORANEOUS_UPDATE",
        data_date_rationale="Approved statused update selected for the analysis cut-off.",
        statused_update_evidence_hash=HASH_C,
        event_evidence_manifest_hash=HASH_B,
        result_hash=HASH_A,
        created_by="analyst-1",
        created_at=NOW,
    )


def test_case_and_analysis_revisions_are_idempotent_and_append_only():
    connection = sqlite3.connect(":memory:")
    repository = SQLiteDelayAnalysisRecordRepository(connection)
    repository.initialize()

    case = make_case()
    assert repository.create_case(case) == case
    assert repository.create_case(case) == case

    revision = make_revision()
    assert repository.append_revision(revision) == revision
    assert repository.append_revision(revision) == revision
    assert repository.list_revisions(SCOPE, case.case_id) == (revision,)

    with pytest.raises(sqlite3.IntegrityError, match="APPEND_ONLY_ANALYSIS_REVISION"):
        connection.execute(
            "UPDATE eng_delay_analysis_revision SET payload_json='{}' WHERE case_id=?",
            (case.case_id,),
        )
    with pytest.raises(sqlite3.IntegrityError, match="APPEND_ONLY_ANALYSIS_CASE"):
        connection.execute(
            "DELETE FROM eng_delay_analysis_case WHERE case_id=?",
            (case.case_id,),
        )


def test_revision_sequence_and_data_date_governance_fail_closed():
    connection = sqlite3.connect(":memory:")
    repository = SQLiteDelayAnalysisRecordRepository(connection)
    repository.initialize()
    repository.create_case(make_case())

    with pytest.raises(DelayAnalysisRecordError, match="CURRENT_DATA_DATE_PRECEDES_BASELINE"):
        repository.append_revision(make_revision(current_date=date(2026, 11, 9)))

    with pytest.raises(DelayAnalysisRecordError, match="RECONSTRUCTED_DATA_DATE_REQUIRES_RATIONALE"):
        make_revision().__class__(
            **{
                **make_revision().__dict__,
                "data_date_basis": "RECONSTRUCTED",
                "data_date_rationale": "",
            }
        ).validate()

    repository.append_revision(make_revision())
    with pytest.raises(DelayAnalysisRecordError, match="ANALYSIS_REVISION_SEQUENCE_CONFLICT"):
        repository.append_revision(make_revision(revision=3))


def test_review_requires_independent_reviewer_and_rejection_blocks_approval():
    connection = sqlite3.connect(":memory:")
    repository = SQLiteDelayAnalysisRecordRepository(connection)
    repository.initialize()
    repository.create_case(make_case())
    repository.append_revision(make_revision())

    self_review = DelayAnalysisReview(
        scope=SCOPE, case_id="DA-CASE-1", revision=1, reviewer_id="analyst-1",
        decision="APPROVE", rationale="Looks good.", reviewed_at=NOW,
    )
    with pytest.raises(DelayAnalysisRecordError, match="SELF_REVIEW_NOT_ALLOWED"):
        repository.record_review(self_review)

    approval = DelayAnalysisReview(
        scope=SCOPE, case_id="DA-CASE-1", revision=1, reviewer_id="reviewer-1",
        decision="APPROVE", rationale="Evidence and assumptions independently checked.",
        reviewed_at=NOW,
    )
    assert repository.record_review(approval) == approval
    assert repository.is_review_approved(SCOPE, "DA-CASE-1", 1)

    rejection = DelayAnalysisReview(
        scope=SCOPE, case_id="DA-CASE-1", revision=1, reviewer_id="reviewer-2",
        decision="REJECT", rationale="Data-date evidence is insufficient.",
        reviewed_at=NOW,
    )
    repository.record_review(rejection)
    assert not repository.is_review_approved(SCOPE, "DA-CASE-1", 1)


def test_reusing_idempotency_key_with_different_payload_is_rejected():
    connection = sqlite3.connect(":memory:")
    repository = SQLiteDelayAnalysisRecordRepository(connection)
    repository.initialize()
    repository.create_case(make_case())
    conflicting = DelayAnalysisCase(
        scope=SCOPE, case_id="DA-CASE-2", idempotency_key="request-1",
        request_hash=HASH_B, created_by="analyst-1", created_at=NOW,
    )
    with pytest.raises(DelayAnalysisRecordError, match="CASE_IDEMPOTENCY_CONFLICT"):
        repository.create_case(conflicting)


@pytest.fixture(scope="module")
def postgres_dsn():
    import os
    value = os.getenv("P6_TEST_POSTGRES_DSN")
    if not value:
        pytest.skip("P6_TEST_POSTGRES_DSN is not configured")
    return value


def test_postgres_analysis_records_round_trip_and_append_only(postgres_dsn):
    psycopg = pytest.importorskip("psycopg")
    from uuid import uuid4
    from construction_pm.delay_analysis.analysis_records import PostgresDelayAnalysisRecordRepository

    suffix = uuid4().hex
    scope = BackendScope(f"T-{suffix}", f"P-{suffix}", 1)
    now = NOW
    case = DelayAnalysisCase(
        scope=scope, case_id=f"CASE-{suffix}", idempotency_key=f"REQ-{suffix}",
        request_hash=HASH_A, created_by="analyst", created_at=now,
    )
    revision = DelayAnalysisRevision(
        scope=scope, case_id=case.case_id, revision=1, revision_key=f"REV-{suffix}",
        method="P6_EPPM_STYLE_INSERTED_FRAGNET_WHAT_IF",
        baseline_snapshot_id="SOURCE", baseline_snapshot_hash=HASH_A,
        baseline_data_date=date(2026, 11, 10),
        current_snapshot_id="IMPACTED", current_snapshot_hash=HASH_B,
        current_data_date=date(2026, 11, 17),
        data_date_basis="APPROVED_CONTEMPORANEOUS_UPDATE",
        data_date_rationale="Approved update evidence linked.",
        statused_update_evidence_hash=HASH_C,
        event_evidence_manifest_hash=HASH_B,
        result_hash=HASH_A, created_by="analyst", created_at=now,
    )
    connection = psycopg.connect(postgres_dsn)
    try:
        repository = PostgresDelayAnalysisRecordRepository(connection)
        repository.initialize()
        repository.create_case(case)
        repository.append_revision(revision)
        assert repository.list_revisions(scope, case.case_id) == (revision,)
        repository.record_review(DelayAnalysisReview(
            scope=scope, case_id=case.case_id, revision=1, reviewer_id="reviewer",
            decision="APPROVE", rationale="Independent review completed.", reviewed_at=now,
        ))
        assert repository.is_review_approved(scope, case.case_id, 1)
        with pytest.raises(psycopg.errors.RaiseException, match="APPEND_ONLY_DELAY_ANALYSIS_RECORD"):
            connection.execute(
                "UPDATE eng_delay_analysis_revision SET payload_json='{}' "
                "WHERE tenant_id=%s AND project_id=%s AND case_id=%s AND revision=1",
                (scope.tenant_id, scope.project_id, case.case_id),
            )
    finally:
        connection.rollback()
        connection.close()
