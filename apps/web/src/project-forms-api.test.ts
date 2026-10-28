import assert from "node:assert/strict";
import test from "node:test";

import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";
import {
  createProjectFormsClient,
  type ProjectFormDefinition,
  type ProjectFormDraftInput,
  type ProjectFormSubmission,
} from "./project-forms-api.js";

const context: ProjectContext = {
  tenant_id: "tenant-1",
  project_id: "project-1",
  revision: 7,
};

const form: ProjectFormDefinition = {
  contract_version: "project-form.v1",
  scope: {
    tenant_id: context.tenant_id,
    project_id: context.project_id,
    project_revision: context.revision,
  },
  form_id: "FORM-DAILY-001",
  version: 1,
  name: "Daily field report",
  description: "Daily site record",
  status: "published",
  sections: [{ section_id: "GENERAL", title: "General", localized_titles: { fa: "عمومی" } }],
  fields: [
    {
      field_id: "WORK-DATE",
      section_id: "GENERAL",
      field_type: "date",
      label: "Work date",
      required: true,
      options: [],
      localized_labels: {},
      minimum: null,
      maximum: null,
      min_length: null,
      max_length: null,
    },
    {
      field_id: "WORK-COMPLETED",
      section_id: "GENERAL",
      field_type: "boolean",
      label: "Work completed",
      required: true,
      options: [],
      localized_labels: {},
      minimum: null,
      maximum: null,
      min_length: null,
      max_length: null,
    },
  ],
  shared_with_user_ids: ["worker-1"],
  shared_with_roles: ["field_worker"],
  approver_user_ids: ["supervisor-1"],
  approver_roles: ["project_admin"],
  output_mappings: [],
  requires_approval: true,
  created_by: "owner-1",
  created_at: "2026-10-28T08:00:00+00:00",
  published_by: "owner-1",
  published_at: "2026-10-28T08:05:00+00:00",
};

const submission: ProjectFormSubmission = {
  contract_version: "project-form-submission.v1",
  scope: form.scope,
  submission_id: "SUB-DAILY-001",
  form_id: form.form_id,
  form_version: form.version,
  submitted_by: "worker-1",
  answers: { "WORK-DATE": "2026-10-28", "WORK-COMPLETED": false },
  status: "pending_approval",
  submitted_at: "2026-10-28T08:10:00+00:00",
  reviewed_by: null,
  reviewed_at: null,
  review_note: null,
};

class StubTransport implements ApiTransport {
  readonly posts: Array<{ path: string; request: unknown; context: ProjectContext }> = [];

  async get<T>(_path: string, _context: ProjectContext): Promise<ApiResult<T>> {
    return { ok: true, data: form as T };
  }

  async post<TRequest, TResponse>(
    path: string,
    request: TRequest,
    requestContext: ProjectContext,
  ): Promise<ApiResult<TResponse>> {
    this.posts.push({ path, request, context: requestContext });
    if (path.endsWith("/submissions")) return { ok: true, data: submission as TResponse };
    return { ok: true, data: form as TResponse };
  }
}

test("form API round-trips date and boolean fields and preserves false answers", async () => {
  const transport = new StubTransport();
  const client = createProjectFormsClient(transport, context);
  const loaded = await client.getSharedForm(form.form_id, form.version);

  assert.equal(loaded.fields.find((field) => field.field_id === "WORK-DATE")?.field_type, "date");
  assert.equal(loaded.fields.find((field) => field.field_id === "WORK-COMPLETED")?.field_type, "boolean");

  const result = await client.submitSharedForm(form.form_id, 1, submission.submission_id, {
    "WORK-DATE": "2026-10-28",
    "WORK-COMPLETED": false,
  });

  assert.equal(result.answers["WORK-COMPLETED"], false);
  assert.equal(result.answers["WORK-DATE"], "2026-10-28");
  assert.deepEqual((transport.posts[0].request as { answers: Record<string, unknown> }).answers, {
    "WORK-DATE": "2026-10-28",
    "WORK-COMPLETED": false,
  });
});

test("form API sends explicit user and approver assignments when creating a draft", async () => {
  const transport = new StubTransport();
  const client = createProjectFormsClient(transport, context);
  const draft: ProjectFormDraftInput = {
    form_id: form.form_id,
    name: form.name,
    description: form.description,
    sections: form.sections,
    fields: form.fields,
    shared_with_user_ids: ["worker-1", "worker-2"],
    shared_with_roles: ["field_worker"],
    approver_user_ids: ["supervisor-1"],
    approver_roles: ["project_admin"],
    output_mappings: [],
    requires_approval: true,
    expected_latest_version: null,
  };

  await client.createDraft(draft);

  assert.deepEqual(transport.posts[0].request, draft);
  assert.deepEqual((transport.posts[0].request as ProjectFormDraftInput).shared_with_user_ids, ["worker-1", "worker-2"]);
  assert.deepEqual((transport.posts[0].request as ProjectFormDraftInput).approver_user_ids, ["supervisor-1"]);
});
