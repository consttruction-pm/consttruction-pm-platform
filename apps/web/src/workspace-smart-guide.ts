import {
  projectControlIntelligence,
  type ControlRoomIntelligenceSnapshot,
  type WorkspaceControlSummary,
} from "./workspace-control-intelligence.js";

export const SMART_GUIDE_VERSION = "smart-guide.v1" as const;
export const SCHEDULE_QUERY_VERSION = "schedule-query.v1" as const;

export type SmartGuideModule =
  | "control-room"
  | "schedule"
  | "progress"
  | "resources"
  | "cost"
  | "documents"
  | "field"
  | "commercial"
  | "procurement";

export type SmartGuideLocale = string;

export type WorkspaceSmartGuide = Readonly<{
  contractVersion: typeof SMART_GUIDE_VERSION;
  module: SmartGuideModule;
  locale: SmartGuideLocale;
  textDirection: "auto" | "ltr" | "rtl";
  resultId: string;
  generatedAt: string;
  summaryKey: string;
  findings: WorkspaceControlSummary["findings"];
  proposedActions: readonly {
    actionId: string;
    actionType: string;
    titleKey: string;
    requiresApproval: boolean;
    sourceCount: number;
  }[];
  sourceCount: number;
  approvalRequiredCount: number;
}>;

export type ScheduleQueryKind = "fact" | "explanation" | "filter" | "scenario";

export type ScheduleQueryRequest = Readonly<{
  contract_version: typeof SCHEDULE_QUERY_VERSION;
  query_id: string;
  scope: {
    tenant_id: string;
    project_id: string;
    project_revision: number;
  };
  requested_by: string;
  query_text: string;
  kind: ScheduleQueryKind;
  language: string;
  constraints?: Record<string, unknown>;
}>;

export function projectSmartGuide(
  snapshot: ControlRoomIntelligenceSnapshot,
  context: { tenant_id: string; project_id: string; revision: number },
  module: SmartGuideModule,
  locale: SmartGuideLocale,
  textDirection: "auto" | "ltr" | "rtl" = "auto",
): WorkspaceSmartGuide {
  const summary = projectControlIntelligence(snapshot, context);

  if (!module) {
    throw new Error("INVALID_SMART_GUIDE_MODULE");
  }
  if (!locale.trim()) {
    throw new Error("INVALID_SMART_GUIDE_LOCALE");
  }

  const proposedActions = summary.proposedActions.map((action) =>
    Object.freeze({
      actionId: action.action_id,
      actionType: action.action_type,
      titleKey: action.title_key,
      requiresApproval: action.requires_approval,
      sourceCount: action.source_refs.length,
    }),
  );

  return Object.freeze({
    contractVersion: SMART_GUIDE_VERSION,
    module,
    locale,
    textDirection,
    resultId: summary.resultId,
    generatedAt: summary.generatedAt,
    summaryKey: summary.summaryKey,
    findings: summary.findings.map((finding) =>
      Object.freeze({
        ...finding,
        source_refs: Object.freeze([...finding.source_refs]),
      }),
    ),
    proposedActions: Object.freeze(proposedActions),
    sourceCount: snapshot.source_refs.length,
    approvalRequiredCount: proposedActions.filter((action) => action.requiresApproval).length,
  });
}

export function buildScheduleQueryRequest(
  context: { tenant_id: string; project_id: string; revision: number },
  requestedBy: string,
  queryId: string,
  queryText: string,
  kind: ScheduleQueryKind,
  language: string,
  constraints?: Record<string, unknown>,
): ScheduleQueryRequest {
  if (!requestedBy.trim() || !queryId.trim() || !queryText.trim() || !language.trim()) {
    throw new Error("INVALID_SCHEDULE_QUERY_REQUEST");
  }
  if (!["fact", "explanation", "filter", "scenario"].includes(kind)) {
    throw new Error("INVALID_SCHEDULE_QUERY_KIND");
  }
  if (
    !context.tenant_id ||
    !context.project_id ||
    !Number.isInteger(context.revision) ||
    context.revision < 0 ||
    context.revision > 9_007_199_254_740_991
  ) {
    throw new Error("INVALID_SCHEDULE_QUERY_SCOPE");
  }

  return Object.freeze({
    contract_version: SCHEDULE_QUERY_VERSION,
    query_id: queryId,
    scope: Object.freeze({
      tenant_id: context.tenant_id,
      project_id: context.project_id,
      project_revision: context.revision,
    }),
    requested_by: requestedBy,
    query_text: queryText,
    kind,
    language,
    ...(constraints === undefined ? {} : { constraints: Object.freeze({ ...constraints }) }),
  });
}
