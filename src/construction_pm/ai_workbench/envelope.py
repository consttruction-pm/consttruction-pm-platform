"""Typed command context for the CUBI AI Workbench.

The Workbench never owns project facts. Every command carries the exact scope
the server resolved (tenant, actor, project, revision, data date, locale) so a
studio can only read or propose against that pinned context. A missing or
inconsistent envelope is rejected; it is never repaired by guessing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Mapping, Sequence

ENGINEERING = "engineering"
ENTERPRISE = "enterprise"
ENVIRONMENTS = frozenset({ENGINEERING, ENTERPRISE})

# Roles that may propose a mutation. A read-only role can still open a studio
# and inspect the same pinned data, but every write/execute control stays off.
WRITE_ROLES = frozenset({"project_admin", "planner", "global_admin", "scheduler"})

_CORRELATION = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{7,63}$")
_PROJECT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,199}$")
_LOCALE = re.compile(r"^[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})?$")


class EnvelopeError(ValueError):
    """The command cannot be scoped to a real, authorized context."""


def _text(value: object, field: str, *, pattern: re.Pattern[str] | None = None) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EnvelopeError(f"{field.upper()}_REQUIRED")
    resolved = value.strip()
    if pattern is not None and not pattern.match(resolved):
        raise EnvelopeError(f"{field.upper()}_INVALID")
    return resolved


@dataclass(frozen=True)
class CommandEnvelope:
    """Server-resolved context for one assistant command.

    ``roles`` and ``environment`` come from the authenticated session, never
    from the request body. The remaining fields are optional scope the client
    may already know (open project, selected activity) and are only accepted
    after the caller has been authorized for that project.
    """

    tenant_id: str
    actor_id: str
    roles: tuple[str, ...]
    environment: str
    locale: str
    correlation_id: str
    project_id: str | None = None
    source_revision: int | None = None
    data_date: date | None = None
    selected_object: str | None = None

    def __post_init__(self) -> None:
        _text(self.tenant_id, "tenant_id")
        _text(self.actor_id, "actor_id")
        _text(self.correlation_id, "correlation_id", pattern=_CORRELATION)
        _text(self.locale, "locale", pattern=_LOCALE)
        if self.environment not in ENVIRONMENTS:
            raise EnvelopeError("ENVIRONMENT_INVALID")
        if not self.roles:
            raise EnvelopeError("ROLES_REQUIRED")
        if any(not isinstance(role, str) or not role.strip() for role in self.roles):
            raise EnvelopeError("ROLE_INVALID")
        if self.project_id is not None:
            _text(self.project_id, "project_id", pattern=_PROJECT)
        if self.source_revision is not None and (
            not isinstance(self.source_revision, int) or self.source_revision < 0
        ):
            raise EnvelopeError("SOURCE_REVISION_INVALID")
        if self.selected_object is not None:
            _text(self.selected_object, "selected_object")
        if self.environment == ENGINEERING and self.project_id is None:
            # Engineering commands are always project-scoped; asking the user
            # to pick a project is an honest missing input, not an error, so
            # the orchestrator reports it instead of inventing a scope.
            return

    @property
    def can_propose(self) -> bool:
        return bool(set(self.roles).intersection(WRITE_ROLES))

    @property
    def is_engineering(self) -> bool:
        return self.environment == ENGINEERING

    def facts(self) -> tuple[str, ...]:
        """Only server-known facts; no derived numbers are added here."""
        facts: list[str] = [f"environment={self.environment}", f"actor={self.actor_id}"]
        if self.project_id:
            facts.append(f"project={self.project_id}")
        if self.source_revision is not None:
            facts.append(f"source_revision={self.source_revision}")
        if self.data_date is not None:
            facts.append(f"data_date={self.data_date.isoformat()}")
        if self.selected_object:
            facts.append(f"selected={self.selected_object}")
        return tuple(facts)


def envelope_from_session(
    *,
    tenant_id: object,
    actor_id: object,
    roles: object,
    locale: object,
    correlation_id: object,
    environment: object = ENGINEERING,
    project_id: object = None,
    source_revision: object = None,
    data_date: object = None,
    selected_object: object = None,
) -> CommandEnvelope:
    """Build an envelope from trusted session values and validated scope.

    Callers must pass session values (not request body values) for tenant,
    actor and roles; the HTTP boundary is responsible for that.
    """
    if isinstance(roles, str):
        role_values: Sequence[object] = (roles,)
    elif isinstance(roles, (list, tuple, set, frozenset)):
        role_values = tuple(roles)
    else:
        raise EnvelopeError("ROLES_REQUIRED")
    revision: int | None
    if source_revision is None:
        revision = None
    elif isinstance(source_revision, bool) or not isinstance(source_revision, int):
        raise EnvelopeError("SOURCE_REVISION_INVALID")
    else:
        revision = source_revision
    if data_date is not None and not isinstance(data_date, date):
        raise EnvelopeError("DATA_DATE_INVALID")
    return CommandEnvelope(
        tenant_id=str(tenant_id or ""),
        actor_id=str(actor_id or ""),
        roles=tuple(str(role) for role in role_values if str(role).strip()),
        environment=str(environment or ""),
        locale=str(locale or ""),
        correlation_id=str(correlation_id or ""),
        project_id=str(project_id) if project_id is not None else None,
        source_revision=revision,
        data_date=data_date,
        selected_object=str(selected_object) if selected_object is not None else None,
    )


__all__ = [
    "CommandEnvelope",
    "ENVIRONMENTS",
    "ENGINEERING",
    "ENTERPRISE",
    "EnvelopeError",
    "WRITE_ROLES",
    "envelope_from_session",
]
