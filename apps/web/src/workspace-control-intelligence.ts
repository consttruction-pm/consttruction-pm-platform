export type ControlRoomSeverity = "info" | "warning" | "critical";

export type ControlRoomDomain =
  | "schedule"
  | "progress"
  | "evm"
  | "resource"
  | "cost"
  | "document"
  | "change"
  | "claim"
  | "procurement"
  | "field";

export const CONTROL_INTELLIGENCE_RESULT_VERSION = "control-intelligence-result.v1" as const;

export type ControlRoomSourceRef = {
  source_id: string;
  source_type: string;
  locator: string;
  revision: number;
  excerpt_key?: string | null;
  content_hash?: string | null;
};

export type ControlRoomFinding = {
  finding_id: string;
  domain: ControlRoomDomain;
  severity: ControlRoomSeverity;
  title_key: string;
  detail_key: string;
  source_refs: readonly ControlRoomSourceRef[];
};

export type ControlRoomProposedAction = {
  action_id: string;
  action_type: string;
  title_key: string;
  source_refs: readonly ControlRoomSourceRef[];
  requires_approval: boolean;
};

export type ControlRoomIntelligenceSnapshot = {
  contract_version: typeof CONTROL_INTELLIGENCE_RESULT_VERSION;
  result_id: string;
  scope: {
    tenant_id: string;
    project_id: string;
    project_revision: number;
  };
  generated_at: string;
  summary_key: string;
  findings: readonly ControlRoomFinding[];
  metrics: Readonly<Record<string, number>>;
  source_refs: readonly ControlRoomSourceRef[];
  proposed_actions: readonly ControlRoomProposedAction[];
};

export type WorkspaceControlSummary = {
  resultId: string;
  generatedAt: string;
  summaryKey: string;
  metrics: Readonly<Record<string, number>>;
  findings: readonly ControlRoomFinding[];
  proposedActions: readonly ControlRoomProposedAction[];
};

export function projectControlIntelligence(
  snapshot: ControlRoomIntelligenceSnapshot,
  context: { tenant_id: string; project_id: string; revision: number },
): WorkspaceControlSummary {
  if (snapshot.contract_version !== CONTROL_INTELLIGENCE_RESULT_VERSION) {
    throw new Error("UNSUPPORTED_CONTROL_INTELLIGENCE_CONTRACT");
  }
  if (
    snapshot.scope.tenant_id !== context.tenant_id ||
    snapshot.scope.project_id !== context.project_id ||
    snapshot.scope.project_revision !== context.revision
  ) {
    throw new Error("STALE_CONTROL_INTELLIGENCE_SCOPE");
  }
  if (
    !snapshot.result_id ||
    !snapshot.generated_at ||
    !Number.isFinite(Date.parse(snapshot.generated_at)) ||
    !snapshot.summary_key ||
    !snapshot.source_refs.length
  ) {
    throw new Error("INVALID_CONTROL_INTELLIGENCE_SNAPSHOT");
  }
  for (const [key, value] of Object.entries(snapshot.metrics)) {
    if (!key.trim() || !Number.isFinite(value)) {
      throw new Error("INVALID_CONTROL_INTELLIGENCE_METRIC");
    }
  }
  for (const finding of snapshot.findings) {
    if (
      !finding.finding_id ||
      !finding.title_key ||
      !finding.detail_key ||
      !finding.source_refs.length
    ) {
      throw new Error("INVALID_CONTROL_INTELLIGENCE_FINDING");
    }
  }
  for (const action of snapshot.proposed_actions) {
    if (!action.action_id || !action.action_type || !action.title_key) {
      throw new Error("INVALID_CONTROL_INTELLIGENCE_ACTION");
    }
    if (action.requires_approval && !action.source_refs.length) {
      throw new Error("APPROVAL_ACTION_SOURCE_REQUIRED");
    }
  }

  return Object.freeze({
    resultId: snapshot.result_id,
    generatedAt: snapshot.generated_at,
    summaryKey: snapshot.summary_key,
    metrics: Object.freeze({ ...snapshot.metrics }),
    findings: snapshot.findings.map((finding) => Object.freeze({ ...finding, source_refs: [...finding.source_refs] })),
    proposedActions: snapshot.proposed_actions.map((action) => Object.freeze({ ...action, source_refs: [...action.source_refs] })),
  });
}
