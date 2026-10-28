from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from typing import Callable, Protocol

from .ai_action_runtime import AIActionTransactionManager
from .ai_learning_memory import (
    AILearningMemoryRecord,
    LearningScope,
    LearningSignalKind,
    LearningStatus,
)
from .ai_learning_memory_repository import AILearningMemoryRepository


class AILearningKnowledgeAdminError(ValueError):
    """Stable validation and state-transition errors for global knowledge review."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


class _ModerationRepository(AILearningMemoryRepository, Protocol):
    def list_general_candidates(self) -> tuple[AILearningMemoryRecord, ...]: ...
    def get_general_candidate(self, record_id: str, record_version: int) -> AILearningMemoryRecord | None: ...


class AILearningKnowledgeAdminService:
    """Human review boundary for moving public research from candidate to active knowledge.

    Only an authenticated global knowledge-admin role should be allowed to call this
    service through HTTP. The service never treats a model output as approval evidence.
    Every decision appends a new record version; prior versions remain immutable.
    """

    def __init__(
        self,
        *,
        repository: _ModerationRepository,
        transaction_manager: AIActionTransactionManager,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._repository = repository
        self._transaction_manager = transaction_manager
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        repository_connection = getattr(repository, "connection", None)
        manager_connection = getattr(transaction_manager, "connection", None)
        if (
            repository_connection is not None
            and manager_connection is not None
            and repository_connection is not manager_connection
        ):
            raise AILearningKnowledgeAdminError("AI_LEARNING_TRANSACTION_CONNECTION_MISMATCH")

    def list_candidates(self) -> tuple[AILearningMemoryRecord, ...]:
        try:
            records = self._repository.list_general_candidates()
        except Exception as exc:
            raise AILearningKnowledgeAdminError("AI_LEARNING_CANDIDATE_LIST_FAILED") from exc
        for record in records:
            if (
                record.scope is not LearningScope.GENERAL_CANDIDATE
                or record.status is not LearningStatus.CANDIDATE
                or record.signal_kind is not LearningSignalKind.PUBLIC_RESEARCH
            ):
                raise AILearningKnowledgeAdminError("AI_LEARNING_CANDIDATE_REPOSITORY_CONTRACT_INVALID")
        return records

    def decide(
        self,
        record_id: str,
        record_version: int,
        *,
        decision: str,
        actor_user_id: str,
        privacy_review_passed: bool = False,
        consent_for_generalization: bool = False,
        validation_evidence_refs: tuple[str, ...] = (),
    ) -> AILearningMemoryRecord:
        if not isinstance(actor_user_id, str) or not actor_user_id.strip() or len(actor_user_id) > 128:
            raise AILearningKnowledgeAdminError("AI_LEARNING_REVIEW_ACTOR_INVALID")
        if decision not in {"approve", "reject"}:
            raise AILearningKnowledgeAdminError("AI_LEARNING_REVIEW_DECISION_INVALID")
        if not isinstance(record_id, str) or not record_id.strip() or len(record_id) > 128:
            raise AILearningKnowledgeAdminError("AI_LEARNING_RECORD_ID_INVALID")
        if isinstance(record_version, bool) or not isinstance(record_version, int) or record_version < 1:
            raise AILearningKnowledgeAdminError("AI_LEARNING_RECORD_VERSION_INVALID")

        if decision == "approve":
            if privacy_review_passed is not True:
                raise AILearningKnowledgeAdminError("AI_LEARNING_PRIVACY_REVIEW_REQUIRED")
            if consent_for_generalization is not True:
                raise AILearningKnowledgeAdminError("AI_LEARNING_GENERALIZATION_CONFIRMATION_REQUIRED")
            if (
                not isinstance(validation_evidence_refs, tuple)
                or not 1 <= len(validation_evidence_refs) <= 20
                or any(
                    not isinstance(ref, str) or not ref.strip() or len(ref.strip()) > 500
                    for ref in validation_evidence_refs
                )
            ):
                raise AILearningKnowledgeAdminError("AI_LEARNING_VALIDATION_EVIDENCE_REQUIRED")
            validation_refs = tuple(dict.fromkeys(ref.strip() for ref in validation_evidence_refs))
            if not validation_refs:
                raise AILearningKnowledgeAdminError("AI_LEARNING_VALIDATION_EVIDENCE_REQUIRED")
        else:
            validation_refs = ()

        try:
            candidate = self._repository.get_general_candidate(record_id, record_version)
        except Exception as exc:
            raise AILearningKnowledgeAdminError("AI_LEARNING_CANDIDATE_READ_FAILED") from exc
        if candidate is None:
            raise AILearningKnowledgeAdminError("AI_LEARNING_CANDIDATE_NOT_FOUND_OR_STALE")
        if candidate.signal_kind is not LearningSignalKind.PUBLIC_RESEARCH:
            raise AILearningKnowledgeAdminError("AI_LEARNING_CANDIDATE_SIGNAL_NOT_REVIEWABLE")

        now = self._clock().astimezone(timezone.utc)
        if decision == "approve":
            revised = replace(
                candidate,
                record_version=candidate.record_version + 1,
                scope=LearningScope.GENERAL_PUBLISHED,
                status=LearningStatus.PUBLISHED,
                updated_at=now,
                privacy_review_passed=True,
                consent_for_generalization=True,
                validation_evidence_refs=validation_refs,
                approved_by=actor_user_id,
                approved_at=now,
            )
        else:
            revised = replace(
                candidate,
                record_version=candidate.record_version + 1,
                scope=LearningScope.GENERAL_CANDIDATE,
                status=LearningStatus.REJECTED,
                updated_at=now,
                privacy_review_passed=False,
                consent_for_generalization=False,
                validation_evidence_refs=(),
                approved_by=None,
                approved_at=None,
            )
        try:
            with self._transaction_manager.transaction():
                stored = self._repository.append(revised)
        except Exception as exc:
            raise AILearningKnowledgeAdminError("AI_LEARNING_CANDIDATE_DECISION_PERSISTENCE_FAILED") from exc
        if stored != revised:
            raise AILearningKnowledgeAdminError("AI_LEARNING_CANDIDATE_DECISION_READBACK_MISMATCH")
        return stored


__all__ = ["AILearningKnowledgeAdminError", "AILearningKnowledgeAdminService"]
