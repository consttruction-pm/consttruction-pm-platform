import assert from "node:assert/strict";
import test from "node:test";

import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";
import {
  WorkspaceReadClient,
  WORKSPACE_CONTROL_ROOM_READ_VERSION,
} from "./workspace-read-api.js";

const context: ProjectContext = {
  tenant_id: "tenant-1",
  project_id: "project-1",
  revision: 4,
};

class StubTransport implements ApiTransport {
  constructor(private readonly data: unknown) {}
  async get<T>(): Promise<ApiResult<T>> {
    return { ok: true, data: this.data as T };
  }
  async post<TRequest, TResponse>(): Promise<ApiResult<TResponse>> {
    throw new Error("POST_NOT_EXPECTED");
  }
}

test("workspace read hydrates procurement workflow records without calculations", async () => {
  const snapshot = {
    contract_version: WORKSPACE_CONTROL_ROOM_READ_VERSION,
    context,
    workspace: {
      contract_version: "workspace-control-room.v1",
      context,
      columns: [],
      activities: [{
        id: "A-1",
        wbs_id: "WBS-1",
        code: "A-1",
        name: "Concrete",
        cells: {},
        gantt: null,
      }],
    },
    control_intelligence: null,
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
    procurement_rfqs: [{
      contract_version: "procurement-rfq.v1",
      rfq_id: "RFQ-1",
      scope: {
        tenant_id: context.tenant_id,
        project_id: context.project_id,
        project_revision: context.revision,
      },
      status: "issued",
      title_key: "rfq.concrete",
      requested_by: "buyer-1",
      due_at: null,
      items: [{
        item_id: "I-1",
        description_key: "concrete",
        quantity: "100",
        unit: "m3",
        activity_ids: ["A-1"],
      }],
      supplier_ids: ["S-1", "S-2"],
      audit: {
        created_by: "buyer-1",
        created_at: "2026-09-27T06:00:00Z",
        updated_at: "2026-09-27T07:00:00Z",
      },
    }],
    procurement_quotes: [{
      contract_version: "procurement-quote.v1",
      quote_id: "Q-1",
      scope: {
        tenant_id: context.tenant_id,
        project_id: context.project_id,
        project_revision: context.revision,
      },
      rfq_id: "RFQ-1",
      supplier_id: "S-1",
      status: "submitted",
      currency: "USD",
      valid_until: "2026-10-01",
      items: [{
        item_id: "I-1",
        description_key: "concrete",
        quantity: "100",
        unit: "m3",
        unit_price: "25.00",
        activity_ids: ["A-1"],
      }],
      audit: {
        created_by: "buyer-1",
        created_at: "2026-09-27T06:00:00Z",
        updated_at: "2026-09-27T07:00:00Z",
      },
      evidence_refs: [{
        source_id: "quote-doc-1",
        source_type: "document",
        locator: "/docs/quote-1",
        revision: 1,
      }],
    }],
    procurement_bid_comparisons: [],
    purchase_orders: [],
    procurement_commitments: [],
    procurement_deliveries: [],
  };

  const result = await new WorkspaceReadClient(new StubTransport(snapshot)).load(context);

  assert.equal(result.ok, true);
  if (!result.ok) throw new Error("expected success");
  assert.equal(result.data.procurementRecords.length, 2);
  assert.equal(result.data.procurementRecords[0]?.type, "rfq");
  assert.equal(result.data.procurementRecords[1]?.type, "quote");
  assert.equal(result.data.procurementRecords[1]?.activityIds[0], "A-1");
  assert.equal(result.data.procurementRecords[1]?.amount, null);
});
