from datetime import date, timezone

import pytest

from construction_pm.claim_day_archive import (
    ClaimDayArchive,
    ClaimDayArchiveError,
    ClaimDayArchiveService,
    ClaimDayEvidenceLink,
    ClaimDayIdempotencyConflict,
    ClaimDayRevisionConflict,
    ClaimDayVisibility,
    InMemoryClaimDayArchiveRepository,
)


def day(**changes):
    values = dict(
        tenant_id="T-1",
        project_id="P-1",
        contract_id="C-1",
        claim_id="CL-1",
        claim_day_id="CL-1:2026-10-25",
        reporting_date=date(2026, 10, 25),
        timezone="Europe/Berlin",
        claim_party_ids=("EMPLOYER", "CONTRACTOR", "CONSULTANT"),
    )
    values.update(changes)
    return ClaimDayArchive(**values)


def evidence(**changes):
    values = dict(
        evidence_link_id="EV-1",
        source_system="cubi-document-management",
        source_type="document",
        source_id="DOC-1",
        source_revision=3,
        source_content_version="content-v3",
        actor_id="u-contractor",
        effective_at="2026-10-25T09:00:00+02:00",
        party_visibility=ClaimDayVisibility.PRIVATE,
        owner_party_id="CONTRACTOR",
        content_sha256="sha256:" + "a" * 64,
        captured_at="2026-10-25T09:02:00+02:00",
        captured_timezone="Europe/Berlin",
        server_received_at="2026-10-25T07:04:00Z",
        activity_refs=("ACT-1",),
        wbs_refs=("WBS-1",),
        delay_event_refs=("DE-1",),
    )
    values.update(changes)
    return ClaimDayEvidenceLink(**values)


@pytest.fixture
def service():
    return ClaimDayArchiveService(InMemoryClaimDayArchiveRepository())


def test_reporting_day_boundaries_respect_dst_transition():
    spring = day(reporting_date=date(2026, 3, 29))
    autumn = day(reporting_date=date(2026, 10, 25))
    assert (spring.day_end.astimezone(timezone.utc) - spring.day_start.astimezone(timezone.utc)).total_seconds() == 23 * 3600
    assert (autumn.day_end.astimezone(timezone.utc) - autumn.day_start.astimezone(timezone.utc)).total_seconds() == 25 * 3600
    assert spring.day_start_utc.endswith("+00:00")
    assert autumn.day_end_utc.endswith("+00:00")


def test_archive_creation_and_evidence_append_are_revision_guarded(service):
    created = service.create_day(day(), idempotency_key="create-1")
    assert created.revision == 1
    updated = service.add_evidence(
        tenant_id="T-1",
        project_id="P-1",
        claim_day_id=created.claim_day_id,
        evidence=evidence(),
        expected_revision=1,
        idempotency_key="evidence-1",
    )
    assert updated.revision == 2
    assert updated.evidence_links[0].source_revision == 3
    with pytest.raises(ClaimDayRevisionConflict):
        service.add_evidence(
            tenant_id="T-1", project_id="P-1", claim_day_id=created.claim_day_id,
            evidence=evidence(evidence_link_id="EV-2"), expected_revision=1,
            idempotency_key="evidence-2",
        )


def test_archive_cannot_remove_or_rewrite_existing_evidence():
    repository = InMemoryClaimDayArchiveRepository()
    original = day(evidence_links=(evidence(),))
    repository.put_day(original, expected_revision=0, idempotency_key="k1")
    with pytest.raises(ClaimDayArchiveError, match="CANNOT_BE_REMOVED"):
        repository.put_day(
            day(revision=2), expected_revision=1, idempotency_key="k2"
        )
    with pytest.raises(ClaimDayArchiveError, match="CANNOT_BE_REWRITTEN"):
        repository.put_day(
            day(revision=2, evidence_links=(evidence(source_revision=4),)),
            expected_revision=1,
            idempotency_key="k3",
        )


def test_private_and_explicit_party_evidence_isolated():
    private = evidence()
    explicit = evidence(
        evidence_link_id="EV-2",
        party_visibility=ClaimDayVisibility.EXPLICIT_PARTIES,
        audience_party_ids=("EMPLOYER",),
    )
    shared = evidence(
        evidence_link_id="EV-3",
        party_visibility=ClaimDayVisibility.CLAIM_PARTIES,
        owner_party_id="CONSULTANT",
    )
    archive = day(evidence_links=(private, explicit, shared))
    assert [item.evidence_link_id for item in archive.visible_evidence("CONTRACTOR")] == ["EV-1", "EV-3"]
    assert [item.evidence_link_id for item in archive.visible_evidence("EMPLOYER")] == ["EV-2", "EV-3"]
    with pytest.raises(ClaimDayArchiveError, match="NOT_ASSIGNED"):
        archive.visible_evidence("UNKNOWN")


def test_submission_freezes_exact_evidence_revisions_and_form_snapshot(service):
    created = service.create_day(day(), idempotency_key="create-1")
    service.add_evidence(
        tenant_id="T-1", project_id="P-1", claim_day_id=created.claim_day_id,
        evidence=evidence(), expected_revision=1, idempotency_key="evidence-1",
    )
    submission = service.submit(
        tenant_id="T-1", project_id="P-1", contract_id="C-1", claim_id="CL-1",
        submission_id="SUB-1", submission_number=1,
        submitting_party_id="CONTRACTOR", submitted_by="u-contractor",
        submitted_at="2026-10-26T08:00:00Z",
        form_template_id="FORM-EOT", form_template_version="v5",
        form_snapshot={"requested_days": 14, "reason": "late access"},
        claim_day_ids=(created.claim_day_id,),
        schedule_snapshot_ids=("SCHED-17",), baseline_snapshot_ids=("BASE-4",),
    )
    submission.validate()
    assert '"source_revision":3' in submission.manifest_json
    assert '"reporting_date":"2026-10-25"' in submission.manifest_json
    assert '"claim_day_id":"CL-1:2026-10-25"' in submission.manifest_json
    assert submission.form_template_version == "v5"
    assert submission.schedule_snapshot_ids == ("SCHED-17",)
    assert submission.manifest_sha256.startswith("sha256:")
    replay = service.repository.append_submission(submission)
    assert replay == submission


def test_submission_excludes_other_party_private_evidence(service):
    created = service.create_day(day(), idempotency_key="create-1")
    service.add_evidence(
        tenant_id="T-1", project_id="P-1", claim_day_id=created.claim_day_id,
        evidence=evidence(), expected_revision=1, idempotency_key="evidence-1",
    )
    submission = service.submit(
        tenant_id="T-1", project_id="P-1", contract_id="C-1", claim_id="CL-1",
        submission_id="SUB-EMP", submission_number=1,
        submitting_party_id="EMPLOYER", submitted_by="u-employer",
        submitted_at="2026-10-26T08:00:00Z",
        form_template_id="FORM-CLAIM", form_template_version="v1",
        form_snapshot={"position": "employer response"},
        claim_day_ids=(created.claim_day_id,),
    )
    assert '"evidence":[]' in submission.manifest_json


def test_submission_rejects_day_from_another_claim_scope(service):
    created = service.create_day(day(), idempotency_key="create-1")
    with pytest.raises(ClaimDayArchiveError, match="SCOPE_MISMATCH"):
        service.submit(
            tenant_id="T-1", project_id="P-1", contract_id="C-1", claim_id="CL-OTHER",
            submission_id="SUB-1", submission_number=1,
            submitting_party_id="CONTRACTOR", submitted_by="u-contractor",
            submitted_at="2026-10-26T08:00:00Z",
            form_template_id="FORM-EOT", form_template_version="v1",
            form_snapshot={}, claim_day_ids=(created.claim_day_id,),
        )


def test_idempotency_key_reuse_with_changed_archive_is_rejected():
    repository = InMemoryClaimDayArchiveRepository()
    repository.put_day(day(), expected_revision=0, idempotency_key="same")
    with pytest.raises(ClaimDayIdempotencyConflict):
        repository.put_day(
            day(claim_day_id="other-day"), expected_revision=0, idempotency_key="same"
        )


def test_day_timezone_and_evidence_hash_are_validated():
    with pytest.raises(ClaimDayArchiveError, match="TIMEZONE"):
        day(timezone="Not/A_Zone").validate()
    with pytest.raises(ClaimDayArchiveError, match="SHA256"):
        evidence(content_sha256="sha256:bad").validate(
            claim_party_ids=("EMPLOYER", "CONTRACTOR", "CONSULTANT")
        )
