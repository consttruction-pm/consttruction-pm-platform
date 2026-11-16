from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime, time, timedelta, timezone
from enum import Enum
from hashlib import sha256
import json
import re
from typing import Any, Mapping, Protocol
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


CLAIM_DAY_ARCHIVE_CONTRACT_VERSION = "claim-day-archive.v1"
CLAIM_SUBMISSION_CONTRACT_VERSION = "claim-submission.v1"
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class ClaimDayArchiveError(ValueError):
    """Invalid claim-day archive data or operation."""


class ClaimDayRevisionConflict(ClaimDayArchiveError):
    """The aggregate revision changed since the caller read it."""


class ClaimDayIdempotencyConflict(ClaimDayArchiveError):
    """An idempotency key was reused for a different command."""


class ClaimDayVisibility(str, Enum):
    PRIVATE = "private"
    CLAIM_PARTIES = "claim_parties"
    EXPLICIT_PARTIES = "explicit_parties"


def _require_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ClaimDayArchiveError(f"INVALID_{field.upper()}")
    return value.strip()


def _aware_datetime(value: str, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ClaimDayArchiveError(f"INVALID_{field.upper()}")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError) as exc:
        raise ClaimDayArchiveError(f"INVALID_{field.upper()}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ClaimDayArchiveError(f"{field.upper()}_MUST_BE_TIMEZONE_AWARE")
    return parsed


def _canonical_json(value: object) -> str:
    try:
        return json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
        )
    except (TypeError, ValueError) as exc:
        raise ClaimDayArchiveError("INVALID_CANONICAL_JSON") from exc


def _digest(value: str) -> str:
    return "sha256:" + sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ClaimDayEvidenceLink:
    """A revision-pinned pointer to an authoritative CUBI source record.

    This object never owns the source bytes. Document Management, Field Daily
    Log and Engineering remain authoritative for their respective records.
    """

    evidence_link_id: str
    source_system: str
    source_type: str
    source_id: str
    source_revision: int
    source_content_version: str
    actor_id: str
    effective_at: str
    party_visibility: ClaimDayVisibility
    owner_party_id: str
    audience_party_ids: tuple[str, ...] = ()
    content_sha256: str | None = None
    captured_at: str | None = None
    captured_timezone: str | None = None
    server_received_at: str | None = None
    location_key: str | None = None
    work_front: str | None = None
    activity_refs: tuple[str, ...] = ()
    wbs_refs: tuple[str, ...] = ()
    delay_event_refs: tuple[str, ...] = ()
    chain_of_custody_refs: tuple[str, ...] = ()
    supersedes_evidence_link_id: str | None = None
    correction_reason: str | None = None

    def validate(self, *, claim_party_ids: tuple[str, ...]) -> None:
        for field_name in (
            "evidence_link_id", "source_system", "source_type", "source_id",
            "source_content_version", "actor_id", "owner_party_id",
        ):
            _require_text(getattr(self, field_name), field_name)
        if isinstance(self.source_revision, bool) or not isinstance(self.source_revision, int) or self.source_revision < 1:
            raise ClaimDayArchiveError("INVALID_SOURCE_REVISION")
        _aware_datetime(self.effective_at, "effective_at")
        if self.captured_at is not None:
            _aware_datetime(self.captured_at, "captured_at")
        if self.server_received_at is not None:
            _aware_datetime(self.server_received_at, "server_received_at")
        if self.captured_timezone is not None:
            _require_text(self.captured_timezone, "captured_timezone")
            try:
                ZoneInfo(self.captured_timezone)
            except ZoneInfoNotFoundError as exc:
                raise ClaimDayArchiveError("INVALID_CAPTURE_TIMEZONE") from exc
        if not isinstance(self.content_sha256, str) or not _SHA256_RE.fullmatch(self.content_sha256):
            raise ClaimDayArchiveError("INVALID_EVIDENCE_SHA256")
        if self.owner_party_id not in claim_party_ids:
            raise ClaimDayArchiveError("EVIDENCE_OWNER_NOT_A_CLAIM_PARTY")
        if not isinstance(self.party_visibility, ClaimDayVisibility):
            raise ClaimDayArchiveError("INVALID_EVIDENCE_VISIBILITY")
        if self.party_visibility is ClaimDayVisibility.PRIVATE and self.audience_party_ids:
            raise ClaimDayArchiveError("PRIVATE_EVIDENCE_CANNOT_HAVE_AUDIENCE")
        if self.party_visibility is ClaimDayVisibility.CLAIM_PARTIES and self.audience_party_ids:
            raise ClaimDayArchiveError("CLAIM_PARTY_EVIDENCE_CANNOT_HAVE_EXPLICIT_AUDIENCE")
        if self.party_visibility is ClaimDayVisibility.EXPLICIT_PARTIES:
            if not self.audience_party_ids:
                raise ClaimDayArchiveError("EXPLICIT_EVIDENCE_AUDIENCE_REQUIRED")
            if any(party not in claim_party_ids for party in self.audience_party_ids):
                raise ClaimDayArchiveError("EVIDENCE_AUDIENCE_NOT_A_CLAIM_PARTY")
        if self.supersedes_evidence_link_id is not None:
            _require_text(self.supersedes_evidence_link_id, "supersedes_evidence_link_id")
            _require_text(self.correction_reason, "correction_reason")
        elif self.correction_reason is not None:
            raise ClaimDayArchiveError("CORRECTION_REASON_REQUIRES_SUPERSEDED_EVIDENCE")
        for values in (self.activity_refs, self.wbs_refs, self.delay_event_refs, self.chain_of_custody_refs):
            if not isinstance(values, tuple) or any(not isinstance(item, str) or not item.strip() for item in values):
                raise ClaimDayArchiveError("INVALID_EVIDENCE_REFERENCES")

    def visible_to(self, party_id: str) -> bool:
        # Explicit disclosure is an exact allow-list: the owner retains access
        # only when included in the disclosed audience. PRIVATE remains owner-only.
        if self.party_visibility is ClaimDayVisibility.PRIVATE:
            return party_id == self.owner_party_id
        if self.party_visibility is ClaimDayVisibility.CLAIM_PARTIES:
            return True
        if self.party_visibility is ClaimDayVisibility.EXPLICIT_PARTIES:
            return party_id in self.audience_party_ids
        return False

    def manifest_entry(self) -> dict[str, object]:
        return {
            "evidence_link_id": self.evidence_link_id,
            "source_system": self.source_system,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "source_revision": self.source_revision,
            "source_content_version": self.source_content_version,
            "content_sha256": self.content_sha256,
            "effective_at": self.effective_at,
            "captured_at": self.captured_at,
            "captured_timezone": self.captured_timezone,
            "server_received_at": self.server_received_at,
            "actor_id": self.actor_id,
            "owner_party_id": self.owner_party_id,
            "party_visibility": self.party_visibility.value,
            "audience_party_ids": sorted(self.audience_party_ids),
            "location_key": self.location_key,
            "work_front": self.work_front,
            "activity_refs": sorted(self.activity_refs),
            "wbs_refs": sorted(self.wbs_refs),
            "delay_event_refs": sorted(self.delay_event_refs),
            "chain_of_custody_refs": sorted(self.chain_of_custody_refs),
            "supersedes_evidence_link_id": self.supersedes_evidence_link_id,
            "correction_reason": self.correction_reason,
        }


@dataclass(frozen=True)
class ClaimDayArchive:
    tenant_id: str
    project_id: str
    contract_id: str
    claim_id: str
    claim_day_id: str
    reporting_date: date
    timezone: str
    claim_party_ids: tuple[str, ...]
    revision_actor_id: str
    revision_occurred_at: str
    revision_reason: str
    revision: int = 1
    delay_event_ids: tuple[str, ...] = ()
    evidence_links: tuple[ClaimDayEvidenceLink, ...] = ()
    contract_version: str = CLAIM_DAY_ARCHIVE_CONTRACT_VERSION

    def validate(self) -> None:
        for name in ("tenant_id", "project_id", "contract_id", "claim_id", "claim_day_id"):
            _require_text(getattr(self, name), name)
        if self.contract_version != CLAIM_DAY_ARCHIVE_CONTRACT_VERSION:
            raise ClaimDayArchiveError("UNSUPPORTED_CLAIM_DAY_ARCHIVE_CONTRACT_VERSION")
        if not isinstance(self.reporting_date, date) or isinstance(self.reporting_date, datetime):
            raise ClaimDayArchiveError("INVALID_REPORTING_DATE")
        try:
            ZoneInfo(self.timezone)
        except (TypeError, ZoneInfoNotFoundError) as exc:
            raise ClaimDayArchiveError("INVALID_REPORTING_TIMEZONE") from exc
        if isinstance(self.revision, bool) or not isinstance(self.revision, int) or self.revision < 1:
            raise ClaimDayArchiveError("INVALID_CLAIM_DAY_REVISION")
        _require_text(self.revision_actor_id, "revision_actor_id")
        _aware_datetime(self.revision_occurred_at, "revision_occurred_at")
        _require_text(self.revision_reason, "revision_reason")
        if (
            not isinstance(self.claim_party_ids, tuple)
            or not self.claim_party_ids
            or len(set(self.claim_party_ids)) != len(self.claim_party_ids)
        ):
            raise ClaimDayArchiveError("INVALID_CLAIM_PARTIES")
        for party_id in self.claim_party_ids:
            _require_text(party_id, "claim_party_id")
        for event_id in self.delay_event_ids:
            _require_text(event_id, "delay_event_id")
        ids: dict[str, ClaimDayEvidenceLink] = {}
        for link in self.evidence_links:
            link.validate(claim_party_ids=self.claim_party_ids)
            if link.evidence_link_id in ids:
                raise ClaimDayArchiveError("DUPLICATE_EVIDENCE_LINK_ID")
            if link.supersedes_evidence_link_id is not None:
                previous = ids.get(link.supersedes_evidence_link_id)
                if previous is None:
                    raise ClaimDayArchiveError("SUPERSEDED_EVIDENCE_NOT_FOUND")
                if (
                    (previous.source_system, previous.source_type, previous.source_id)
                    != (link.source_system, link.source_type, link.source_id)
                    or link.source_revision <= previous.source_revision
                ):
                    raise ClaimDayArchiveError("INVALID_EVIDENCE_CORRECTION_CHAIN")
            ids[link.evidence_link_id] = link

    @property
    def day_start(self) -> datetime:
        self.validate()
        return datetime.combine(self.reporting_date, time.min, ZoneInfo(self.timezone))

    @property
    def day_end(self) -> datetime:
        self.validate()
        next_day = self.reporting_date + timedelta(days=1)
        return datetime.combine(next_day, time.min, ZoneInfo(self.timezone))

    @property
    def day_start_utc(self) -> str:
        return self.day_start.astimezone(timezone.utc).isoformat()

    @property
    def day_end_utc(self) -> str:
        return self.day_end.astimezone(timezone.utc).isoformat()

    def add_evidence(self, link: ClaimDayEvidenceLink) -> "ClaimDayArchive":
        self.validate()
        link.validate(claim_party_ids=self.claim_party_ids)
        if any(item.evidence_link_id == link.evidence_link_id for item in self.evidence_links):
            raise ClaimDayArchiveError("DUPLICATE_EVIDENCE_LINK_ID")
        updated = replace(
            self,
            revision=self.revision + 1,
            revision_actor_id=link.actor_id,
            revision_occurred_at=link.server_received_at or link.captured_at or link.effective_at,
            revision_reason=(
                f"Evidence correction: {link.correction_reason}"
                if link.supersedes_evidence_link_id is not None
                else f"Evidence linked: {link.evidence_link_id}"
            ),
            evidence_links=(*self.evidence_links, link),
        )
        updated.validate()
        return updated

    def visible_evidence(self, party_id: str) -> tuple[ClaimDayEvidenceLink, ...]:
        if party_id not in self.claim_party_ids:
            raise ClaimDayArchiveError("PARTY_NOT_ASSIGNED_TO_CLAIM")
        return tuple(link for link in self.evidence_links if link.visible_to(party_id))

    def as_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "contract_version": self.contract_version,
            "tenant_id": self.tenant_id,
            "project_id": self.project_id,
            "contract_id": self.contract_id,
            "claim_id": self.claim_id,
            "claim_day_id": self.claim_day_id,
            "reporting_date": self.reporting_date.isoformat(),
            "timezone": self.timezone,
            "day_start_utc": self.day_start_utc,
            "day_end_utc": self.day_end_utc,
            "claim_party_ids": list(self.claim_party_ids),
            "revision_actor_id": self.revision_actor_id,
            "revision_occurred_at": self.revision_occurred_at,
            "revision_reason": self.revision_reason,
            "revision": self.revision,
            "delay_event_ids": list(self.delay_event_ids),
            "evidence_links": [item.manifest_entry() for item in self.evidence_links],
        }


@dataclass(frozen=True)
class ClaimSubmission:
    tenant_id: str
    project_id: str
    contract_id: str
    claim_id: str
    submission_id: str
    submission_number: int
    submitting_party_id: str
    submitted_by: str
    submitted_at: str
    form_template_id: str
    form_template_version: str
    form_snapshot_json: str
    form_snapshot_sha256: str
    manifest_json: str
    manifest_sha256: str
    schedule_snapshot_ids: tuple[str, ...] = ()
    baseline_snapshot_ids: tuple[str, ...] = ()
    supersedes_submission_id: str | None = None
    contract_version: str = CLAIM_SUBMISSION_CONTRACT_VERSION

    @classmethod
    def build(
        cls,
        *,
        tenant_id: str,
        project_id: str,
        contract_id: str,
        claim_id: str,
        submission_id: str,
        submission_number: int,
        submitting_party_id: str,
        submitted_by: str,
        submitted_at: str,
        form_template_id: str,
        form_template_version: str,
        form_snapshot: Mapping[str, object],
        evidence_links: tuple[tuple[str, ClaimDayEvidenceLink], ...],
        claim_days: tuple[ClaimDayArchive, ...],
        schedule_snapshot_ids: tuple[str, ...] = (),
        baseline_snapshot_ids: tuple[str, ...] = (),
        supersedes_submission_id: str | None = None,
    ) -> "ClaimSubmission":
        _aware_datetime(submitted_at, "submitted_at")
        form_json = _canonical_json(dict(form_snapshot))
        manifest = {
            "contract_version": CLAIM_SUBMISSION_CONTRACT_VERSION,
            "tenant_id": tenant_id,
            "project_id": project_id,
            "contract_id": contract_id,
            "claim_id": claim_id,
            "submission_id": submission_id,
            "submission_number": submission_number,
            "submitting_party_id": submitting_party_id,
            "submitted_by": submitted_by,
            "form_template_id": form_template_id,
            "form_template_version": form_template_version,
            "form_snapshot_sha256": _digest(form_json),
            "claim_days": sorted(
                (
                    {
                        "claim_day_id": item.claim_day_id,
                        "reporting_date": item.reporting_date.isoformat(),
                        "timezone": item.timezone,
                        "revision": item.revision,
                        "revision_actor_id": item.revision_actor_id,
                        "revision_occurred_at": item.revision_occurred_at,
                        "revision_reason": item.revision_reason,
                        "day_start_utc": item.day_start_utc,
                        "day_end_utc": item.day_end_utc,
                        "delay_event_ids": sorted(item.delay_event_ids),
                    }
                    for item in claim_days
                ),
                key=lambda item: str(item["claim_day_id"]),
            ),
            "evidence": sorted(
                (
                    {"claim_day_id": claim_day_id, **link.manifest_entry()}
                    for claim_day_id, link in evidence_links
                ),
                key=lambda item: (str(item["claim_day_id"]), str(item["evidence_link_id"])),
            ),
            "schedule_snapshot_ids": sorted(schedule_snapshot_ids),
            "baseline_snapshot_ids": sorted(baseline_snapshot_ids),
            "submitted_at": submitted_at,
            "supersedes_submission_id": supersedes_submission_id,
        }
        manifest_json = _canonical_json(manifest)
        result = cls(
            tenant_id=tenant_id, project_id=project_id, contract_id=contract_id,
            claim_id=claim_id, submission_id=submission_id,
            submission_number=submission_number, submitting_party_id=submitting_party_id,
            submitted_by=submitted_by, submitted_at=submitted_at,
            form_template_id=form_template_id, form_template_version=form_template_version,
            form_snapshot_json=form_json, form_snapshot_sha256=_digest(form_json),
            manifest_json=manifest_json, manifest_sha256=_digest(manifest_json),
            schedule_snapshot_ids=tuple(schedule_snapshot_ids),
            baseline_snapshot_ids=tuple(baseline_snapshot_ids),
            supersedes_submission_id=supersedes_submission_id,
        )
        result.validate()
        return result

    def validate(self) -> None:
        for name in (
            "tenant_id", "project_id", "contract_id", "claim_id", "submission_id",
            "submitting_party_id", "submitted_by", "form_template_id", "form_template_version",
        ):
            _require_text(getattr(self, name), name)
        _aware_datetime(self.submitted_at, "submitted_at")
        if self.contract_version != CLAIM_SUBMISSION_CONTRACT_VERSION:
            raise ClaimDayArchiveError("UNSUPPORTED_CLAIM_SUBMISSION_CONTRACT_VERSION")
        if isinstance(self.submission_number, bool) or not isinstance(self.submission_number, int) or self.submission_number < 1:
            raise ClaimDayArchiveError("INVALID_CLAIM_SUBMISSION_NUMBER")
        if _digest(self.form_snapshot_json) != self.form_snapshot_sha256:
            raise ClaimDayArchiveError("CLAIM_SUBMISSION_FORM_SNAPSHOT_HASH_MISMATCH")
        if _digest(self.manifest_json) != self.manifest_sha256:
            raise ClaimDayArchiveError("CLAIM_SUBMISSION_MANIFEST_HASH_MISMATCH")
        try:
            json.loads(self.form_snapshot_json)
            manifest = json.loads(self.manifest_json)
        except (TypeError, ValueError) as exc:
            raise ClaimDayArchiveError("INVALID_CLAIM_SUBMISSION_SNAPSHOT") from exc
        if not isinstance(manifest, dict):
            raise ClaimDayArchiveError("INVALID_CLAIM_SUBMISSION_MANIFEST")
        expected_manifest_fields = {
            "contract_version": self.contract_version,
            "tenant_id": self.tenant_id,
            "project_id": self.project_id,
            "contract_id": self.contract_id,
            "claim_id": self.claim_id,
            "submission_id": self.submission_id,
            "submission_number": self.submission_number,
            "submitting_party_id": self.submitting_party_id,
            "submitted_by": self.submitted_by,
            "submitted_at": self.submitted_at,
            "form_template_id": self.form_template_id,
            "form_template_version": self.form_template_version,
            "form_snapshot_sha256": self.form_snapshot_sha256,
            "schedule_snapshot_ids": sorted(self.schedule_snapshot_ids),
            "baseline_snapshot_ids": sorted(self.baseline_snapshot_ids),
            "supersedes_submission_id": self.supersedes_submission_id,
        }
        if any(manifest.get(key) != value for key, value in expected_manifest_fields.items()):
            raise ClaimDayArchiveError("CLAIM_SUBMISSION_MANIFEST_FIELDS_MISMATCH")
        if self.supersedes_submission_id is not None:
            _require_text(self.supersedes_submission_id, "supersedes_submission_id")
        for item in (*self.schedule_snapshot_ids, *self.baseline_snapshot_ids):
            _require_text(item, "schedule_or_baseline_snapshot_id")


class ClaimDayArchiveRepository(Protocol):
    def get_day(self, tenant_id: str, project_id: str, claim_day_id: str) -> ClaimDayArchive | None: ...
    def get_day_revision(self, tenant_id: str, project_id: str, claim_day_id: str, revision: int) -> ClaimDayArchive | None: ...
    def put_day(self, day: ClaimDayArchive, *, expected_revision: int, idempotency_key: str) -> ClaimDayArchive: ...
    def append_submission(self, submission: ClaimSubmission) -> ClaimSubmission: ...
    def get_submission(self, tenant_id: str, project_id: str, submission_id: str) -> ClaimSubmission | None: ...


class InMemoryClaimDayArchiveRepository:
    """Deterministic repository used by domain tests and local preview composition."""

    def __init__(self) -> None:
        self.days: dict[tuple[str, str, str], ClaimDayArchive] = {}
        self.day_revisions: dict[tuple[str, str, str, int], ClaimDayArchive] = {}
        self.submissions: dict[tuple[str, str, str], ClaimSubmission] = {}
        self.idempotency: dict[tuple[str, str, str], tuple[str, ClaimDayArchive]] = {}

    def get_day(self, tenant_id: str, project_id: str, claim_day_id: str) -> ClaimDayArchive | None:
        return self.days.get((tenant_id, project_id, claim_day_id))

    def get_day_revision(self, tenant_id: str, project_id: str, claim_day_id: str, revision: int) -> ClaimDayArchive | None:
        return self.day_revisions.get((tenant_id, project_id, claim_day_id, revision))

    def put_day(
        self, day: ClaimDayArchive, *, expected_revision: int, idempotency_key: str
    ) -> ClaimDayArchive:
        day.validate()
        _require_text(idempotency_key, "idempotency_key")
        key = (day.tenant_id, day.project_id, idempotency_key)
        fingerprint = _digest(_canonical_json(day.as_dict()))
        replay = self.idempotency.get(key)
        if replay is not None:
            if replay[0] != fingerprint:
                raise ClaimDayIdempotencyConflict("CLAIM_DAY_IDEMPOTENCY_KEY_REUSE")
            return replay[1]
        aggregate_key = (day.tenant_id, day.project_id, day.claim_day_id)
        current = self.days.get(aggregate_key)
        actual_revision = 0 if current is None else current.revision
        if actual_revision != expected_revision:
            raise ClaimDayRevisionConflict("CLAIM_DAY_REVISION_CONFLICT")
        if current is not None:
            _validate_day_append_only(current, day)
            if day.revision != current.revision + 1:
                raise ClaimDayRevisionConflict("CLAIM_DAY_REVISION_CONFLICT")
        elif day.revision != 1:
            raise ClaimDayRevisionConflict("CLAIM_DAY_INITIAL_REVISION_MUST_BE_ONE")
        self.days[aggregate_key] = day
        self.day_revisions[(day.tenant_id, day.project_id, day.claim_day_id, day.revision)] = day
        self.idempotency[key] = (fingerprint, day)
        return day

    def append_submission(self, submission: ClaimSubmission) -> ClaimSubmission:
        submission.validate()
        key = (submission.tenant_id, submission.project_id, submission.submission_id)
        if key in self.submissions:
            existing = self.submissions[key]
            if existing != submission:
                raise ClaimDayArchiveError("CLAIM_SUBMISSION_ID_IMMUTABLE")
            return existing
        claim_submissions = [
            item for item in self.submissions.values()
            if (item.tenant_id, item.project_id, item.contract_id, item.claim_id)
            == (submission.tenant_id, submission.project_id, submission.contract_id, submission.claim_id)
        ]
        # Match the PostgreSQL uniqueness scope: each submitting party has its
        # own submission-number sequence within a claim.
        party_submissions = [
            item for item in claim_submissions
            if item.submitting_party_id == submission.submitting_party_id
        ]
        if any(item.submission_number == submission.submission_number for item in party_submissions):
            raise ClaimDayArchiveError("CLAIM_SUBMISSION_NUMBER_ALREADY_EXISTS")
        if submission.supersedes_submission_id is not None and not any(
            item.submission_id == submission.supersedes_submission_id
            for item in party_submissions
        ):
            raise ClaimDayArchiveError("CLAIM_SUBMISSION_SUPERSEDED_PACKAGE_NOT_FOUND")
        self.submissions[key] = submission
        return submission

    def get_submission(
        self, tenant_id: str, project_id: str, submission_id: str
    ) -> ClaimSubmission | None:
        return self.submissions.get((tenant_id, project_id, submission_id))


@dataclass(frozen=True)
class ClaimDayArchiveService:
    repository: ClaimDayArchiveRepository

    def create_day(self, day: ClaimDayArchive, *, idempotency_key: str) -> ClaimDayArchive:
        day.validate()
        return self.repository.put_day(day, expected_revision=0, idempotency_key=idempotency_key)

    def add_evidence(
        self,
        *,
        tenant_id: str,
        project_id: str,
        claim_day_id: str,
        evidence: ClaimDayEvidenceLink,
        expected_revision: int,
        idempotency_key: str,
    ) -> ClaimDayArchive:
        current = self.repository.get_day(tenant_id, project_id, claim_day_id)
        if current is None:
            raise ClaimDayArchiveError("CLAIM_DAY_NOT_FOUND")
        if current.revision != expected_revision:
            raise ClaimDayRevisionConflict("CLAIM_DAY_REVISION_CONFLICT")
        updated = current.add_evidence(evidence)
        return self.repository.put_day(updated, expected_revision=expected_revision, idempotency_key=idempotency_key)

    def submit(
        self,
        *,
        tenant_id: str,
        project_id: str,
        contract_id: str,
        claim_id: str,
        submission_id: str,
        submission_number: int,
        submitting_party_id: str,
        submitted_by: str,
        submitted_at: str,
        form_template_id: str,
        form_template_version: str,
        form_snapshot: Mapping[str, object],
        claim_day_ids: tuple[str, ...],
        schedule_snapshot_ids: tuple[str, ...] = (),
        baseline_snapshot_ids: tuple[str, ...] = (),
        supersedes_submission_id: str | None = None,
    ) -> ClaimSubmission:
        if not claim_day_ids:
            raise ClaimDayArchiveError("CLAIM_SUBMISSION_REQUIRES_CLAIM_DAYS")
        days: list[ClaimDayArchive] = []
        for claim_day_id in claim_day_ids:
            day = self.repository.get_day(tenant_id, project_id, claim_day_id)
            if day is None or day.claim_id != claim_id or day.contract_id != contract_id:
                raise ClaimDayArchiveError("CLAIM_SUBMISSION_DAY_SCOPE_MISMATCH")
            if submitting_party_id not in day.claim_party_ids:
                raise ClaimDayArchiveError("CLAIM_SUBMITTER_NOT_A_CLAIM_PARTY")
            days.append(day)
        evidence = tuple(
            (day.claim_day_id, link)
            for day in days
            for link in day.visible_evidence(submitting_party_id)
        )
        submission = ClaimSubmission.build(
            tenant_id=tenant_id, project_id=project_id, contract_id=contract_id,
            claim_id=claim_id, submission_id=submission_id,
            submission_number=submission_number, submitting_party_id=submitting_party_id,
            submitted_by=submitted_by, submitted_at=submitted_at,
            form_template_id=form_template_id, form_template_version=form_template_version,
            form_snapshot=form_snapshot, evidence_links=evidence,
            claim_days=tuple(days),
            schedule_snapshot_ids=schedule_snapshot_ids,
            baseline_snapshot_ids=baseline_snapshot_ids,
            supersedes_submission_id=supersedes_submission_id,
        )
        return self.repository.append_submission(submission)


class ClaimDayArchiveConnection(Protocol):
    def execute(self, sql: str, params: tuple[Any, ...] = ()): ...
    def transaction(self): ...


def _day_from_json(payload: str) -> ClaimDayArchive:
    data = json.loads(payload)
    links = tuple(
        ClaimDayEvidenceLink(
            evidence_link_id=item["evidence_link_id"],
            source_system=item["source_system"],
            source_type=item["source_type"],
            source_id=item["source_id"],
            source_revision=int(item["source_revision"]),
            source_content_version=item["source_content_version"],
            actor_id=item["actor_id"],
            effective_at=item["effective_at"],
            party_visibility=ClaimDayVisibility(item["party_visibility"]),
            owner_party_id=item["owner_party_id"],
            audience_party_ids=tuple(item.get("audience_party_ids", ())),
            content_sha256=item.get("content_sha256"),
            captured_at=item.get("captured_at"),
            captured_timezone=item.get("captured_timezone"),
            server_received_at=item.get("server_received_at"),
            location_key=item.get("location_key"),
            work_front=item.get("work_front"),
            activity_refs=tuple(item.get("activity_refs", ())),
            wbs_refs=tuple(item.get("wbs_refs", ())),
            delay_event_refs=tuple(item.get("delay_event_refs", ())),
            chain_of_custody_refs=tuple(item.get("chain_of_custody_refs", ())),
            supersedes_evidence_link_id=item.get("supersedes_evidence_link_id"),
            correction_reason=item.get("correction_reason"),
        )
        for item in data["evidence_links"]
    )
    result = ClaimDayArchive(
        tenant_id=data["tenant_id"],
        project_id=data["project_id"],
        contract_id=data["contract_id"],
        claim_id=data["claim_id"],
        claim_day_id=data["claim_day_id"],
        reporting_date=date.fromisoformat(data["reporting_date"]),
        timezone=data["timezone"],
        claim_party_ids=tuple(data["claim_party_ids"]),
        revision_actor_id=data["revision_actor_id"],
        revision_occurred_at=data["revision_occurred_at"],
        revision_reason=data["revision_reason"],
        revision=int(data["revision"]),
        delay_event_ids=tuple(data.get("delay_event_ids", ())),
        evidence_links=links,
        contract_version=data["contract_version"],
    )
    result.validate()
    return result


def _submission_json(submission: ClaimSubmission) -> str:
    return _canonical_json({
        "tenant_id": submission.tenant_id,
        "project_id": submission.project_id,
        "contract_id": submission.contract_id,
        "claim_id": submission.claim_id,
        "submission_id": submission.submission_id,
        "submission_number": submission.submission_number,
        "submitting_party_id": submission.submitting_party_id,
        "submitted_by": submission.submitted_by,
        "submitted_at": submission.submitted_at,
        "form_template_id": submission.form_template_id,
        "form_template_version": submission.form_template_version,
        "form_snapshot_json": submission.form_snapshot_json,
        "form_snapshot_sha256": submission.form_snapshot_sha256,
        "manifest_json": submission.manifest_json,
        "manifest_sha256": submission.manifest_sha256,
        "schedule_snapshot_ids": list(submission.schedule_snapshot_ids),
        "baseline_snapshot_ids": list(submission.baseline_snapshot_ids),
        "supersedes_submission_id": submission.supersedes_submission_id,
        "contract_version": submission.contract_version,
    })


def _submission_from_json(payload: str) -> ClaimSubmission:
    data = json.loads(payload)
    result = ClaimSubmission(
        **{
            **data,
            "schedule_snapshot_ids": tuple(data.get("schedule_snapshot_ids", ())),
            "baseline_snapshot_ids": tuple(data.get("baseline_snapshot_ids", ())),
        }
    )
    result.validate()
    return result


class PostgresClaimDayArchiveRepository:
    """PostgreSQL persistence for immutable claim-day and submission snapshots.

    This repository stores source references and canonical JSON snapshots only;
    it never duplicates Document Management binary content or Engineering data.
    """

    def __init__(self, connection: ClaimDayArchiveConnection) -> None:
        self.connection = connection

    def initialize(self) -> None:
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS claim_day_archives (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                claim_day_id TEXT NOT NULL,
                claim_id TEXT NOT NULL,
                contract_id TEXT NOT NULL,
                revision BIGINT NOT NULL,
                day_json TEXT NOT NULL,
                PRIMARY KEY (tenant_id, project_id, claim_day_id)
            )"""
        )
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS claim_day_archive_revisions (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                claim_day_id TEXT NOT NULL,
                revision BIGINT NOT NULL,
                day_json TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (tenant_id, project_id, claim_day_id, revision)
            )"""
        )
        self.connection.execute(
            """CREATE OR REPLACE FUNCTION claim_day_archive_revision_immutable()
               RETURNS trigger
               LANGUAGE plpgsql
               AS 'BEGIN
                   RAISE EXCEPTION ''CLAIM_DAY_ARCHIVE_REVISION_IMMUTABLE'';
               END;'"""
        )
        self.connection.execute(
            "DROP TRIGGER IF EXISTS claim_day_archive_revision_no_mutation ON claim_day_archive_revisions"
        )
        self.connection.execute(
            """CREATE TRIGGER claim_day_archive_revision_no_mutation
               BEFORE UPDATE OR DELETE ON claim_day_archive_revisions
               FOR EACH ROW EXECUTE FUNCTION claim_day_archive_revision_immutable()"""
        )
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS claim_day_archive_idempotency (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                idempotency_key TEXT NOT NULL,
                fingerprint TEXT NOT NULL,
                result_json TEXT NOT NULL,
                PRIMARY KEY (tenant_id, project_id, idempotency_key)
            )"""
        )
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS claim_submissions (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                submission_id TEXT NOT NULL,
                contract_id TEXT NOT NULL,
                claim_id TEXT NOT NULL,
                submitting_party_id TEXT NOT NULL,
                submission_number BIGINT NOT NULL,
                manifest_sha256 TEXT NOT NULL,
                submission_json TEXT NOT NULL,
                PRIMARY KEY (tenant_id, project_id, submission_id),
                UNIQUE (tenant_id, project_id, contract_id, claim_id, submitting_party_id, submission_number)
            )"""
        )
        self.connection.execute(
            """CREATE OR REPLACE FUNCTION claim_submission_immutable()
               RETURNS trigger
               LANGUAGE plpgsql
               AS 'BEGIN
                   RAISE EXCEPTION ''CLAIM_SUBMISSION_IMMUTABLE'';
               END;'"""
        )
        self.connection.execute(
            "DROP TRIGGER IF EXISTS claim_submission_no_mutation ON claim_submissions"
        )
        self.connection.execute(
            """CREATE TRIGGER claim_submission_no_mutation
               BEFORE UPDATE OR DELETE ON claim_submissions
               FOR EACH ROW EXECUTE FUNCTION claim_submission_immutable()"""
        )

    def get_day_revision(
        self, tenant_id: str, project_id: str, claim_day_id: str, revision: int
    ) -> ClaimDayArchive | None:
        row = self.connection.execute(
            "SELECT day_json FROM claim_day_archive_revisions "
            "WHERE tenant_id=%s AND project_id=%s AND claim_day_id=%s AND revision=%s",
            (tenant_id, project_id, claim_day_id, revision),
        ).fetchone()
        return None if row is None else _day_from_json(row[0])

    def get_day(
        self, tenant_id: str, project_id: str, claim_day_id: str
    ) -> ClaimDayArchive | None:
        row = self.connection.execute(
            "SELECT day_json FROM claim_day_archives "
            "WHERE tenant_id=%s AND project_id=%s AND claim_day_id=%s",
            (tenant_id, project_id, claim_day_id),
        ).fetchone()
        return None if row is None else _day_from_json(row[0])

    def put_day(
        self,
        day: ClaimDayArchive,
        *,
        expected_revision: int,
        idempotency_key: str,
    ) -> ClaimDayArchive:
        day.validate()
        _require_text(idempotency_key, "idempotency_key")
        fingerprint = _digest(_canonical_json(day.as_dict()))
        with self.connection.transaction():
            replay = self.connection.execute(
                "SELECT fingerprint, result_json FROM claim_day_archive_idempotency "
                "WHERE tenant_id=%s AND project_id=%s AND idempotency_key=%s",
                (day.tenant_id, day.project_id, idempotency_key),
            ).fetchone()
            if replay is not None:
                if replay[0] != fingerprint:
                    raise ClaimDayIdempotencyConflict("CLAIM_DAY_IDEMPOTENCY_KEY_REUSE")
                return _day_from_json(replay[1])

            row = self.connection.execute(
                "SELECT day_json, revision FROM claim_day_archives "
                "WHERE tenant_id=%s AND project_id=%s AND claim_day_id=%s FOR UPDATE",
                (day.tenant_id, day.project_id, day.claim_day_id),
            ).fetchone()
            current = None if row is None else _day_from_json(row[0])
            actual_revision = 0 if row is None else int(row[1])
            if actual_revision != expected_revision:
                raise ClaimDayRevisionConflict("CLAIM_DAY_REVISION_CONFLICT")
            if current is None:
                if day.revision != 1:
                    raise ClaimDayRevisionConflict("CLAIM_DAY_INITIAL_REVISION_MUST_BE_ONE")
            else:
                _validate_day_append_only(current, day)
                if day.revision != current.revision + 1:
                    raise ClaimDayRevisionConflict("CLAIM_DAY_REVISION_CONFLICT")

            serialized = _canonical_json(day.as_dict())
            self.connection.execute(
                """INSERT INTO claim_day_archives
                   (tenant_id, project_id, claim_day_id, claim_id, contract_id, revision, day_json)
                   VALUES (%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT (tenant_id, project_id, claim_day_id)
                   DO UPDATE SET claim_id=EXCLUDED.claim_id,
                                 contract_id=EXCLUDED.contract_id,
                                 revision=EXCLUDED.revision,
                                 day_json=EXCLUDED.day_json""",
                (
                    day.tenant_id, day.project_id, day.claim_day_id, day.claim_id,
                    day.contract_id, day.revision, serialized,
                ),
            )
            self.connection.execute(
                """INSERT INTO claim_day_archive_revisions
                   (tenant_id, project_id, claim_day_id, revision, day_json)
                   VALUES (%s,%s,%s,%s,%s)""",
                (day.tenant_id, day.project_id, day.claim_day_id, day.revision, serialized),
            )
            self.connection.execute(
                "INSERT INTO claim_day_archive_idempotency "
                "(tenant_id, project_id, idempotency_key, fingerprint, result_json) "
                "VALUES (%s,%s,%s,%s,%s)",
                (day.tenant_id, day.project_id, idempotency_key, fingerprint, serialized),
            )
        return day

    def append_submission(self, submission: ClaimSubmission) -> ClaimSubmission:
        submission.validate()
        serialized = _submission_json(submission)
        with self.connection.transaction():
            existing = self.connection.execute(
                "SELECT submission_json FROM claim_submissions "
                "WHERE tenant_id=%s AND project_id=%s AND submission_id=%s",
                (submission.tenant_id, submission.project_id, submission.submission_id),
            ).fetchone()
            if existing is not None:
                previous = _submission_from_json(existing[0])
                if previous != submission:
                    raise ClaimDayArchiveError("CLAIM_SUBMISSION_ID_IMMUTABLE")
                return previous
            if submission.supersedes_submission_id is not None:
                superseded = self.connection.execute(
                    "SELECT submitting_party_id, contract_id, claim_id FROM claim_submissions "
                    "WHERE tenant_id=%s AND project_id=%s AND submission_id=%s",
                    (submission.tenant_id, submission.project_id, submission.supersedes_submission_id),
                ).fetchone()
                if superseded is None or tuple(superseded) != (
                    submission.submitting_party_id, submission.contract_id, submission.claim_id
                ):
                    raise ClaimDayArchiveError("CLAIM_SUBMISSION_SUPERSEDED_PACKAGE_NOT_FOUND")
            self.connection.execute(
                """INSERT INTO claim_submissions
                   (tenant_id, project_id, submission_id, contract_id, claim_id,
                    submitting_party_id, submission_number, manifest_sha256, submission_json)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    submission.tenant_id, submission.project_id, submission.submission_id,
                    submission.contract_id, submission.claim_id, submission.submitting_party_id,
                    submission.submission_number, submission.manifest_sha256, serialized,
                ),
            )
        return submission

    def get_submission(
        self, tenant_id: str, project_id: str, submission_id: str
    ) -> ClaimSubmission | None:
        row = self.connection.execute(
            "SELECT submission_json FROM claim_submissions "
            "WHERE tenant_id=%s AND project_id=%s AND submission_id=%s",
            (tenant_id, project_id, submission_id),
        ).fetchone()
        return None if row is None else _submission_from_json(row[0])


def _validate_day_append_only(current: ClaimDayArchive, updated: ClaimDayArchive) -> None:
    if (
        current.claim_id != updated.claim_id
        or current.contract_id != updated.contract_id
        or current.reporting_date != updated.reporting_date
        or current.timezone != updated.timezone
        or current.claim_party_ids != updated.claim_party_ids
    ):
        raise ClaimDayArchiveError("CLAIM_DAY_IDENTITY_IS_IMMUTABLE")
    if not set(current.delay_event_ids).issubset(set(updated.delay_event_ids)):
        raise ClaimDayArchiveError("CLAIM_DAY_EVENTS_CANNOT_BE_REMOVED")
    if updated.revision_reason == current.revision_reason:
        raise ClaimDayArchiveError("CLAIM_DAY_REVISION_REASON_REQUIRED")
    if _aware_datetime(updated.revision_occurred_at, "revision_occurred_at") < _aware_datetime(
        current.revision_occurred_at, "revision_occurred_at"
    ):
        raise ClaimDayArchiveError("CLAIM_DAY_REVISION_TIME_CANNOT_MOVE_BACKWARD")
    updated_by_id = {item.evidence_link_id: item for item in updated.evidence_links}
    for previous in current.evidence_links:
        if previous.evidence_link_id not in updated_by_id:
            raise ClaimDayArchiveError("CLAIM_DAY_EVIDENCE_CANNOT_BE_REMOVED")
        if updated_by_id[previous.evidence_link_id] != previous:
            raise ClaimDayArchiveError("CLAIM_DAY_EVIDENCE_CANNOT_BE_REWRITTEN")
