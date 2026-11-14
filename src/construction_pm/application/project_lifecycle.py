from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol
from urllib.parse import urlsplit

from .authorization import AuthorizationContext, AuthorizationError, Permission, RoleBasedAuthorizationPolicy


class SessionError(ValueError):
    """Raised when a session is invalid or expired."""


class ProjectLifecycleError(ValueError):
    """Raised when a project lifecycle operation cannot be completed."""


@dataclass(frozen=True)
class AuthenticatedSession:
    session_id: str
    user_id: str
    tenant_id: str
    roles: frozenset[str]
    expires_at: datetime

    def validate(self, *, now: datetime) -> None:
        for name, value in (
            ("session_id", self.session_id),
            ("user_id", self.user_id),
            ("tenant_id", self.tenant_id),
        ):
            if not isinstance(value, str) or not value.strip():
                raise SessionError(f"INVALID_SESSION_{name.upper()}")
        if not isinstance(self.roles, frozenset) or any(
            not isinstance(role, str) or not role.strip() for role in self.roles
        ):
            raise SessionError("INVALID_SESSION_ROLES")
        if self.expires_at.tzinfo is None or self.expires_at.utcoffset() is None:
            raise SessionError("SESSION_EXPIRY_MUST_BE_TIMEZONE_AWARE")
        if now.tzinfo is None or now.utcoffset() is None:
            raise SessionError("NOW_MUST_BE_TIMEZONE_AWARE")
        if now >= self.expires_at:
            raise SessionError("SESSION_EXPIRED")


@dataclass(frozen=True)
class ProjectSummary:
    project_id: str
    tenant_id: str
    name: str
    revision: int
    description: str = ""
    start_date: str | None = None
    date_system: str = "gregorian"
    primary_calendar_id: str | None = None
    # Configuration edits are guarded by their own optimistic token. The
    # ``revision`` column identifies the workspace data version every
    # activity/WBS/relationship row is stamped with; reusing it for metadata
    # edits would make existing workspace data unreadable after a rename.
    settings_revision: int = 0
    # V26 Project Details General tab status. Metadata edits carry their own
    # revision; the status change is a separate, audited lifecycle operation.
    status: str = "active"
    # CUBI replaces the P6 EPS classification with a Business Domain. It is a
    # persisted project attribute, so the Projects register groups real records
    # rather than deriving a hierarchy from names. The empty string means the
    # record has not been classified yet.
    business_domain: str = ""
    # V26 Project Details General/Defaults values. The responsible manager is
    # stored on the project record until the Enterprise OBS domain (Agent 3)
    # exposes a hierarchy reference; it is never a display-only decoration.
    obs_responsible_manager: str = ""
    website_url: str = ""
    # P6 project checkout: while a project is checked out by one user, other
    # sessions may read it but metadata/status edits are rejected until that
    # user (or the checkout owner) checks it in.
    checkout_state: str = "checked_in"
    checked_out_by: str = ""
    checked_out_at: str | None = None


DATE_SYSTEMS = frozenset({"gregorian", "jalali"})
PROJECT_STATUSES = frozenset({"active", "inactive", "planned", "what_if"})
# CUBI Business Domain taxonomy (workspace-information-architecture.md). The
# stored value is a stable code; the browser localizes the label.
BUSINESS_DOMAINS = frozenset(
    {"construction", "oil_gas", "infrastructure", "industrial", "energy", "other"}
)
MAX_PROJECT_DESCRIPTION = 2000
MAX_PROJECT_CALENDAR_ID = 200
MAX_PROJECT_OBS_MANAGER = 160
MAX_PROJECT_WEBSITE_URL = 2048
CHECKOUT_STATES = frozenset({"checked_in", "checked_out"})


def normalize_project_description(value: object) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ProjectLifecycleError("PROJECT_DESCRIPTION_INVALID")
    description = value.strip()
    if len(description) > MAX_PROJECT_DESCRIPTION:
        raise ProjectLifecycleError("PROJECT_DESCRIPTION_TOO_LONG")
    return description


def normalize_project_start_date(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ProjectLifecycleError("PROJECT_START_DATE_INVALID")
    start_date = value.strip()
    try:
        parsed = date.fromisoformat(start_date)
    except ValueError as exc:
        raise ProjectLifecycleError("PROJECT_START_DATE_INVALID") from exc
    if parsed.isoformat() != start_date:
        raise ProjectLifecycleError("PROJECT_START_DATE_INVALID")
    return start_date


def normalize_project_date_system(value: object) -> str:
    if value is None or value == "":
        return "gregorian"
    if not isinstance(value, str) or value not in DATE_SYSTEMS:
        raise ProjectLifecycleError("PROJECT_DATE_SYSTEM_INVALID")
    return value


def normalize_project_calendar_id(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ProjectLifecycleError("PROJECT_PRIMARY_CALENDAR_ID_INVALID")
    calendar_id = value.strip()
    if len(calendar_id) > MAX_PROJECT_CALENDAR_ID:
        raise ProjectLifecycleError("PROJECT_PRIMARY_CALENDAR_ID_INVALID")
    return calendar_id


def normalize_project_business_domain(value: object) -> str:
    """Normalise the CUBI Business Domain classification.

    ``None`` and the empty string are the explicit "not classified" state for
    records created before the field existed. Any other value must be one of
    the six documented domains; the API never stores an arbitrary grouping
    label, so the Projects tree cannot invent a domain from a typo.
    """
    if value is None or value == "":
        return ""
    if not isinstance(value, str):
        raise ProjectLifecycleError("PROJECT_BUSINESS_DOMAIN_INVALID")
    cleaned = value.strip().lower()
    # Accept the human label from the V26 Help taxonomy as well as the stable
    # code, so a form can submit "Oil & Gas" without inventing a new domain.
    aliases = {
        "oil & gas": "oil_gas",
        "oil and gas": "oil_gas",
    }
    domain = aliases.get(cleaned, cleaned.replace("-", "_").replace(" ", "_"))
    if domain not in BUSINESS_DOMAINS:
        raise ProjectLifecycleError("PROJECT_BUSINESS_DOMAIN_INVALID")
    return domain


def normalize_project_obs_responsible_manager(value: object) -> str:
    """Normalise the project's responsible-manager label.

    CUBI's Enterprise OBS hierarchy is a separate domain. Until that reference
    exists, the project stores the manager label as a first-class attribute so
    Project Details can persist and read it back instead of showing a control
    that discards its value.
    """
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ProjectLifecycleError("PROJECT_OBS_RESPONSIBLE_MANAGER_INVALID")
    manager = value.strip()
    if len(manager) > MAX_PROJECT_OBS_MANAGER:
        raise ProjectLifecycleError("PROJECT_OBS_RESPONSIBLE_MANAGER_TOO_LONG")
    return manager


def normalize_project_website_url(value: object) -> str:
    """Normalise an optional http(s) project web-site address.

    Only absolute HTTP(S) URLs are accepted. The value is persisted verbatim
    (after trimming) so Project Details re-opens with exactly what the user
    saved, and a ``javascript:`` or scheme-relative entry is never stored.
    """
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ProjectLifecycleError("PROJECT_WEBSITE_URL_INVALID")
    url = value.strip()
    if not url:
        return ""
    if len(url) > MAX_PROJECT_WEBSITE_URL or any(character.isspace() for character in url):
        raise ProjectLifecycleError("PROJECT_WEBSITE_URL_INVALID")
    try:
        parsed = urlsplit(url)
    except ValueError as exc:
        raise ProjectLifecycleError("PROJECT_WEBSITE_URL_INVALID") from exc
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        raise ProjectLifecycleError("PROJECT_WEBSITE_URL_INVALID")
    if parsed.username or parsed.password:
        raise ProjectLifecycleError("PROJECT_WEBSITE_URL_INVALID")
    return url


def normalize_project_status(value: object) -> str:
    """Normalise a V26 project status to its stored form.

    The General tab offers Active, Inactive, Planned and What-If; the stored
    value keeps the Help labels' meaning in a stable snake_case form.
    """
    if not isinstance(value, str):
        raise ProjectLifecycleError("PROJECT_STATUS_INVALID")
    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    if normalized not in PROJECT_STATUSES:
        raise ProjectLifecycleError("PROJECT_STATUS_INVALID")
    return normalized


@dataclass(frozen=True)
class ProjectStatusEvent:
    """Append-only record of one accepted project status change."""

    tenant_id: str
    project_id: str
    event_id: str
    from_status: str
    to_status: str
    actor_user_id: str
    recorded_at: datetime
    settings_revision: int

    def validate(self) -> None:
        for name, value in (
            ("tenant_id", self.tenant_id),
            ("project_id", self.project_id),
            ("event_id", self.event_id),
            ("actor_user_id", self.actor_user_id),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ProjectLifecycleError(f"INVALID_PROJECT_STATUS_EVENT_{name.upper()}")
        for name, value in (
            ("from_status", self.from_status),
            ("to_status", self.to_status),
        ):
            if value not in PROJECT_STATUSES:
                raise ProjectLifecycleError(f"INVALID_PROJECT_STATUS_EVENT_{name.upper()}")
        if not isinstance(self.recorded_at, datetime) or self.recorded_at.tzinfo is None:
            raise ProjectLifecycleError("INVALID_PROJECT_STATUS_EVENT_RECORDED_AT")
        if (
            isinstance(self.settings_revision, bool)
            or not isinstance(self.settings_revision, int)
            or self.settings_revision < 0
        ):
            raise ProjectLifecycleError("INVALID_PROJECT_STATUS_EVENT_REVISION")


def normalize_expected_revision(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ProjectLifecycleError("PROJECT_REVISION_INVALID")
    return value


@dataclass(frozen=True)
class ProjectContext:
    tenant_id: str
    project_id: str
    revision: int
    user_id: str

    def authorization_context(self, roles: frozenset[str]) -> AuthorizationContext:
        return AuthorizationContext(
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            user_id=self.user_id,
            roles=roles,
        )


class ProjectRepository(Protocol):
    def list_for_user(self, tenant_id: str, user_id: str) -> tuple[ProjectSummary, ...]: ...
    def get_for_user(self, tenant_id: str, project_id: str, user_id: str) -> ProjectSummary | None: ...
    def create_for_user(
        self,
        tenant_id: str,
        user_id: str,
        project_id: str,
        name: str,
        *,
        description: str = "",
        start_date: str | None = None,
        date_system: str = "gregorian",
        primary_calendar_id: str | None = None,
        business_domain: str = "",
        obs_responsible_manager: str = "",
        website_url: str = "",
    ) -> ProjectSummary: ...
    def update_for_user(
        self,
        tenant_id: str,
        user_id: str,
        project_id: str,
        *,
        expected_revision: int,
        name: str,
        description: str = "",
        start_date: str | None = None,
        date_system: str = "gregorian",
        primary_calendar_id: str | None = None,
        business_domain: str | None = None,
        obs_responsible_manager: str | None = None,
        website_url: str | None = None,
    ) -> ProjectSummary | None: ...
    def set_checkout_for_user(
        self,
        tenant_id: str,
        user_id: str,
        project_id: str,
        *,
        checked_out: bool,
        expected_revision: int,
        actor_user_id: str,
        changed_at: datetime,
    ) -> ProjectSummary | None: ...
    def set_status_for_user(
        self,
        tenant_id: str,
        user_id: str,
        project_id: str,
        *,
        status: str,
        expected_revision: int,
        actor_user_id: str,
        recorded_at: datetime,
    ) -> ProjectSummary | None: ...
    def status_history_for_user(
        self, tenant_id: str, project_id: str, user_id: str
    ) -> tuple[ProjectStatusEvent, ...]: ...


class SessionRepository(Protocol):
    def get(self, session_id: str) -> AuthenticatedSession | None: ...


class ProjectLifecycleService:
    """Authoritative session-bound project lifecycle boundary.

    The browser never supplies an authoritative tenant/user identity. A transport
    adapter resolves the opaque session first, then this service derives project
    context from that session and the authorized project repository.
    """

    def __init__(
        self,
        sessions: SessionRepository,
        projects: ProjectRepository,
        policy: RoleBasedAuthorizationPolicy,
    ) -> None:
        self._sessions = sessions
        self._projects = projects
        self._policy = policy

    def session(self, session_id: str, *, now: datetime) -> AuthenticatedSession:
        session = self._sessions.get(session_id)
        if session is None:
            raise SessionError("SESSION_NOT_FOUND")
        session.validate(now=now)
        return session

    def list_projects(
        self, session_id: str, *, now: datetime
    ) -> tuple[ProjectSummary, ...]:
        session = self.session(session_id, now=now)
        listed = self._projects.list_for_user(session.tenant_id, session.user_id)
        # Membership decides which rows the query may return; the role policy
        # decides whether this session may read a project at all. Both gates
        # apply, so a membership row alone cannot surface a project to a role
        # that has no project.read grant.
        return tuple(
            project
            for project in listed
            if self._policy.is_allowed(
                AuthorizationContext(
                    tenant_id=project.tenant_id,
                    project_id=project.project_id,
                    user_id=session.user_id,
                    roles=session.roles,
                ),
                Permission.PROJECT_READ,
            )
        )

    def _open_project_for_session(
        self, session: AuthenticatedSession, project_id: str
    ) -> ProjectContext:
        project = self._projects.get_for_user(
            session.tenant_id, project_id, session.user_id
        )
        if project is None:
            raise ProjectLifecycleError("PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED")
        context = ProjectContext(
            tenant_id=project.tenant_id,
            project_id=project.project_id,
            revision=project.revision,
            user_id=session.user_id,
        )
        self._policy.require(
            context.authorization_context(session.roles), Permission.PROJECT_READ
        )
        return context

    def open_project(
        self, session_id: str, project_id: str, *, now: datetime
    ) -> ProjectContext:
        session = self.session(session_id, now=now)
        return self._open_project_for_session(session, project_id)

    def authorize_project(
        self,
        session_id: str,
        project_id: str,
        permission: Permission,
        *,
        now: datetime,
    ) -> ProjectContext:
        """Resolve scope once from the authenticated session, then enforce permission."""
        session = self.session(session_id, now=now)
        context = self._open_project_for_session(session, project_id)
        self._policy.require(context.authorization_context(session.roles), permission)
        return context

    def create_project(
        self,
        session_id: str,
        project_id: str,
        name: str,
        *,
        description: str = "",
        start_date: str | None = None,
        date_system: str = "gregorian",
        primary_calendar_id: str | None = None,
        business_domain: str = "",
        obs_responsible_manager: str = "",
        website_url: str = "",
        now: datetime,
    ) -> ProjectContext:
        session = self.session(session_id, now=now)
        if not self._policy.is_allowed(
            AuthorizationContext(
                tenant_id=session.tenant_id,
                project_id=project_id,
                user_id=session.user_id,
                roles=session.roles,
            ),
            Permission.PROJECT_ADMIN,
        ):
            raise AuthorizationError("authorization denied for permission=project.admin")
        if not isinstance(project_id, str) or not project_id.strip():
            raise ProjectLifecycleError("PROJECT_ID_REQUIRED")
        if not isinstance(name, str) or not name.strip():
            raise ProjectLifecycleError("PROJECT_NAME_REQUIRED")
        normalized_description = normalize_project_description(description)
        normalized_start_date = normalize_project_start_date(start_date)
        normalized_date_system = normalize_project_date_system(date_system)
        normalized_calendar_id = normalize_project_calendar_id(primary_calendar_id)
        normalized_business_domain = normalize_project_business_domain(business_domain)
        normalized_obs_manager = normalize_project_obs_responsible_manager(
            obs_responsible_manager
        )
        normalized_website_url = normalize_project_website_url(website_url)
        project = self._projects.create_for_user(
            session.tenant_id,
            session.user_id,
            project_id.strip(),
            name.strip(),
            description=normalized_description,
            start_date=normalized_start_date,
            date_system=normalized_date_system,
            primary_calendar_id=normalized_calendar_id,
            business_domain=normalized_business_domain,
            obs_responsible_manager=normalized_obs_manager,
            website_url=normalized_website_url,
        )
        return ProjectContext(
            tenant_id=project.tenant_id,
            project_id=project.project_id,
            revision=project.revision,
            user_id=session.user_id,
        )

    def get_project(
        self, session_id: str, project_id: str, *, now: datetime
    ) -> ProjectSummary:
        session = self.session(session_id, now=now)
        project = self._projects.get_for_user(
            session.tenant_id, project_id, session.user_id
        )
        if project is None:
            raise ProjectLifecycleError("PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED")
        self._policy.require(
            ProjectContext(
                tenant_id=project.tenant_id,
                project_id=project.project_id,
                revision=project.revision,
                user_id=session.user_id,
            ).authorization_context(session.roles),
            Permission.PROJECT_READ,
        )
        return project

    def update_project(
        self,
        session_id: str,
        project_id: str,
        *,
        name: str,
        description: str = "",
        start_date: str | None = None,
        date_system: str = "gregorian",
        primary_calendar_id: str | None = None,
        business_domain: str | None = None,
        obs_responsible_manager: str | None = None,
        website_url: str | None = None,
        expected_revision: int,
        now: datetime,
    ) -> ProjectSummary:
        """Replace project metadata under optimistic-concurrency control.

        ``expected_revision`` is the configuration revision the editor loaded
        (``ProjectSummary.settings_revision``), not the workspace data revision.
        A stale value never overwrites newer metadata: the repository performs a
        conditional update and the service reports a conflict for the caller to
        resolve by reloading.
        """
        session = self.session(session_id, now=now)
        existing = self._projects.get_for_user(
            session.tenant_id, project_id, session.user_id
        )
        if existing is None:
            raise ProjectLifecycleError("PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED")
        self._policy.require(
            ProjectContext(
                tenant_id=existing.tenant_id,
                project_id=existing.project_id,
                revision=existing.revision,
                user_id=session.user_id,
            ).authorization_context(session.roles),
            Permission.PROJECT_ADMIN,
        )
        # A checked-out project is editable only by the session that checked it
        # out. This guard runs before validation so a blocked editor gets the
        # checkout conflict rather than a misleading field error.
        if (
            existing.checkout_state == "checked_out"
            and existing.checked_out_by
            and existing.checked_out_by != session.user_id
        ):
            raise ProjectLifecycleError("PROJECT_CHECKED_OUT_BY_OTHER")
        if not isinstance(name, str) or not name.strip():
            raise ProjectLifecycleError("PROJECT_NAME_REQUIRED")
        revision = normalize_expected_revision(expected_revision)
        normalized_description = normalize_project_description(description)
        normalized_start_date = normalize_project_start_date(start_date)
        normalized_date_system = normalize_project_date_system(date_system)
        normalized_calendar_id = normalize_project_calendar_id(primary_calendar_id)
        # ``None`` keeps the stored classification: a client that only edits
        # the name must not silently erase the Business Domain. An explicit
        # empty string clears it.
        normalized_business_domain = (
            None
            if business_domain is None
            else normalize_project_business_domain(business_domain)
        )
        normalized_obs_manager = (
            None
            if obs_responsible_manager is None
            else normalize_project_obs_responsible_manager(obs_responsible_manager)
        )
        normalized_website_url = (
            None
            if website_url is None
            else normalize_project_website_url(website_url)
        )
        updated = self._projects.update_for_user(
            session.tenant_id,
            session.user_id,
            project_id,
            expected_revision=revision,
            name=name.strip(),
            description=normalized_description,
            start_date=normalized_start_date,
            date_system=normalized_date_system,
            primary_calendar_id=normalized_calendar_id,
            business_domain=normalized_business_domain,
            obs_responsible_manager=normalized_obs_manager,
            website_url=normalized_website_url,
        )
        if updated is None:
            if self._projects.get_for_user(
                session.tenant_id, project_id, session.user_id
            ) is None:
                raise ProjectLifecycleError("PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED")
            raise ProjectLifecycleError("PROJECT_REVISION_CONFLICT")
        return updated

    def set_project_status(
        self,
        session_id: str,
        project_id: str,
        *,
        status: str,
        expected_revision: int,
        now: datetime,
    ) -> ProjectSummary:
        """Change the V26 project status under the configuration revision guard.

        Setting the status a project already has is a no-op: it returns the
        stored row without bumping the revision or appending an event, so a
        retried request cannot create duplicate history.
        """
        session = self.session(session_id, now=now)
        existing = self._projects.get_for_user(
            session.tenant_id, project_id, session.user_id
        )
        if existing is None:
            raise ProjectLifecycleError("PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED")
        self._policy.require(
            ProjectContext(
                tenant_id=existing.tenant_id,
                project_id=existing.project_id,
                revision=existing.revision,
                user_id=session.user_id,
            ).authorization_context(session.roles),
            Permission.PROJECT_ADMIN,
        )
        if (
            existing.checkout_state == "checked_out"
            and existing.checked_out_by
            and existing.checked_out_by != session.user_id
        ):
            raise ProjectLifecycleError("PROJECT_CHECKED_OUT_BY_OTHER")
        normalized_status = normalize_project_status(status)
        revision = normalize_expected_revision(expected_revision)
        if existing.status == normalized_status:
            return existing
        updated = self._projects.set_status_for_user(
            session.tenant_id,
            session.user_id,
            project_id,
            status=normalized_status,
            expected_revision=revision,
            actor_user_id=session.user_id,
            recorded_at=now,
        )
        if updated is None:
            if self._projects.get_for_user(
                session.tenant_id, project_id, session.user_id
            ) is None:
                raise ProjectLifecycleError("PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED")
            raise ProjectLifecycleError("PROJECT_REVISION_CONFLICT")
        return updated

    def set_project_checkout(
        self,
        session_id: str,
        project_id: str,
        *,
        checked_out: bool,
        expected_revision: int,
        now: datetime,
    ) -> ProjectSummary:
        """Check a project out or in under the configuration revision guard.

        Checkout is an exclusive-edit lease: while another user holds it, this
        service rejects metadata and status edits. Repeating the current state
        is idempotent and does not bump the revision. The repository performs a
        conditional write so two simultaneous checkout requests cannot both
        win.
        """
        session = self.session(session_id, now=now)
        if not isinstance(checked_out, bool):
            raise ProjectLifecycleError("PROJECT_CHECKOUT_STATE_INVALID")
        existing = self._projects.get_for_user(
            session.tenant_id, project_id, session.user_id
        )
        if existing is None:
            raise ProjectLifecycleError("PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED")
        self._policy.require(
            ProjectContext(
                tenant_id=existing.tenant_id,
                project_id=existing.project_id,
                revision=existing.revision,
                user_id=session.user_id,
            ).authorization_context(session.roles),
            Permission.PROJECT_ADMIN,
        )
        revision = normalize_expected_revision(expected_revision)
        if checked_out:
            if existing.checkout_state == "checked_out":
                if existing.checked_out_by == session.user_id:
                    return existing
                raise ProjectLifecycleError("PROJECT_CHECKOUT_CONFLICT")
        else:
            if existing.checkout_state != "checked_out":
                return existing
            if existing.checked_out_by != session.user_id:
                raise ProjectLifecycleError("PROJECT_CHECKOUT_CONFLICT")
        updated = self._projects.set_checkout_for_user(
            session.tenant_id,
            session.user_id,
            project_id,
            checked_out=checked_out,
            expected_revision=revision,
            actor_user_id=session.user_id,
            changed_at=now,
        )
        if updated is None:
            current = self._projects.get_for_user(
                session.tenant_id, project_id, session.user_id
            )
            if current is None:
                raise ProjectLifecycleError("PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED")
            if current.settings_revision != revision:
                raise ProjectLifecycleError("PROJECT_REVISION_CONFLICT")
            raise ProjectLifecycleError("PROJECT_CHECKOUT_CONFLICT")
        return updated

    def project_status_history(
        self, session_id: str, project_id: str, *, now: datetime
    ) -> tuple[ProjectStatusEvent, ...]:
        session = self.session(session_id, now=now)
        project = self._projects.get_for_user(
            session.tenant_id, project_id, session.user_id
        )
        if project is None:
            raise ProjectLifecycleError("PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED")
        self._policy.require(
            ProjectContext(
                tenant_id=project.tenant_id,
                project_id=project.project_id,
                revision=project.revision,
                user_id=session.user_id,
            ).authorization_context(session.roles),
            Permission.PROJECT_READ,
        )
        return self._projects.status_history_for_user(
            session.tenant_id, project_id, session.user_id
        )
