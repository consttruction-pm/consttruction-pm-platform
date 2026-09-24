from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .context import OfflineProjectContext
from .outcome import SyncMutationOutcome

if TYPE_CHECKING:
    from .result import ClientMutationResult


@dataclass(frozen=True)
class ClientProjectSession:
    """Validated online/offline session boundary for a selected project.

    The session carries identity and contract versions only. It does not own
    scheduling, calendar, financial, Progress, or other authoritative rules.
    """

    context: OfflineProjectContext
    api_contract_version: str
    revision: int | None = None

    contract_version = "client-project-session.v1"

    def validate(self) -> None:
        self.context.validate()
        if not self.api_contract_version.strip():
            raise ValueError("api_contract_version is required")
        if self.revision is not None and self.revision < 0:
            raise ValueError("revision must be non-negative when provided")

    def mutation_context(self) -> OfflineProjectContext:
        self.validate()
        return self.context

    def apply_authoritative_outcome(self, outcome: SyncMutationOutcome) -> "ClientProjectSession":
        """Advance revision only from an applied/replayed authoritative outcome."""
        self.validate()
        outcome.validate()
        if outcome.status not in {"applied", "replayed"}:
            return self
        if outcome.revision is None:
            raise ValueError("successful outcome requires revision")
        if self.revision is not None and outcome.revision < self.revision:
            raise ValueError("authoritative revision cannot move backwards")
        return self.with_revision(outcome.revision)

    def apply_mutation_result(self, result: "ClientMutationResult") -> "ClientProjectSession":
        """Advance revision from a normalized successful mutation result only."""
        self.validate()
        result.validate()
        if not result.successful:
            return self
        if result.revision is None:
            raise ValueError("successful mutation result requires revision")
        if self.revision is not None and result.revision < self.revision:
            raise ValueError("authoritative revision cannot move backwards")
        return self.with_revision(result.revision)

    def with_revision(self, revision: int) -> "ClientProjectSession":
        if revision < 0:
            raise ValueError("revision must be non-negative")
        self.validate()
        return ClientProjectSession(
            context=self.context,
            api_contract_version=self.api_contract_version,
            revision=revision,
        )
