import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";
import { createWorkspaceState, setSmartGuide, setControlSummary, setDocuments, setProcurementRecords, setFieldAssurance, setFieldIssues, setFieldOperations, setSiteDailyLogs, setChangeClaimRecords, withActivities, type WorkspaceCalendarMode, type WorkspaceLocale, type WorkspaceState } from "./workspace-model.js";
import { workspaceActivitiesFromSnapshot, type WorkspaceControlRoomSnapshot } from "./workspace-contract.js";
import { projectControlIntelligence, type ControlRoomIntelligenceSnapshot } from "./workspace-control-intelligence.js";
import { projectSmartGuide } from "./workspace-smart-guide.js";
import { projectSiteDailyLog, type SiteDailyLogSnapshot } from "./workspace-site-log.js";
import { projectFieldIssue, type FieldIssueSnapshot } from "./workspace-field-issues.js";
import { projectChangeNotice, projectChangeCase, projectClaimRecord, projectChangeClaimImpact, type ChangeNoticeSnapshot, type ChangeCaseSnapshot, type ClaimRecordSnapshot, type ChangeClaimImpactSnapshot } from "./workspace-change-claim.js";
import { projectDocument, type DocumentSnapshot } from "./workspace-document.js";
import { projectProcurementRFQ, projectProcurementQuote, projectProcurementBidComparison, projectPurchaseOrder, projectProcurementCommitment, projectProcurementDelivery, type ProcurementRFQSnapshot, type ProcurementQuoteSnapshot, type ProcurementBidComparisonSnapshot, type PurchaseOrderSnapshot, type ProcurementCommitmentSnapshot, type ProcurementDeliverySnapshot } from "./workspace-procurement.js";
import { projectTimecard, projectEquipmentStatus, type EquipmentStatusSnapshot, type FieldTimecardSnapshot } from "./workspace-field-ops.js";
import {
  projectInspection,
  projectQualityRecord,
  projectSafetyObservation,
  projectPunchItem,
  type InspectionSnapshot,
  type QualityRecordSnapshot,
  type SafetyObservationSnapshot,
  type PunchItemSnapshot,
} from "./workspace-field-assurance.js";

export const WORKSPACE_CONTROL_ROOM_READ_VERSION = "workspace-control-room-read.v1" as const;
export const WORKSPACE_CONTROL_ROOM_READ_PATH = "/api/v1/workspace/control-room/read" as const;

export type WorkspaceControlRoomReadSnapshot = {
  contract_version: typeof WORKSPACE_CONTROL_ROOM_READ_VERSION;
  context: ProjectContext;
  workspace: WorkspaceControlRoomSnapshot;
  control_intelligence?: ControlRoomIntelligenceSnapshot | null;
  field_daily_logs: readonly SiteDailyLogSnapshot[];
  field_issues: readonly FieldIssueSnapshot[];
  field_timecards: readonly FieldTimecardSnapshot[];
  equipment_status_reports: readonly EquipmentStatusSnapshot[];
  inspections: readonly InspectionSnapshot[];
  quality_records: readonly QualityRecordSnapshot[];
  safety_observations: readonly SafetyObservationSnapshot[];
  punch_items: readonly PunchItemSnapshot[];
  change_notices?: readonly ChangeNoticeSnapshot[];
  change_cases?: readonly ChangeCaseSnapshot[];
  claims?: readonly ClaimRecordSnapshot[];
  change_claim_impacts?: readonly ChangeClaimImpactSnapshot[];
  documents?: readonly DocumentSnapshot[];
  procurement_rfqs?: readonly ProcurementRFQSnapshot[];
  procurement_quotes?: readonly ProcurementQuoteSnapshot[];
  procurement_bid_comparisons?: readonly ProcurementBidComparisonSnapshot[];
  purchase_orders?: readonly PurchaseOrderSnapshot[];
  procurement_commitments?: readonly ProcurementCommitmentSnapshot[];
  procurement_deliveries?: readonly ProcurementDeliverySnapshot[];
};

export type WorkspaceReadOptions = {
  locale?: WorkspaceLocale;
  calendarMode?: WorkspaceCalendarMode;
  path?: string;
};

export class WorkspaceReadClient {
  constructor(private readonly transport: ApiTransport) {}

  async load(
    context: ProjectContext,
    options: WorkspaceReadOptions = {},
  ): Promise<ApiResult<WorkspaceState>> {
    const result = await this.transport.get<WorkspaceControlRoomReadSnapshot>(
      options.path ?? WORKSPACE_CONTROL_ROOM_READ_PATH,
      context,
    );

    if (!result.ok) return result;

    try {
      validateReadEnvelope(result.data, context);
      const locale = options.locale ?? "en";
      const calendarMode = options.calendarMode ?? "gregorian";
      let state = createWorkspaceState(context, locale, calendarMode);
      const defaultColumns = state.columns;
      state = {
        ...state,
        columns: result.data.workspace.columns.map((column) => {
          const presentation = defaultColumns.find((item) => item.id === column.id);
          return {
            id: column.id,
            label: column.label,
            dataType: column.data_type,
            editable: column.editable,
            formula: column.formula,
            width: column.width,
            alignment: presentation?.alignment ?? "start",
            pinned: presentation?.pinned ?? false,
            frozen: presentation?.frozen ?? false,
          };
        }),
      };

      const activities = workspaceActivitiesFromSnapshot(result.data.workspace);
      state = withActivities(state, activities);

      const summary = result.data.control_intelligence
        ? projectControlIntelligence(result.data.control_intelligence, context)
        : null;
      state = setControlSummary(state, summary);
      state = setSmartGuide(
        state,
        result.data.control_intelligence
          ? projectSmartGuide(result.data.control_intelligence, context, "control-room", locale)
          : null,
      );

      state = setSiteDailyLogs(
        state,
        result.data.field_daily_logs.map((snapshot) => projectSiteDailyLog(snapshot, context)),
      );
      state = setFieldIssues(
        state,
        result.data.field_issues.map((snapshot) => projectFieldIssue(snapshot, {
          tenant_id: context.tenant_id,
          project_id: context.project_id,
          project_revision: context.revision,
        })),
      );
      state = setFieldOperations(
        state,
        result.data.field_timecards.map((snapshot) => projectTimecard(snapshot, toProjectScope(context))),
        result.data.equipment_status_reports.map((snapshot) => projectEquipmentStatus(snapshot, toProjectScope(context))),
      );
      state = setChangeClaimRecords(
        state,
        {
          changeNotices: (result.data.change_notices ?? []).map((snapshot) => projectChangeNotice(snapshot, toProjectScope(context))),
          changeCases: (result.data.change_cases ?? []).map((snapshot) => projectChangeCase(snapshot, toProjectScope(context))),
          claims: (result.data.claims ?? []).map((snapshot) => projectClaimRecord(snapshot, toProjectScope(context))),
          changeClaimImpacts: (result.data.change_claim_impacts ?? []).map((snapshot) => projectChangeClaimImpact(snapshot, toProjectScope(context))),
        },
      );

      state = setDocuments(
        state,
        (result.data.documents ?? []).map((snapshot) => projectDocument(snapshot, toProjectScope(context))),
      );

      const procurementScope = toProjectScope(context);
      state = setProcurementRecords(
        state,
        [
          ...(result.data.procurement_rfqs ?? []).map((snapshot) => projectProcurementRFQ(snapshot, procurementScope)),
          ...(result.data.procurement_quotes ?? []).map((snapshot) => projectProcurementQuote(snapshot, procurementScope)),
          ...(result.data.procurement_bid_comparisons ?? []).map((snapshot) => projectProcurementBidComparison(snapshot, procurementScope)),
          ...(result.data.purchase_orders ?? []).map((snapshot) => projectPurchaseOrder(snapshot, procurementScope)),
          ...(result.data.procurement_commitments ?? []).map((snapshot) => projectProcurementCommitment(snapshot, procurementScope)),
          ...(result.data.procurement_deliveries ?? []).map((snapshot) => projectProcurementDelivery(snapshot, procurementScope)),
        ],
      );

      state = setFieldAssurance(state, {
        inspections: result.data.inspections.map((snapshot) => projectInspection(snapshot, {
          tenant_id: context.tenant_id,
          project_id: context.project_id,
          project_revision: context.revision,
        })),
        qualityRecords: result.data.quality_records.map((snapshot) => projectQualityRecord(snapshot, {
          tenant_id: context.tenant_id,
          project_id: context.project_id,
          project_revision: context.revision,
        })),
        safetyObservations: result.data.safety_observations.map((snapshot) => projectSafetyObservation(snapshot, {
          tenant_id: context.tenant_id,
          project_id: context.project_id,
          project_revision: context.revision,
        })),
        punchItems: result.data.punch_items.map((snapshot) => projectPunchItem(snapshot, {
          tenant_id: context.tenant_id,
          project_id: context.project_id,
          project_revision: context.revision,
        })),
      });

      return { ok: true, data: state };
    } catch (error) {
      const code = error instanceof Error ? error.message : "INVALID_WORKSPACE_READ";
      return {
        ok: false,
        error: {
          code,
          retryable: false,
          message_key: "error.workspace_read.invalid_payload",
          available_actions: ["refresh"],
        },
      };
    }
  }
}

function toProjectScope(context: ProjectContext): { tenant_id: string; project_id: string; project_revision: number } {
  return {
    tenant_id: context.tenant_id,
    project_id: context.project_id,
    project_revision: context.revision,
  };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function validateReadEnvelope(
  snapshot: WorkspaceControlRoomReadSnapshot,
  context: ProjectContext,
): void {
  if (!isRecord(snapshot)) {
    throw new Error("INVALID_WORKSPACE_READ_ENVELOPE");
  }
  if (snapshot.contract_version !== WORKSPACE_CONTROL_ROOM_READ_VERSION) {
    throw new Error("UNSUPPORTED_WORKSPACE_READ_CONTRACT");
  }
  if (!isRecord(snapshot.context)) {
    throw new Error("INVALID_WORKSPACE_READ_CONTEXT");
  }
  if (
    snapshot.context.tenant_id !== context.tenant_id ||
    snapshot.context.project_id !== context.project_id ||
    snapshot.context.revision !== context.revision
  ) {
    throw new Error("STALE_WORKSPACE_READ_SCOPE");
  }
  if (!isRecord(snapshot.workspace)) {
    throw new Error("INVALID_WORKSPACE_READ_WORKSPACE");
  }
  if (snapshot.workspace.contract_version !== "workspace-control-room.v1") {
    throw new Error("UNSUPPORTED_WORKSPACE_CONTRACT");
  }
  if (
    !isRecord(snapshot.workspace.context) ||
    snapshot.workspace.context.tenant_id !== context.tenant_id ||
    snapshot.workspace.context.project_id !== context.project_id ||
    snapshot.workspace.context.revision !== context.revision
  ) {
    throw new Error("STALE_WORKSPACE_SNAPSHOT_SCOPE");
  }

  const requiredCollections = [
    snapshot.field_daily_logs,
    snapshot.field_issues,
    snapshot.field_timecards,
    snapshot.equipment_status_reports,
    snapshot.inspections,
    snapshot.quality_records,
    snapshot.safety_observations,
    snapshot.punch_items,
  ];
  if (requiredCollections.some((collection) => !Array.isArray(collection))) {
    throw new Error("INVALID_WORKSPACE_READ_COLLECTION");
  }

  const optionalCollections = [
    snapshot.change_notices,
    snapshot.change_cases,
    snapshot.claims,
    snapshot.change_claim_impacts,
    snapshot.documents,
    snapshot.procurement_rfqs,
    snapshot.procurement_quotes,
    snapshot.procurement_bid_comparisons,
    snapshot.purchase_orders,
    snapshot.procurement_commitments,
    snapshot.procurement_deliveries,
  ];
  if (optionalCollections.some((collection) => collection !== undefined && !Array.isArray(collection))) {
    throw new Error("INVALID_WORKSPACE_READ_COLLECTION");
  }
}
