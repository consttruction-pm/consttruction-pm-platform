import assert from "node:assert/strict";
import test from "node:test";

import type { ProjectContext, ApiResult, ApiTransport } from "./client.js";
import {
  WorkspaceReadClient,
  WORKSPACE_CONTROL_ROOM_READ_VERSION,
  type WorkspaceControlRoomReadSnapshot,
} from "./workspace-read-api.js";

const context: ProjectContext = {
  tenant_id: "tenant-1",
  project_id: "project-1",
  revision: 8,
};

const source = {
  source_id: "control-1",
  source_type: "schedule",
  locator: "/control/1",
  revision: 8,
};

class StubTransport implements ApiTransport {
  constructor(private readonly payload: unknown) {}

  async get<T>(): Promise<ApiResult<T>> {
    return { ok: true, data: this.payload as T };
  }

  async post<TRequest, TResponse>(): Promise<ApiResult<TResponse>> {
    throw new Error("POST_NOT_EXPECTED");
  }
}

function completeEnvelope(): WorkspaceControlRoomReadSnapshot {
  return {
    contract_version: WORKSPACE_CONTROL_ROOM_READ_VERSION,
    context,
    workspace: {
      contract_version: "workspace-control-room.v1",
      context,
      columns: [],
      activities: [],
    },
    control_intelligence: {
      contract_version: "control-intelligence-result.v1",
      result_id: "result-1",
      scope: {
        tenant_id: context.tenant_id,
        project_id: context.project_id,
        project_revision: context.revision,
      },
      generated_at: "2026-09-27T10:00:00Z",
      summary_key: "control.summary",
      findings: [{
        finding_id: "f-1",
        domain: "schedule",
        severity: "warning",
        title_key: "finding.title",
        detail_key: "finding.detail",
        source_refs: [source],
      }],
      metrics: { schedule_variance: -2 },
      source_refs: [source],
      proposed_actions: [{
        action_id: "a-1",
        action_type: "schedule_review",
        title_key: "action.review",
        source_refs: [source],
        requires_approval: true,
      }],
    },
    field_daily_logs: [],
    field_issues: [],
    field_timecards: [],
    equipment_status_reports: [],
    inspections: [],
    quality_records: [],
    safety_observations: [],
    punch_items: [],
    change_notices: [],
    change_cases: [],
    claims: [],
    change_claim_impacts: [],
    documents: [],
    procurement_rfqs: [],
    procurement_quotes: [],
    procurement_bid_comparisons: [],
    purchase_orders: [],
    procurement_commitments: [],
    procurement_deliveries: [],
  };
}

test("full control-room read envelope hydrates every P0 collection boundary", async () => {
  const result = await new WorkspaceReadClient(
    new StubTransport(completeEnvelope()),
  ).load(context, { locale: "fa", calendarMode: "jalali" });

  assert.equal(result.ok, true);
  if (!result.ok) throw new Error("expected full read success");

  assert.equal(result.data.context.project_id, "project-1");
  assert.equal(result.data.activities.length, 0);
  assert.equal(result.data.smartGuide?.resultId, "result-1");
  assert.equal(result.data.smartGuide?.approvalRequiredCount, 1);
  assert.equal(result.data.fieldIssues.length, 0);
  assert.equal(result.data.changeCases.length, 0);
  assert.equal(result.data.documents.length, 0);
  assert.equal(result.data.procurementRecords.length, 0);
});

test("full control-room read rejects a non-array P0 collection", async () => {
  const payload = completeEnvelope();
  const invalid = {
    ...payload,
    procurement_rfqs: null,
  } as unknown as WorkspaceControlRoomReadSnapshot;

  const result = await new WorkspaceReadClient(
    new StubTransport(invalid),
  ).load(context);

  assert.equal(result.ok, false);
  if (result.ok) throw new Error("expected invalid collection rejection");
  assert.equal(result.error.code, "INVALID_WORKSPACE_READ_COLLECTION");
});
