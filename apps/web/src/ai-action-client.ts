import type { ApiResult, ApiTransport, ClientError, ProjectContext } from "./client.js";

export const AI_ACTION_CONTRACT_VERSION = "ai-action-runtime.v1" as const;

export type AIActionProposal = Readonly<{
  proposal_id: string;
  tool_name: string;
  action: string;
  status: string;
  requires_human_approval: boolean;
  requested_by: string;
  evidence_refs: readonly string[];
  project_revision_id: string;
  resource_domain: string;
  payload: Readonly<Record<string, unknown>>;
  result: Readonly<Record<string, unknown>> | null;
  created_at: string;
  updated_at: string;
  decided_by: string | null;
  is_stale: boolean;
  execution_verification?: AIActionExecutionVerification | null;
}>;

export type AIActionProposalList = Readonly<{
  contract_version: typeof AI_ACTION_CONTRACT_VERSION;
  proposals: readonly AIActionProposal[];
}>;

export type AIActionExecutionVerification = Readonly<{
  contract_version: "ai-action-execution-verification.v1";
  status: "COMPUTED" | "UNAVAILABLE" | "FAILED";
  reason_code: string | null;
  activity: Readonly<{
    activity_id: string;
    start: string;
    finish: string;
    duration: number | null;
    duration_unit: string;
    critical: boolean | null;
  }> | null;
  project_finish: string | null;
  calculation_run_identity: string | null;
  snapshot: Readonly<{
    snapshot_id: string;
    snapshot_hash: string;
    calculation_identity: string;
  }> | null;
  query_id: string | null;
}>;

export type AIActionMutationResult = Readonly<{
  contract_version: typeof AI_ACTION_CONTRACT_VERSION;
  proposal_id: string;
  status: string;
  decided_by?: string | null;
  result?: Readonly<Record<string, unknown>> | null;
  execution_verification?: AIActionExecutionVerification | null;
  execution_verification_stored?: boolean;
}>;

export type CreateActivityProposal = Readonly<{
  activity_id: string;
  name: string;
  duration_value: string;
  duration_unit: "working-day" | "working-hour";
}>;

export type UpdateActivityProposal = Readonly<{
  activity_id: string;
  expected_revision: number;
  name?: string;
  duration_value?: string;
  duration_unit?: "working-day" | "working-hour";
}>;

export type AIAssistantHistoryMessage = Readonly<{
  role: "user" | "assistant";
  content: string;
}>;

export type AIAssistantInputProvenance = Readonly<{
  channel: "voice";
  source: "microphone" | "imported_audio" | "manual_transcript";
  confidence: number | null;
}>;

export type AIAssistantCapabilities = Readonly<{
  contract_version: "ai-assistant-capabilities.v1";
  enabled: boolean;
  reason: string | null;
}>;

export type AIAssistantTurn = Readonly<{
  contract_version: "ai-assistant-turn.v1";
  kind: "message" | "clarification" | "action_proposal";
  message: string;
  proposal: AIActionProposal | null;
}>;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function invalidResponse<T>(): ApiResult<T> {
  const error: ClientError = {
    code: "INVALID_AI_ACTION_RESPONSE",
    retryable: false,
    message_key: "error.ai_action.invalid_response",
    available_actions: ["refresh"],
  };
  return { ok: false, error };
}

function parseProposal(value: unknown): AIActionProposal | null {
  if (!isRecord(value)) return null;
  const textFields = [
    "proposal_id", "tool_name", "action", "status", "requested_by",
    "project_revision_id", "resource_domain", "created_at", "updated_at",
  ] as const;
  if (textFields.some((key) => typeof value[key] !== "string" || !String(value[key]).trim())) return null;
  if (typeof value.requires_human_approval !== "boolean" || typeof value.is_stale !== "boolean") return null;
  if (!Array.isArray(value.evidence_refs) || value.evidence_refs.some((item) => typeof item !== "string")) return null;
  if (!isRecord(value.payload)) return null;
  if (value.result !== null && !isRecord(value.result)) return null;
  if (value.decided_by !== null && typeof value.decided_by !== "string") return null;
  let storedVerification: AIActionExecutionVerification | null | undefined;
  if (value.execution_verification !== undefined) {
    storedVerification = value.execution_verification === null
      ? null
      : parseVerification(value.execution_verification);
    if (storedVerification === null && value.execution_verification !== null) return null;
  }
  return Object.freeze({
    proposal_id: value.proposal_id as string,
    tool_name: value.tool_name as string,
    action: value.action as string,
    status: value.status as string,
    requires_human_approval: value.requires_human_approval,
    requested_by: value.requested_by as string,
    evidence_refs: Object.freeze([...(value.evidence_refs as string[])]),
    project_revision_id: value.project_revision_id as string,
    resource_domain: value.resource_domain as string,
    payload: Object.freeze({ ...value.payload }),
    result: value.result === null ? null : Object.freeze({ ...(value.result as Record<string, unknown>) }),
    created_at: value.created_at as string,
    updated_at: value.updated_at as string,
    decided_by: value.decided_by as string | null,
    is_stale: value.is_stale,
    ...(storedVerification !== undefined ? { execution_verification: storedVerification } : {}),
  });
}

function projectPath(context: ProjectContext): string {
  return `/api/projects/${encodeURIComponent(context.project_id)}/ai/actions`;
}

function nonEmptyText(value: unknown): value is string {
  return typeof value === "string" && Boolean(value.trim());
}

function parseVerification(value: unknown): AIActionExecutionVerification | null {
  if (!isRecord(value) || value.contract_version !== "ai-action-execution-verification.v1") return null;
  const status = value.status;
  if (status !== "COMPUTED" && status !== "UNAVAILABLE" && status !== "FAILED") return null;
  const reasonCode = value.reason_code;
  if (reasonCode !== null && !nonEmptyText(reasonCode)) return null;
  if (value.activity !== null && !isRecord(value.activity)) return null;
  if (value.snapshot !== null && !isRecord(value.snapshot)) return null;
  for (const field of [value.project_finish, value.calculation_run_identity, value.query_id]) {
    if (field !== null && typeof field !== "string") return null;
  }

  if (status === "COMPUTED") {
    const activity = value.activity;
    const snapshot = value.snapshot;
    if (!isRecord(activity) || !isRecord(snapshot) || reasonCode !== null) return null;
    const activityId = activity.activity_id;
    const start = activity.start;
    const finish = activity.finish;
    const durationUnit = activity.duration_unit;
    const duration = activity.duration;
    const critical = activity.critical;
    if (!nonEmptyText(activityId) || !nonEmptyText(start) ||
        !nonEmptyText(finish) || !nonEmptyText(durationUnit)) return null;
    if (duration !== null &&
        (typeof duration !== "number" || !Number.isFinite(duration) || duration < 0)) return null;
    if (critical !== null && typeof critical !== "boolean") return null;
    const snapshotId = snapshot.snapshot_id;
    const snapshotHash = snapshot.snapshot_hash;
    const calculationIdentity = snapshot.calculation_identity;
    const projectFinish = value.project_finish;
    const calculationRunIdentity = value.calculation_run_identity;
    const queryId = value.query_id;
    if (!nonEmptyText(snapshotId) || !nonEmptyText(snapshotHash) ||
        !nonEmptyText(calculationIdentity)) return null;
    if (!nonEmptyText(projectFinish) || !nonEmptyText(calculationRunIdentity) ||
        !nonEmptyText(queryId)) return null;
    return Object.freeze({
      contract_version: "ai-action-execution-verification.v1",
      status: "COMPUTED",
      reason_code: null,
      activity: Object.freeze({
        activity_id: activityId,
        start,
        finish,
        duration,
        duration_unit: durationUnit,
        critical,
      }),
      project_finish: projectFinish,
      calculation_run_identity: calculationRunIdentity,
      snapshot: Object.freeze({
        snapshot_id: snapshotId,
        snapshot_hash: snapshotHash,
        calculation_identity: calculationIdentity,
      }),
      query_id: queryId,
    });
  }

  if (!nonEmptyText(reasonCode)) return null;
  if (value.activity !== null || value.snapshot !== null || value.project_finish !== null ||
      value.calculation_run_identity !== null || value.query_id !== null) return null;
  return Object.freeze({
    contract_version: "ai-action-execution-verification.v1",
    status,
    reason_code: reasonCode,
    activity: null,
    project_finish: null,
    calculation_run_identity: null,
    snapshot: null,
    query_id: null,
  });
}

export class AIActionClient {
  private readonly transport: ApiTransport;

  constructor(transport: ApiTransport) {
    this.transport = transport;
  }

  async listProposals(context: ProjectContext): Promise<ApiResult<AIActionProposalList>> {
    const result = await this.transport.get<unknown>(
      `${projectPath(context)}/proposals`,
      context,
    );
    if (!result.ok) return result;
    const data = result.data;
    if (!isRecord(data) || data.contract_version !== AI_ACTION_CONTRACT_VERSION || !Array.isArray(data.proposals)) {
      return invalidResponse<AIActionProposalList>();
    }
    const proposals = data.proposals.map(parseProposal);
    if (proposals.some((proposal) => proposal === null)) return invalidResponse<AIActionProposalList>();
    return {
      ok: true,
      data: Object.freeze({
        contract_version: AI_ACTION_CONTRACT_VERSION,
        proposals: Object.freeze(proposals as AIActionProposal[]),
      }),
    };
  }

  async proposeActivity(
    context: ProjectContext,
    activity: CreateActivityProposal,
  ): Promise<ApiResult<AIActionProposal>> {
    const result = await this.transport.post<
      { expected_revision: number; tool_name: string; payload: CreateActivityProposal; evidence_refs: string[] },
      unknown
    >(
      `${projectPath(context)}/proposals`,
      {
        expected_revision: context.revision,
        tool_name: "activity.create",
        payload: activity,
        evidence_refs: [],
      },
      context,
    );
    if (!result.ok) return result;
    const data = result.data;
    if (!isRecord(data) || data.contract_version !== AI_ACTION_CONTRACT_VERSION || !isRecord(data.proposal)) {
      return invalidResponse<AIActionProposal>();
    }
    // Create responses omit list-only fields. Normalize only fields the server
    // authoritatively returned; don't copy identity or approval flags from input.
    const created = {
      ...data.proposal,
      status: data.status,
      result: null,
      updated_at: data.proposal.updated_at ?? data.proposal.created_at,
      requested_by: data.proposal.requested_by ?? "",
      decided_by: null,
      is_stale: String(data.proposal.project_revision_id) !== String(context.revision),
    };
    const proposal = parseProposal(created);
    if (!proposal) return invalidResponse<AIActionProposal>();
    return { ok: true, data: proposal };
  }

  async proposeActivityUpdate(
    context: ProjectContext,
    activity: UpdateActivityProposal,
  ): Promise<ApiResult<AIActionProposal>> {
    const result = await this.transport.post<
      { expected_revision: number; tool_name: string; payload: UpdateActivityProposal; evidence_refs: string[] },
      unknown
    >(
      `${projectPath(context)}/proposals`,
      {
        expected_revision: context.revision,
        tool_name: "activity.update",
        payload: activity,
        evidence_refs: [],
      },
      context,
    );
    if (!result.ok) return result;
    const data = result.data;
    if (!isRecord(data) || data.contract_version !== AI_ACTION_CONTRACT_VERSION || !isRecord(data.proposal)) {
      return invalidResponse<AIActionProposal>();
    }
    const created = {
      ...data.proposal,
      status: data.status,
      result: null,
      updated_at: data.proposal.updated_at ?? data.proposal.created_at,
      requested_by: data.proposal.requested_by ?? "",
      decided_by: null,
      is_stale: String(data.proposal.project_revision_id) !== String(context.revision),
    };
    const proposal = parseProposal(created);
    if (!proposal) return invalidResponse<AIActionProposal>();
    return { ok: true, data: proposal };
  }

  async getAssistantCapabilities(
    context: ProjectContext,
  ): Promise<ApiResult<AIAssistantCapabilities>> {
    const result = await this.transport.get<unknown>(
      `/api/projects/${encodeURIComponent(context.project_id)}/ai/assistant/capabilities`,
      context,
    );
    if (!result.ok) return result;
    const value = result.data;
    if (!isRecord(value) || value.contract_version !== "ai-assistant-capabilities.v1" ||
        typeof value.enabled !== "boolean" ||
        (value.reason !== null && (typeof value.reason !== "string" || !value.reason.trim()))) {
      return invalidResponse<AIAssistantCapabilities>();
    }
    return {
      ok: true,
      data: Object.freeze({
        contract_version: "ai-assistant-capabilities.v1",
        enabled: value.enabled,
        reason: value.reason === null ? null : value.reason,
      }),
    };
  }

  async sendAssistantTurn(
    context: ProjectContext,
    message: string,
    language: string,
    history: readonly AIAssistantHistoryMessage[] = [],
    input: AIAssistantInputProvenance | null = null,
  ): Promise<ApiResult<AIAssistantTurn>> {
    const result = await this.transport.post<{
      expected_revision: number;
      message: string;
      language: string;
      history: readonly AIAssistantHistoryMessage[];
      input?: AIAssistantInputProvenance;
    }, unknown>(
      `/api/projects/${encodeURIComponent(context.project_id)}/ai/assistant/turn`,
      {
        expected_revision: context.revision,
        message,
        language,
        history,
        ...(input === null ? {} : { input }),
      },
      context,
    );
    if (!result.ok) return result;
    const value = result.data;
    if (!isRecord(value) || value.contract_version !== "ai-assistant-turn.v1" ||
        typeof value.kind !== "string" ||
        !["message", "clarification", "action_proposal"].includes(value.kind) ||
        typeof value.message !== "string" ||
        !value.message.trim() ||
        value.message.length > 4000 ||
        !("proposal" in value) ||
        (value.proposal !== null && !isRecord(value.proposal))) {
      return invalidResponse<AIAssistantTurn>();
    }
    let proposal: AIActionProposal | null = null;
    if (value.proposal !== null) {
      proposal = parseProposal(value.proposal);
      if (!proposal) return invalidResponse<AIAssistantTurn>();
    }
    const kind = value.kind as AIAssistantTurn["kind"];
    if ((kind === "action_proposal") !== (proposal !== null)) {
      return invalidResponse<AIAssistantTurn>();
    }
    return {
      ok: true,
      data: Object.freeze({
        contract_version: "ai-assistant-turn.v1",
        kind,
        message: value.message,
        proposal,
      }),
    };
  }

  async decide(
    context: ProjectContext,
    proposalId: string,
    approved: boolean,
  ): Promise<ApiResult<AIActionMutationResult>> {
    const result = await this.transport.post<
      { expected_revision: number; approved: boolean },
      unknown
    >(
      `${projectPath(context)}/proposals/${encodeURIComponent(proposalId)}/decision`,
      { expected_revision: context.revision, approved },
      context,
    );
    if (!result.ok) return result;
    return this.parseMutation(result.data, false);
  }

  async execute(
    context: ProjectContext,
    proposalId: string,
    timezone: string | null = null,
  ): Promise<ApiResult<AIActionMutationResult>> {
    const request: { expected_revision: number; timezone?: string } = {
      expected_revision: context.revision,
    };
    if (typeof timezone === "string" && timezone.trim()) request.timezone = timezone.trim();
    const result = await this.transport.post<
      { expected_revision: number; timezone?: string },
      unknown
    >(
      `${projectPath(context)}/proposals/${encodeURIComponent(proposalId)}/execute`,
      request,
      context,
    );
    if (!result.ok) return result;
    return this.parseMutation(result.data, true);
  }

  private parseMutation(
    value: unknown,
    includeResult: boolean,
  ): ApiResult<AIActionMutationResult> {
    if (!isRecord(value) || value.contract_version !== AI_ACTION_CONTRACT_VERSION ||
        typeof value.proposal_id !== "string" || typeof value.status !== "string") {
      return invalidResponse<AIActionMutationResult>();
    }
    if (value.decided_by !== undefined && value.decided_by !== null && typeof value.decided_by !== "string") {
      return invalidResponse<AIActionMutationResult>();
    }
    if (includeResult && value.result !== undefined && value.result !== null && !isRecord(value.result)) {
      return invalidResponse<AIActionMutationResult>();
    }
    let verification: AIActionExecutionVerification | null | undefined;
    if (value.execution_verification !== undefined) {
      verification = value.execution_verification === null
        ? null
        : parseVerification(value.execution_verification);
      if (verification === null && value.execution_verification !== null) {
        return invalidResponse<AIActionMutationResult>();
      }
    }
    if (value.execution_verification_stored !== undefined &&
        typeof value.execution_verification_stored !== "boolean") {
      return invalidResponse<AIActionMutationResult>();
    }
    return {
      ok: true,
      data: Object.freeze({
        contract_version: AI_ACTION_CONTRACT_VERSION,
        proposal_id: value.proposal_id,
        status: value.status,
        ...(value.decided_by === undefined ? {} : { decided_by: value.decided_by as string | null }),
        ...(includeResult ? {
          result: value.result === null || value.result === undefined
            ? null
            : Object.freeze({ ...(value.result as Record<string, unknown>) }),
        } : {}),
        ...(includeResult && verification !== undefined
          ? { execution_verification: verification }
          : {}),
        ...(includeResult && value.execution_verification_stored !== undefined
          ? { execution_verification_stored: value.execution_verification_stored }
          : {}),
      }),
    };
  }
}
