/**
 * HTTP client for the CUBI AI Workbench.
 *
 * Every call uses the shared transport so session cookies, CSRF headers,
 * timeouts and error codes behave exactly like the rest of the workspace. The
 * Workbench adds no second API convention.
 */
import { FetchApiTransport, type ApiResult, type ProjectContext } from "../client.js";

export type WorkbenchStudio = {
  id: string;
  status: string;
  service: string;
  intent: string;
  can_open: boolean;
  can_execute: boolean;
  blocked_reason: string | null;
  help_topic: string;
  help_status: string;
  help_url: string | null;
};

export type WorkbenchContext = {
  contract_version: string;
  environment: string;
  project: {
    project_id: string;
    name: string;
    revision: number;
    settings_revision: number;
    start_date: string | null;
    status: string;
    date_system: string;
  };
  data_date: string | null;
  actor: { user_id: string; roles: string[] };
  permissions: { can_read: boolean; can_propose: boolean };
  studios: WorkbenchStudio[];
};

export type WorkbenchQuestion = {
  id: string;
  prompt: string;
  options: { value: string; label: string }[];
  allow_unknown: boolean;
};

export type WorkbenchCommandPlan = {
  contract_version: string;
  correlation_id: string;
  command: string;
  intent: string;
  studio: string | null;
  status: string;
  can_open: boolean;
  can_execute: boolean;
  refusal: string | null;
  reason: string | null;
  missing_inputs: string[];
  questions: WorkbenchQuestion[];
  facts: string[];
  calculated: string[];
  assumptions: string[];
  recommendations: string[];
  objective: string | null;
  constraints: string[];
  evidence: string;
  project: { project_id: string; revision: number };
  resolved_at: string;
};

export type RiskRecord = {
  contract_version: string;
  risk_id: string;
  title: string;
  description: string;
  category: string;
  status: string;
  probability: number;
  impact: number;
  score: number;
  exposure_level: string;
  response_strategy: string;
  response_owner: string | null;
  response_due_date: string | null;
  owner: string;
  responsible_manager: string | null;
  date_identified: string;
  closure_note: string | null;
  revision: number;
};

export type RiskHistoryEvent = {
  contract_version: string;
  entity_type: string;
  entity_id: string;
  revision: number;
  event_type: string;
  actor_id: string;
  occurred_at: string;
  reason: string | null;
};


export type BaselineRecord = {
  baseline_id: string;
  name: string;
  baseline_type: string;
  source_revision: number;
  created_at: string;
  notes: string | null;
};

export type BaselineListEntry = {
  contract_version: string;
  kind: string;
  scope: { tenant_id: string; project_id: string; project_revision: number };
  baseline: BaselineRecord;
};

export type EarnedValueSnapshot = {
  contract_version: string;
  kind: string;
  scope: { tenant_id: string; project_id: string; project_revision: number };
  baseline_id: string;
  data_date: string;
  currency: string;
  pv_method: string;
  earned_value: {
    planned_value: string;
    earned_value: string;
    actual_cost: string;
    cost_variance: string;
    schedule_variance: string;
    cost_performance_index: string | null;
    schedule_performance_index: string | null;
    etc_method: string;
    budget_at_completion: string | null;
    estimate_to_complete: string;
    estimate_at_completion: string;
    variance_at_completion: string | null;
    performance_factor: string | null;
  };
};

export type WorkspaceActivityRow = {
  id: string;
  wbs_id?: string;
  code?: string;
  name?: string;
  cells?: Record<string, unknown>;
  gantt?: { start?: string; finish?: string; progressPercent?: number; critical?: boolean } | null;
};

export type WorkspaceWbsNode = {
  wbs_id: string;
  parent_wbs_id?: string | null;
  local_code?: string;
  code?: string;
  name?: string;
  sequence_number?: number;
};

export type WorkspaceRelationshipRow = {
  relationship_id?: string;
  id?: string;
};

/**
 * The cursor writes the canonical v2 workspace read contract, which names the
 * WBS collection `wbs_nodes`. `wbs` remains in the type only so an older
 * envelope can still be displayed without hiding rows.
 */
export type WorkspaceReadSnapshot = {
  contract_version: string;
  context: { tenant_id: string; project_id: string; revision: number };
  workspace: {
    activities?: WorkspaceActivityRow[];
    wbs_nodes?: WorkspaceWbsNode[];
    wbs?: WorkspaceWbsNode[];
    relationships?: WorkspaceRelationshipRow[];
  };
  control_intelligence?: {
    contract_version: string;
    result_id: string;
    scope: { tenant_id: string; project_id: string; project_revision: number };
    generated_at: string;
    summary_key: string;
    metrics: Record<string, number>;
    source_refs: { id?: string; kind?: string; label?: string }[];
  } | null;
};

export type AIActionProposal = {
  proposal_id: string;
  tool_name: string;
  action: string;
  status: string;
  requires_human_approval: boolean;
  requested_by: string;
  evidence_refs: string[];
  project_revision_id: string;
  resource_domain: string | null;
  payload: Record<string, unknown>;
  result: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
  decided_by: string | null;
  is_stale: boolean;
};

export type SessionInfo = {
  session_id: string;
  user_id: string;
  tenant_id: string;
  roles: string[];
  expires_at: string;
};

export class WorkbenchApi {
  constructor(
    private readonly transport: FetchApiTransport = new FetchApiTransport(
      typeof window === "undefined" ? "http://127.0.0.1" : window.location.origin,
    ),
  ) {}

  session(): Promise<ApiResult<SessionInfo>> {
    return this.transport.get<SessionInfo>("/api/session", {
      tenant_id: "",
      project_id: "",
      revision: 0,
    });
  }

  context(projectId: string): Promise<ApiResult<WorkbenchContext>> {
    return this.transport.get<WorkbenchContext>(
      `/api/projects/${encodeURIComponent(projectId)}/workbench/context`,
      { tenant_id: "", project_id: projectId, revision: 0 },
    );
  }

  command(
    projectId: string,
    payload: { command: string; locale: string; correlation_id: string },
    context: ProjectContext,
  ): Promise<ApiResult<WorkbenchCommandPlan>> {
    return this.transport.post<
      { command: string; locale: string; correlation_id: string },
      WorkbenchCommandPlan
    >(
      `/api/projects/${encodeURIComponent(projectId)}/workbench/command`,
      payload,
      context,
    );
  }

  risks(
    projectId: string,
    context: ProjectContext,
  ): Promise<ApiResult<{ contract_version: string; risks: RiskRecord[] }>> {
    return this.transport.get(
      `/api/projects/${encodeURIComponent(projectId)}/risks`,
      context,
    );
  }

  createRisk(
    projectId: string,
    body: Record<string, unknown>,
    context: ProjectContext,
    idempotencyKey: string,
  ): Promise<ApiResult<RiskRecord>> {
    return this.transport.post<Record<string, unknown>, RiskRecord>(
      `/api/projects/${encodeURIComponent(projectId)}/risks`,
      body,
      context,
      idempotencyKey,
    );
  }

  updateRisk(
    projectId: string,
    riskId: string,
    body: Record<string, unknown>,
    context: ProjectContext,
  ): Promise<ApiResult<RiskRecord>> {
    return this.transport.put<Record<string, unknown>, RiskRecord>(
      `/api/projects/${encodeURIComponent(projectId)}/risks/${encodeURIComponent(riskId)}`,
      body,
      context,
    );
  }

  riskHistory(
    projectId: string,
    riskId: string,
    context: ProjectContext,
  ): Promise<ApiResult<{ contract_version: string; events: RiskHistoryEvent[] }>> {
    return this.transport.get(
      `/api/projects/${encodeURIComponent(projectId)}/risks/${encodeURIComponent(riskId)}/history`,
      context,
    );
  }

  baselines(
    projectId: string,
    context: ProjectContext,
  ): Promise<ApiResult<{ contract_version: string; baselines: BaselineListEntry[] }>> {
    return this.transport.get(
      `/api/projects/${encodeURIComponent(projectId)}/p6/baselines`,
      context,
    );
  }

  earnedValue(
    projectId: string,
    body: { baseline_id: string; data_date: string; currency: string },
    context: ProjectContext,
  ): Promise<ApiResult<EarnedValueSnapshot>> {
    return this.transport.post<
      { baseline_id: string; data_date: string; currency: string },
      EarnedValueSnapshot
    >(
      `/api/projects/${encodeURIComponent(projectId)}/p6/earned-value`,
      body,
      context,
    );
  }

  proposals(
    projectId: string,
    context: ProjectContext,
  ): Promise<ApiResult<{ contract_version: string; proposals: AIActionProposal[] }>> {
    return this.transport.get(
      `/api/projects/${encodeURIComponent(projectId)}/ai/actions/proposals`,
      context,
    );
  }

  decideProposal(
    projectId: string,
    proposalId: string,
    body: { expected_revision: number; approved: boolean },
    context: ProjectContext,
  ): Promise<
    ApiResult<{ contract_version: string; proposal_id: string; status: string; decided_by: string | null }>
  > {
    return this.transport.post(
      `/api/projects/${encodeURIComponent(projectId)}/ai/actions/proposals/${encodeURIComponent(proposalId)}/decision`,
      body,
      context,
    );
  }

  executeProposal(
    projectId: string,
    proposalId: string,
    body: { expected_revision: number },
    context: ProjectContext,
  ): Promise<
    ApiResult<{
      contract_version: string;
      proposal_id: string;
      status: string;
      result: Record<string, unknown> | null;
    }>
  > {
    return this.transport.post(
      `/api/projects/${encodeURIComponent(projectId)}/ai/actions/proposals/${encodeURIComponent(proposalId)}/execute`,
      body,
      context,
    );
  }

  readWorkspace(
    projectId: string,
    context: ProjectContext,
  ): Promise<ApiResult<WorkspaceReadSnapshot>> {    return this.transport.get<WorkspaceReadSnapshot>(
      "/api/v2/workspace/control-room/read",
      { ...context, project_id: projectId },
    );
  }
}

export function newCorrelationId(prefix = "wb"): string {
  const random =
    typeof crypto !== "undefined" && "randomUUID" in crypto
      ? crypto.randomUUID().replace(/-/g, "").slice(0, 20)
      : Math.random().toString(36).slice(2, 12) + Date.now().toString(36);
  return `${prefix}-${random}`;
}
