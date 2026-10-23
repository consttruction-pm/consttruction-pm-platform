from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class AILearningMemoryError(ValueError):
    """Raised when a learning-memory record violates its versioned contract."""


class LearningScope(str, Enum):
    USER_PRIVATE = "user_private"
    PROJECT_PRIVATE = "project_private"
    TENANT_SHARED = "tenant_shared"
    GENERAL_CANDIDATE = "general_candidate"
    GENERAL_PUBLISHED = "general_published"


class LearningStatus(str, Enum):
    CAPTURED = "captured"
    CANDIDATE = "candidate"
    VALIDATED = "validated"
    PUBLISHED = "published"
    REJECTED = "rejected"
    RETIRED = "retired"


class LearningSignalKind(str, Enum):
    USER_CORRECTION = "user_correction"
    USER_FEEDBACK = "user_feedback"
    OBSERVED_OUTCOME = "observed_outcome"
    ASSISTANT_MISUNDERSTANDING = "assistant_misunderstanding"
    PUBLIC_RESEARCH = "public_research"
    VALIDATION_TEST = "validation_test"
    ADMIN_CURATED = "admin_curated"


@dataclass(frozen=True)
class LearningRetrievalScope:
    """Trusted retrieval scope supplied by the application, never by model output."""

    user_id: str
    tenant_id: str | None = None
    project_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.user_id, str) or not self.user_id.strip():
            raise AILearningMemoryError("AI_LEARNING_AUTHENTICATED_USER_REQUIRED")
        for name, value in (("tenant_id", self.tenant_id), ("project_id", self.project_id)):
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise AILearningMemoryError(f"INVALID_AI_LEARNING_SCOPE_{name.upper()}")


@dataclass(frozen=True)
class AILearningMemoryRecord:
    """Versioned lesson/experience record without a raw transcript field.

    Persistence, tenant filtering, privacy scanning and authorization belong to
    the application/repository layer. This contract makes the intended scope and
    publication gates explicit; it is not a substitute for those runtime controls.
    """

    record_id: str
    record_version: int
    scope: LearningScope
    status: LearningStatus
    signal_kind: LearningSignalKind
    lesson: str
    conditions: str
    limitations: str
    evidence_refs: tuple[str, ...]
    captured_at: datetime
    updated_at: datetime
    owner_user_id: str | None = None
    tenant_id: str | None = None
    project_id: str | None = None
    user_expertise_level: str | None = None
    privacy_review_passed: bool = False
    consent_for_generalization: bool = False
    validation_evidence_refs: tuple[str, ...] = ()
    approved_by: str | None = None
    approved_at: datetime | None = None
    supersedes_record_id: str | None = None
    schema_version: str = "1.0"

    def __post_init__(self) -> None:
        if self.schema_version != "1.0":
            raise AILearningMemoryError("UNSUPPORTED_AI_LEARNING_MEMORY_SCHEMA")
        for name, value in (
            ("record_id", self.record_id),
            ("lesson", self.lesson),
            ("conditions", self.conditions),
            ("limitations", self.limitations),
        ):
            if not isinstance(value, str) or not value.strip():
                raise AILearningMemoryError(f"INVALID_AI_LEARNING_{name.upper()}")
        if isinstance(self.record_version, bool) or not isinstance(self.record_version, int) or self.record_version < 1:
            raise AILearningMemoryError("INVALID_AI_LEARNING_RECORD_VERSION")
        if not isinstance(self.scope, LearningScope):
            raise AILearningMemoryError("INVALID_AI_LEARNING_SCOPE")
        if not isinstance(self.status, LearningStatus):
            raise AILearningMemoryError("INVALID_AI_LEARNING_STATUS")
        if not isinstance(self.signal_kind, LearningSignalKind):
            raise AILearningMemoryError("INVALID_AI_LEARNING_SIGNAL_KIND")
        for name, value in (
            ("owner_user_id", self.owner_user_id),
            ("tenant_id", self.tenant_id),
            ("project_id", self.project_id),
            ("approved_by", self.approved_by),
            ("supersedes_record_id", self.supersedes_record_id),
            ("user_expertise_level", self.user_expertise_level),
        ):
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise AILearningMemoryError(f"INVALID_AI_LEARNING_{name.upper()}")
        for name, refs in (
            ("evidence_refs", self.evidence_refs),
            ("validation_evidence_refs", self.validation_evidence_refs),
        ):
            if not isinstance(refs, tuple) or any(not isinstance(ref, str) or not ref.strip() for ref in refs):
                raise AILearningMemoryError(f"INVALID_AI_LEARNING_{name.upper()}")
        if not self.evidence_refs:
            raise AILearningMemoryError("AI_LEARNING_EVIDENCE_REQUIRED")
        for name, value in (("captured_at", self.captured_at), ("updated_at", self.updated_at)):
            if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
                raise AILearningMemoryError(f"AI_LEARNING_{name.upper()}_MUST_BE_TIMEZONE_AWARE")
        if self.approved_at is not None and (
            not isinstance(self.approved_at, datetime)
            or self.approved_at.tzinfo is None
            or self.approved_at.utcoffset() is None
        ):
            raise AILearningMemoryError("AI_LEARNING_APPROVED_AT_MUST_BE_TIMEZONE_AWARE")

        self._validate_scope()
        self._validate_publication()

    def _validate_scope(self) -> None:
        if self.scope is LearningScope.USER_PRIVATE:
            if not self.owner_user_id or self.tenant_id is not None or self.project_id is not None:
                raise AILearningMemoryError("INVALID_USER_PRIVATE_LEARNING_SCOPE")
        elif self.scope is LearningScope.PROJECT_PRIVATE:
            if not self.owner_user_id or not self.tenant_id or not self.project_id:
                raise AILearningMemoryError("INVALID_PROJECT_PRIVATE_LEARNING_SCOPE")
        elif self.scope is LearningScope.TENANT_SHARED:
            if not self.tenant_id or self.owner_user_id is not None or self.project_id is not None:
                raise AILearningMemoryError("INVALID_TENANT_SHARED_LEARNING_SCOPE")
        else:
            if any((self.owner_user_id, self.tenant_id, self.project_id, self.user_expertise_level)):
                raise AILearningMemoryError("GENERAL_LEARNING_MUST_NOT_RETAIN_SOURCE_SCOPE")

    def _validate_publication(self) -> None:
        if self.status is LearningStatus.PUBLISHED:
            if self.scope is not LearningScope.GENERAL_PUBLISHED:
                raise AILearningMemoryError("PUBLISHED_LEARNING_MUST_USE_GENERAL_PUBLISHED_SCOPE")
            if not self.privacy_review_passed:
                raise AILearningMemoryError("GENERAL_LEARNING_PRIVACY_REVIEW_REQUIRED")
            if not self.consent_for_generalization:
                raise AILearningMemoryError("GENERAL_LEARNING_CONSENT_REQUIRED")
            if not self.validation_evidence_refs:
                raise AILearningMemoryError("GENERAL_LEARNING_VALIDATION_EVIDENCE_REQUIRED")
            if not self.approved_by or self.approved_at is None:
                raise AILearningMemoryError("GENERAL_LEARNING_ADMIN_APPROVAL_REQUIRED")
        if self.scope is LearningScope.GENERAL_PUBLISHED and self.status is not LearningStatus.PUBLISHED:
            raise AILearningMemoryError("GENERAL_PUBLISHED_SCOPE_REQUIRES_PUBLISHED_STATUS")
        if self.scope is LearningScope.GENERAL_CANDIDATE and self.status is LearningStatus.PUBLISHED:
            raise AILearningMemoryError("GENERAL_CANDIDATE_CANNOT_BE_PUBLISHED")

    def is_general_retrieval_eligible(self) -> bool:
        """Only approved, validated, privacy-reviewed general lessons are reusable."""
        return (
            self.scope is LearningScope.GENERAL_PUBLISHED
            and self.status is LearningStatus.PUBLISHED
            and self.privacy_review_passed
            and self.consent_for_generalization
            and bool(self.validation_evidence_refs)
            and bool(self.approved_by)
            and self.approved_at is not None
        )

    def is_retrievable_for(self, scope: LearningRetrievalScope) -> bool:
        """Return whether this record's scope matches the trusted caller scope."""
        if not isinstance(scope, LearningRetrievalScope):
            raise AILearningMemoryError("TRUSTED_AI_LEARNING_RETRIEVAL_SCOPE_REQUIRED")
        if self.is_general_retrieval_eligible():
            return True
        if self.status in {LearningStatus.REJECTED, LearningStatus.RETIRED}:
            return False
        if self.scope is LearningScope.USER_PRIVATE:
            return self.owner_user_id == scope.user_id
        if self.scope is LearningScope.PROJECT_PRIVATE:
            return (
                self.owner_user_id == scope.user_id
                and self.tenant_id == scope.tenant_id
                and self.project_id == scope.project_id
            )
        if self.scope is LearningScope.TENANT_SHARED:
            return bool(scope.tenant_id) and self.tenant_id == scope.tenant_id
        return False
