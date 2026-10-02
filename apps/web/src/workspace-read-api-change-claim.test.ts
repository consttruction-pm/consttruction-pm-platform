import assert from "node:assert/strict";
import test from "node:test";

import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";
import {
  WORKSPACE_CONTROL_ROOM_READ_PATH,
  WORKSPACE_CONTROL_ROOM_READ_VERSION,
  WorkspaceReadClient,
  type WorkspaceControlRoomReadSnapshot,
} from "./workspace-read-api.js";

const context: ProjectContext = {
  tenant_id: "tenant-1",
  project_id: "project-1",
  revision: 7,
};

function workspaceSnapshot(): WorkspaceControlRoomReadSnapshot {
  return {
    contract_version: WORKSPACE_CONTROL_ROOM_READ_VERSION,
    context,
    workspace: {
      contract_version: "workspace-control-room.v1",
      context,
      columns: [{
        id: "activity_id",
        label: "Activity ID",
        data_type: "text",
        editable: false,
        formula: null,
        width: 120,
      }],
      activities: [{
        id: "A-101",
        wbs_id: "WBS-1",
        code: "A-101",
        name: "Foundation",
        cells: { activity_id: "A-101" },
        gantt: null,
      }],
    },
    control_intelligence: null,
    field_daily_logs: [],
    field_issues: [{
      contract_version: "field-issue.v1",
      issue_id: "issue-1",
      scope: {
        tenant_id: context.tenant_id,
        project_id: context.project_id,
        project_revision: context.revision,
      },
      category: "quality",
      severity: "high",
      status: "open",
      title_key: "issue.honeycombing",
      detail_key: "issue.detail",
      reported_by: "qc-1",
      location_key: "tower-a",
      activity_ids: ["A-101"],
      evidence_refs: [{
        source_id: "photo-1",
        source_type: "photo",
        locator: "/photos/1",
        revision: 7,
      }],
      audit: {
        created_by: "qc-1",
        created_at: "2026-09-27T06:00:00Z",
        updated_at: "2026-09-27T07:00:00Z",
      },
    }],
    field_timecards: [],
    equipment_status_reports: [],
    inspections: [],
    quality_records: [],
    safety_observations: [],
    punch_items: [],
    change_notices: [{
      contract_version: "change-notice.v1",
      notice_id: "N-1",
      scope: {
        tenant_id: context.tenant_id,
        project_id: context.project_id,
        project_revision: context.revision,
      },
      notice_type: "variation",
      status: "under_review",
      title_key: "notice.title",
      submitted_by: "user-1",
      evidence_refs: [{
        source_id: "doc-2",
        source_type: "document",
        locator: "/documents/change-1",
        revision: 7,
      }],
      audit: {
        created_by: "user-1",
        created_at: "2026-09-27T06:00:00Z",
        updated_at: "2026-09-27T07:00:00Z",
      },
    }],
    change_cases: [{
      contract_version: "change-case.v1",
      change_id: "CH-1",
      scope: {
        tenant_id: context.tenant_id,
        project_id: context.project_id,
        project_revision: context.revision,
      },
      change_type: "variation",
      status: "under_review",
      title_key: "change.title",
      initiated_by: "user-1",
      evidence_refs: [{
        source_id: "doc-2",
        source_type: "document",
        locator: "/documents/change-1",
        revision: 7,
      }],
      audit: {
        created_by: "user-1",
        created_at: "2026-09-27T06:00:00Z",
        updated_at: "2026-09-27T07:00:00Z",
      },
    }],
    claims: [{
      contract_version: "claim-record.v1",
      claim_id: "CL-1",
      scope: {
        tenant_id: context.tenant_id,
        project_id: context.project_id,
        project_revision: context.revision,
      },
      claim_type: "extension_of_time",
      status: "submitted",
      title_key: "claim.title",
      submitted_by: "user-1",
      evidence_refs: [{
        source_id: "doc-3",
        source_type: "document",
        locator: "/documents/claim-1",
        revision: 7,
      }],
      audit: {
        created_by: "user-1",
        created_at: "2026-09-27T06:00:00Z",
        updated_at: "2026-09-27T07:00:00Z",
      },
    }],
    change_claim_impacts: [{
      contract_version: "change-claim-impact.v1",
      link_id: "IMP-1",
      scope: {
        tenant_id: context.tenant_id,
        project_id: context.project_id,
        project_revision: context.revision,
      },
      record_type: "change",
      record_id: "CH-1",
      impacted_domain: "schedule",
      impacted_entity_type: "activity",
      impacted_entity_id: "A-101",
      impact_type: "potential_delay",
      schedule_reference: "A-101",
      cost_reference: "C-10",
      evidence_refs: [{
        source_id: "doc-2",
        source_type: "document",
        locator: "/documents/change-1",
        revision: 7,
      }],
      requires_application_approval: true,
    }],
  };
}

class StubTransport implements ApiTransport {
  public path = "";
  public context: ProjectContext | null = null;

  constructor(private readonly result: ApiResult<WorkspaceControlRoomReadSnapshot>) {}

  async get<T>(path: string, contextValue: ProjectContext): Promise<ApiResult<T>> {
    this.path = path;
    this.context = contextValue;
    if (path.includes("/p6/fields/")) {
      return { ok: true, data: { registry_version: "p6-field-registry.v1", reference_product: "Oracle Primavera P6 Professional", reference_version: "test", status: "seeded_not_certified", fields: [] } } as ApiResult<T>;
    }
    return this.result as ApiResult<T>;
  }

  async post<TRequest, TResponse>(): Promise<ApiResult<TResponse>> {
    throw new Error("POST_NOT_EXPECTED");
  }
}

test("workspace read client hydrates the control room and field issue projection", async () => {
  const transport = new StubTransport({ ok: true, data: workspaceSnapshot() });
  const result = await new WorkspaceReadClient(transport).load(context, {
    locale: "fa",
    calendarMode: "jalali",
  });

  assert.equal(result.ok, true);
  if (!result.ok) throw new Error("expected success");
  assert.equal(result.data.activities[0]?.id, "A-101");
  assert.equal(result.data.fieldIssues[0]?.issueId, "issue-1");
  assert.equal(result.data.changeNotices[0]?.noticeId, "N-1");
  assert.equal(result.data.changeCases[0]?.changeId, "CH-1");
  assert.equal(result.data.claims[0]?.claimId, "CL-1");
  assert.equal(result.data.changeClaimImpacts[0]?.linkId, "IMP-1");
  assert.equal(result.data.locale, "fa");
  assert.equal(result.data.direction, "rtl");
  assert.equal(result.data.calendarMode, "jalali");
  assert.equal(transport.path, WORKSPACE_CONTROL_ROOM_READ_PATH);
  assert.deepEqual(transport.context, context);
});

test("workspace read client preserves API errors without masking them", async () => {
  const transport = new StubTransport({
    ok: false,
    error: {
      code: "FORBIDDEN",
      retryable: false,
      message_key: "error.forbidden",
      available_actions: [],
    },
  });

  const result = await new WorkspaceReadClient(transport).load(context);

  assert.equal(result.ok, false);
  if (result.ok) throw new Error("expected API error");
  assert.equal(result.error.code, "FORBIDDEN");
});

test("workspace read client rejects stale envelope scope with a stable error", async () => {
  const snapshot = workspaceSnapshot();
  const transport = new StubTransport({
    ok: true,
    data: {
      ...snapshot,
      context: { ...context, revision: 6 },
    },
  });

  const result = await new WorkspaceReadClient(transport).load(context);

  assert.equal(result.ok, false);
  if (result.ok) throw new Error("expected stale scope error");
  assert.equal(result.error.code, "STALE_WORKSPACE_READ_SCOPE");
});

test("workspace read client rejects unsupported envelope versions", async () => {
  const snapshot = workspaceSnapshot();
  const transport = new StubTransport({
    ok: true,
    data: {
      ...snapshot,
      contract_version: "workspace-control-room-read.v99",
    } as never,
  });

  const result = await new WorkspaceReadClient(transport).load(context);

  assert.equal(result.ok, false);
  if (result.ok) throw new Error("expected version error");
  assert.equal(result.error.code, "UNSUPPORTED_WORKSPACE_READ_CONTRACT");
});
