from __future__ import annotations

import os
import uuid
from datetime import date

import pytest

psycopg = pytest.importorskip("psycopg")
DSN = os.getenv("CONSTRUCTION_PM_POSTGRES_DSN") or os.getenv("P6_TEST_POSTGRES_DSN")
if not DSN:
    pytest.skip("CONSTRUCTION_PM_POSTGRES_DSN is not configured", allow_module_level=True)

from construction_pm.claim_day_archive import (
    ClaimDayArchive,
    ClaimDayArchiveService,
    ClaimDayEvidenceLink,
    ClaimDayRevisionConflict,
    ClaimDayVisibility,
    PostgresClaimDayArchiveRepository,
)


def test_claim_day_archive_postgres_round_trip_replay_and_submission_freeze():
    suffix = uuid.uuid4().hex
    tenant_id, project_id = f"tenant-{suffix}", f"project-{suffix}"
    claim_id, contract_id = f"claim-{suffix}", f"contract-{suffix}"
    day_id = f"claim-day-{suffix}"
    day = ClaimDayArchive(
        tenant_id=tenant_id,
        project_id=project_id,
        contract_id=contract_id,
        claim_id=claim_id,
        claim_day_id=day_id,
        reporting_date=date(2026, 10, 25),
        timezone="Europe/Berlin",
        claim_party_ids=("EMPLOYER", "CONTRACTOR"),
    )
    evidence = ClaimDayEvidenceLink(
        evidence_link_id=f"evidence-{suffix}",
        source_system="cubi-document-management",
        source_type="document",
        source_id=f"document-{suffix}",
        source_revision=2,
        source_content_version="content-v2",
        actor_id="contractor-user",
        effective_at="2026-10-25T09:00:00+02:00",
        party_visibility=ClaimDayVisibility.PRIVATE,
        owner_party_id="CONTRACTOR",
        content_sha256="sha256:" + "c" * 64,
        captured_at="2026-10-25T09:01:00+02:00",
        captured_timezone="Europe/Berlin",
        server_received_at="2026-10-25T07:05:00Z",
        activity_refs=("ACT-1",),
        wbs_refs=("WBS-1",),
        delay_event_refs=("DE-1",),
    )

    with psycopg.connect(DSN) as connection:
        repository = PostgresClaimDayArchiveRepository(connection)
        repository.initialize()
        connection.commit()
        service = ClaimDayArchiveService(repository)

        created = service.create_day(day, idempotency_key=f"create-{suffix}")
        assert created.revision == 1
        updated = service.add_evidence(
            tenant_id=tenant_id,
            project_id=project_id,
            claim_day_id=day_id,
            evidence=evidence,
            expected_revision=1,
            idempotency_key=f"evidence-{suffix}",
        )
        assert updated.revision == 2
        assert repository.get_day(tenant_id, project_id, day_id) == updated
        assert repository.get_day_revision(tenant_id, project_id, day_id, 1) == created
        assert repository.get_day_revision(tenant_id, project_id, day_id, 2) == updated

        # Revision snapshots are protected at the database boundary, not only
        # by repository methods.
        with pytest.raises(psycopg.errors.RaiseException):
            with connection.transaction():
                connection.execute(
                    "UPDATE claim_day_archive_revisions SET day_json=%s "
                    "WHERE tenant_id=%s AND project_id=%s AND claim_day_id=%s AND revision=1",
                    ("{}", tenant_id, project_id, day_id),
                )
        with pytest.raises(psycopg.errors.RaiseException):
            with connection.transaction():
                connection.execute(
                    "DELETE FROM claim_day_archive_revisions "
                    "WHERE tenant_id=%s AND project_id=%s AND claim_day_id=%s AND revision=1",
                    (tenant_id, project_id, day_id),
                )


        replay = repository.put_day(
            updated, expected_revision=1, idempotency_key=f"evidence-{suffix}"
        )
        assert replay == updated

        with pytest.raises(ClaimDayRevisionConflict):
            service.add_evidence(
                tenant_id=tenant_id,
                project_id=project_id,
                claim_day_id=day_id,
                evidence=ClaimDayEvidenceLink(
                    **{**evidence.__dict__, "evidence_link_id": f"stale-{suffix}"}
                ),
                expected_revision=1,
                idempotency_key=f"stale-{suffix}",
            )

        submission = service.submit(
            tenant_id=tenant_id,
            project_id=project_id,
            contract_id=contract_id,
            claim_id=claim_id,
            submission_id=f"submission-{suffix}",
            submission_number=1,
            submitting_party_id="CONTRACTOR",
            submitted_by="contractor-user",
            submitted_at="2026-10-26T08:00:00Z",
            form_template_id="FORM-EOT",
            form_template_version="v3",
            form_snapshot={"requested_days": 7},
            claim_day_ids=(day_id,),
            schedule_snapshot_ids=(f"schedule-snapshot-{suffix}",),
            baseline_snapshot_ids=(f"baseline-snapshot-{suffix}",),
        )
        assert repository.get_submission(
            tenant_id, project_id, submission.submission_id
        ) == submission
        assert submission.manifest_sha256.startswith("sha256:")
        # Submission numbers are independently sequenced by submitting party,
        # matching the database unique key and the in-memory repository.
        employer_submission = service.submit(
            tenant_id=tenant_id,
            project_id=project_id,
            contract_id=contract_id,
            claim_id=claim_id,
            submission_id=f"employer-submission-{suffix}",
            submission_number=1,
            submitting_party_id="EMPLOYER",
            submitted_by="employer-user",
            submitted_at="2026-10-26T09:00:00Z",
            form_template_id="FORM-RESPONSE",
            form_template_version="v1",
            form_snapshot={"response": "received"},
            claim_day_ids=(day_id,),
        )
        assert employer_submission.submission_number == submission.submission_number
        assert employer_submission.submitting_party_id == "EMPLOYER"

