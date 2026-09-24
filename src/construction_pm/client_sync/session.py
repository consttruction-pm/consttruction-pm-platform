from __future__ import annotations

from dataclasses import dataclass

from .context import OfflineProjectContext


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

    def with_revision(self, revision: int) -> "ClientProjectSession":
        if revision < 0:
            raise ValueError("revision must be non-negative")
        self.validate()
        return ClientProjectSession(
            context=self.context,
            api_contract_version=self.api_contract_version,
            revision=revision,
        )
