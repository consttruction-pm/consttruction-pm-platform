"""Studio registry for the CUBI AI Workbench.

A studio is a full-size analytical surface backed by authoritative services.
The registry states what is actually connected today. A studio whose canonical
service is absent is returned as BLOCKED or PARTIAL and its controls stay off;
opening a URL is never treated as capability.
"""

from __future__ import annotations

from dataclasses import dataclass

from .intents import Intent


class StudioId:
    IMPORT_STAGING = "import-staging"
    SCHEDULE_SCENARIO = "schedule-scenario"
    RISK_ANALYSIS = "risk-analysis"
    PROJECT_ANALYSIS = "project-analysis"
    DECISION_APPROVAL = "decision-approval"


class StudioStatus:
    LIVE_VERIFIED = "LIVE_VERIFIED"
    WIRED_READ = "WIRED_READ"
    WIRED_WRITE = "WIRED_WRITE"
    PARTIAL = "PARTIAL"
    SHELL_ONLY = "SHELL_ONLY"
    PLANNED = "PLANNED"
    BLOCKED = "BLOCKED"
    HELP_REFERENCE_PENDING = "HELP_REFERENCE_PENDING"
    HELP_REFERENCE_VERIFIED = "HELP_REFERENCE_VERIFIED"


@dataclass(frozen=True)
class Capabilities:
    """Canonical services the Workbench is allowed to call.

    These flags describe the repository, not a tenant. Tenant-level permissions
    are checked separately on the command envelope.
    """

    scheduling_core: bool = True
    project_import_engine: bool = False
    register_exchange_import: bool = True
    scenario_service: bool = False
    risk_service: bool = True
    analysis_read_models: bool = True
    proposal_execution: bool = False


@dataclass(frozen=True)
class Studio:
    id: str
    intent: str
    status: str
    service: str
    read_route: str | None
    write_route: str | None
    blocked_reason: str | None
    help_topic: str
    help_status: str
    help_url: str | None = None

    @property
    def can_open(self) -> bool:
        return self.status in {
            StudioStatus.LIVE_VERIFIED,
            StudioStatus.WIRED_READ,
            StudioStatus.WIRED_WRITE,
            StudioStatus.PARTIAL,
        }

    @property
    def can_execute(self) -> bool:
        return self.status in {StudioStatus.LIVE_VERIFIED, StudioStatus.WIRED_WRITE}


def studios(capabilities: Capabilities | None = None) -> tuple[Studio, ...]:
    caps = capabilities or Capabilities()
    import_status = (
        StudioStatus.WIRED_WRITE
        if caps.project_import_engine
        else StudioStatus.PARTIAL
        if caps.register_exchange_import
        else StudioStatus.BLOCKED
    )
    import_reason = (
        None
        if caps.project_import_engine
        else "The canonical project exchange/import engine is not connected. "
        "Only register-level exchange preview/apply is available."
    )
    scenario_status = (
        StudioStatus.WIRED_WRITE if caps.scenario_service else StudioStatus.BLOCKED
    )
    scenario_reason = (
        None
        if caps.scenario_service
        else "No revision-bound scenario service is mounted. The schedule core is present, "
        "but scenario creation, runs and comparison have no persisted contract."
    )
    decision_status = (
        StudioStatus.WIRED_WRITE if caps.proposal_execution else StudioStatus.PARTIAL
    )
    decision_reason = (
        None
        if caps.proposal_execution
        else "The canonical proposal/execution runtime is not mounted in this "
        "environment. The studio stays partial and shows no approval control."
    )
    return (
        Studio(
            id=StudioId.IMPORT_STAGING,
            intent=Intent.IMPORT,
            status=import_status,
            service="P6 exchange / import contract",
            read_route="/api/projects/{project_id}/exchange/datasets",
            write_route=(
                "/api/projects/{project_id}/exchange/import"
                if caps.register_exchange_import
                else None
            ),
            blocked_reason=import_reason,
            help_topic="Importing and exporting data",
            help_status=StudioStatus.HELP_REFERENCE_VERIFIED,
            help_url=(
                "https://docs.oracle.com/cd/G48902_01/client_help/en_US/48617.htm"
            ),
        ),
        Studio(
            id=StudioId.SCHEDULE_SCENARIO,
            intent=Intent.SCENARIO,
            status=scenario_status,
            service="Shared Scheduling Core + scenario store",
            read_route="/api/projects/{project_id}/p6/schedule",
            write_route=None,
            blocked_reason=scenario_reason,
            help_topic="Scheduling Projects",
            help_status=StudioStatus.HELP_REFERENCE_VERIFIED,
            help_url=(
                "https://docs.oracle.com/cd/G48902_01/client_help/en_US/"
                "schedulingprojects.htm"
            ),
        ),
        Studio(
            id=StudioId.RISK_ANALYSIS,
            intent=Intent.RISK,
            status=(
                StudioStatus.WIRED_WRITE if caps.risk_service else StudioStatus.BLOCKED
            ),
            service="Risk register API",
            read_route="/api/projects/{project_id}/risks",
            write_route="/api/projects/{project_id}/risks" if caps.risk_service else None,
            blocked_reason=None if caps.risk_service else "Risk service is not mounted.",
            help_topic="Risks",
            help_status=StudioStatus.HELP_REFERENCE_VERIFIED,
            help_url=(
                "https://docs.oracle.com/cd/G48902_01/client_help/en_US/risks.htm"
            ),
        ),
        Studio(
            id=StudioId.PROJECT_ANALYSIS,
            intent=Intent.ANALYSIS,
            status=(
                StudioStatus.WIRED_READ
                if caps.analysis_read_models
                else StudioStatus.BLOCKED
            ),
            service="Authoritative schedule and project read models",
            read_route="/api/projects/{project_id}/p6/schedule",
            write_route=None,
            blocked_reason=(
                None
                if caps.analysis_read_models
                else "No authoritative project read model is mounted."
            ),
            help_topic="Earned Value",
            help_status=StudioStatus.HELP_REFERENCE_VERIFIED,
            help_url=(
                "https://docs.oracle.com/cd/G48902_01/client_help/en_US/earned_value.htm"
            ),
        ),
        Studio(
            id=StudioId.DECISION_APPROVAL,
            intent=Intent.DECISION,
            status=decision_status,
            service=(
                "Canonical AI action proposal store with approval and execution"
                if caps.proposal_execution
                else "AI action proposal store (not mounted)"
            ),
            read_route="/api/projects/{project_id}/ai/actions/proposals",
            write_route=(
                "/api/projects/{project_id}/ai/actions/proposals/{proposal_id}/decision"
                if caps.proposal_execution
                else None
            ),
            blocked_reason=decision_reason,
            help_topic="Approving or Denying Budget Change Requests",
            help_status=StudioStatus.HELP_REFERENCE_VERIFIED,
            help_url=(
                "https://docs.oracle.com/cd/G48897_01/p6help/en/44036.htm"
            ),
        ),
    )


def studio_for(intent: str, capabilities: Capabilities | None = None) -> Studio | None:
    for studio in studios(capabilities):
        if studio.intent == intent:
            return studio
    # Comparison and export are views inside an analytical studio; they must
    # not become a sixth top-level studio.
    if intent in {Intent.COMPARE, Intent.EXPORT}:
        return studio_for(Intent.SCENARIO, capabilities)
    if intent == Intent.EXPLAIN:
        return studio_for(Intent.ANALYSIS, capabilities)
    return None


__all__ = [
    "Capabilities",
    "Studio",
    "StudioId",
    "StudioStatus",
    "studio_for",
    "studios",
]
