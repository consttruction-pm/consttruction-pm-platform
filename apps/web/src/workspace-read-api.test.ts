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
    documents: [{
      document_id: "DOC-1",
      tenant_id: context.tenant_id,
      project_id: context.project_id,
      resource_type: "rfi",
      title: "RFI — foundation reinforcement",
      status: "submitted",
      storage_ref: "object://documents/DOC-1",
      content_hash: "sha256:" + "a".repeat(64),
      linked_entity_refs: ["A-101"],
      revision: context.revision,
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

test("workspace read client rejects malformed read context with a stable error", async () => {
  const snapshot = workspaceSnapshot();
  const transport = new StubTransport({
    ok: true,
    data: {
      ...snapshot,
      context: null,
    } as never,
  });

  const result = await new WorkspaceReadClient(transport).load(context);

  assert.equal(result.ok, false);
  if (result.ok) throw new Error("expected invalid context error");
  assert.equal(result.error.code, "INVALID_WORKSPACE_READ_CONTEXT");
});

test("workspace read client rejects malformed workspace with a stable error", async () => {
  const snapshot = workspaceSnapshot();
  const transport = new StubTransport({
    ok: true,
    data: {
      ...snapshot,
      workspace: null,
    } as never,
  });

  const result = await new WorkspaceReadClient(transport).load(context);

  assert.equal(result.ok, false);
  if (result.ok) throw new Error("expected invalid workspace error");
  assert.equal(result.error.code, "INVALID_WORKSPACE_READ_WORKSPACE");
});

test("workspace read client hydrates document workflow metadata and links", async () => {
  const transport = new StubTransport({ ok: true, data: workspaceSnapshot() });
  const result = await new WorkspaceReadClient(transport).load(context);

  assert.equal(result.ok, true);
  if (!result.ok) throw new Error("expected success");
  assert.equal(result.data.documents[0]?.documentId, "DOC-1");
  assert.equal(result.data.documents[0]?.resourceType, "rfi");
  assert.equal(result.data.documents[0]?.status, "submitted");
  assert.deepEqual(result.data.documents[0]?.linkedEntityRefs, ["A-101"]);
});

test("workspace read client rejects malformed document collection", async () => {
  const snapshot = workspaceSnapshot();
  const transport = new StubTransport({
    ok: true,
    data: {
      ...snapshot,
      documents: { invalid: true },
    } as never,
  });

  const result = await new WorkspaceReadClient(transport).load(context);

  assert.equal(result.ok, false);
  if (result.ok) throw new Error("expected invalid collection error");
  assert.equal(result.error.code, "INVALID_WORKSPACE_READ_COLLECTION");
});

test("workspace read client rejects malformed procurement collection", async () => {
  const snapshot = workspaceSnapshot();
  const transport = new StubTransport({
    ok: true,
    data: {
      ...snapshot,
      procurement_quotes: { invalid: true },
    } as never,
  });

  const result = await new WorkspaceReadClient(transport).load(context);

  assert.equal(result.ok, false);
  if (result.ok) throw new Error("expected invalid procurement collection error");
  assert.equal(result.error.code, "INVALID_WORKSPACE_READ_COLLECTION");
});

test("workspace read client rejects null optional collections", async () => {
  const snapshot = workspaceSnapshot();
  const transport = new StubTransport({
    ok: true,
    data: {
      ...snapshot,
      documents: null,
    } as never,
  });

  const result = await new WorkspaceReadClient(transport).load(context);

  assert.equal(result.ok, false);
  if (result.ok) throw new Error("expected invalid optional collection error");
  assert.equal(result.error.code, "INVALID_WORKSPACE_READ_COLLECTION");
});
