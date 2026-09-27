import assert from "node:assert/strict";
import test from "node:test";

import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";
import { WorkspaceReadClient, WORKSPACE_CONTROL_ROOM_READ_VERSION } from "./workspace-read-api.js";

const context: ProjectContext = {
  tenant_id: "tenant-1",
  project_id: "project-1",
  revision: 7,
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

test("workspace read hydrates documents with independent document revisions", async () => {
  const documentRevision = 2;
  const result = await new WorkspaceReadClient(new StubTransport({
    contract_version: WORKSPACE_CONTROL_ROOM_READ_VERSION,
    context,
    workspace: {
      contract_version: "workspace-control-room.v1",
      context,
      columns: [],
      activities: [],
    },
    field_daily_logs: [],
    field_issues: [],
    field_timecards: [],
    equipment_status_reports: [],
    inspections: [],
    quality_records: [],
    safety_observations: [],
    punch_items: [],
    documents: [{
      contract_version: "1.0",
      resource_type: "rfi",
      resource_id: "RFI-001",
      tenant_id: context.tenant_id,
      project_id: context.project_id,
      revision: documentRevision,
      payload: {
        title: "RFI structural opening",
        status: "submitted",
        storage_ref: "object://rfi-001",
        content_hash: "sha256:" + "a".repeat(64),
        linked_entity_refs: ["A-101"],
      },
    }],
    document_ocr_results: [{
      contract_version: "1.0",
      tenant_id: context.tenant_id,
      project_id: context.project_id,
      document_id: "RFI-001",
      revision: documentRevision,
      text: "Confirm structural opening.",
      provider: "reference",
    }],
    document_search_entries: [{
      contract_version: "1.0",
      tenant_id: context.tenant_id,
      project_id: context.project_id,
      document_id: "RFI-001",
      revision: documentRevision,
      content_hash: "sha256:" + "a".repeat(64),
      text: "Confirm structural opening.",
    }],
  })).load(context);

  assert.equal(result.ok, true);
  if (!result.ok) throw new Error("expected success");
  assert.equal(result.data.documents[0]?.revision, documentRevision);
  assert.equal(result.data.documents[0]?.ocrAvailable, true);
  assert.equal(result.data.documents[0]?.indexed, true);
});
