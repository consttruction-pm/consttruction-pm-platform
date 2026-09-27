from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .control_intelligence.contracts import ControlIntelligenceResult
from .control_intelligence.scenario import ScenarioProposal


@dataclass(frozen=True)
class ControlIntelligenceResultEnvelope:
    contract_version: str
    result: ControlIntelligenceResult

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "result_id": self.result.result_id,
            "tenant_id": self.result.scope.tenant_id,
            "project_id": self.result.scope.project_id,
            "project_revision": self.result.scope.project_revision,
            "generated_at": self.result.generated_at.isoformat(),
            "summary_key": self.result.summary_key,
            "findings": tuple(
                {
                    "finding_id": finding.finding_id,
                    "domain": finding.domain.value,
                    "severity": finding.severity.value,
                    "title_key": finding.title_key,
                    "detail_key": finding.detail_key,
                    "source_refs": tuple(ref.source_id for ref in finding.source_refs),
                }
                for finding in self.result.findings
            ),
            "source_refs": tuple(ref.source_id for ref in self.result.source_refs),
            "proposed_actions": tuple(
                {
                    "action_id": action.action_id,
                    "action_type": action.action_type,
                    "title_key": action.title_key,
                    "requires_approval": action.requires_approval,
                    "source_refs": tuple(ref.source_id for ref in action.source_refs),
                }
                for action in self.result.proposed_actions
            ),
        }


@dataclass(frozen=True)
class ScenarioProposalEnvelope:
    contract_version: str
    proposal: ScenarioProposal

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "scenario_id": self.proposal.scenario_id,
            "tenant_id": self.proposal.base_scope.tenant_id,
            "project_id": self.proposal.base_scope.project_id,
            "project_revision": self.proposal.base_scope.project_revision,
            "authoritative_mutation_allowed": self.proposal.authoritative_mutation_allowed,
            "impacts": tuple(
                {
                    "domain": impact.domain.value,
                    "entity_type": impact.entity_type,
                    "entity_id": impact.entity_id,
                    "impact_type": impact.impact_type,
                    "description_key": impact.description_key,
                    "source_refs": tuple(ref.source_id for ref in impact.source_refs),
                }
                for impact in self.proposal.impacts
            ),
        }


def ensure_read_only_scenario(proposal: ScenarioProposal) -> ScenarioProposal:
    if proposal.authoritative_mutation_allowed:
        raise ValueError("SCENARIO_CANNOT_MUTATE_AUTHORITATIVE_STATE")
    return proposal
