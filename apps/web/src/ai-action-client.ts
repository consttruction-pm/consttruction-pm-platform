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
}>;

export type AIActionProposalList = Readonly<{
  contract_version: typeof AI_ACTION_CONTRACT_VERSION;
  proposals: readonly AIActionProposal[];
}>;

export type AIActionMutationResult = Readonly<{
  contract_version: typeof AI_ACTION_CONTRACT_VERSION;
  proposal_id: string;
  status: string;
  decided_by?: string | null;
  result?: Readonly<Record<string, unknown>> | null;
}>;

export type CreateActivityProposal = Readonly<{
  activity_id: string;
  name: string;
  duration_value: string;
  duration_unit: "working-day" | "calendar-day" | "hour";
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
  });
}

function projectPath(context: ProjectContext): string {
  return `/api/projects/${encodeURIComponent(context.project_id)}/ai/actions`;
}

export class AIActionClient {
  constructor(private readonly transport: ApiTransport) {}

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
      updated_at: data.proposal.created_at,
      requested_by: data.proposal.requested_by ?? "",
      decided_by: null,
      is_stale: String(data.proposal.project_revision_id) !== String(context.revision),
    };
    const proposal = parseProposal(created);
    if (!proposal) return invalidResponse<AIActionProposal>();
    return { ok: true, data: proposal };
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
  ): Promise<ApiResult<AIActionMutationResult>> {
    const result = await this.transport.post<
      { expected_revision: number },
      unknown
    >(
      `${projectPath(context)}/proposals/${encodeURIComponent(proposalId)}/execute`,
      { expected_revision: context.revision },
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
      }),
    };
  }
}
