import assert from "node:assert/strict";
import test from "node:test";

import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";
import {
  GANTT_ATTACHMENT_API_VERSION,
  createGanttAttachment,
  deleteGanttAttachment,
  loadGanttAttachments,
  parseGanttAttachment,
  parseGanttAttachmentList,
  updateGanttAttachment,
} from "./workspace-gantt-attachments.js";

const CONTEXT: ProjectContext = { tenant_id: "t1", project_id: "preview-rps-01", revision: 4 };

function record(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    attachment_id: "ga-1",
    kind: "curtain",
    label: "Permit window",
    start_date: "2026-03-02",
    end_date: "2026-03-20",
    color: "#b45309",
    activity_id: null,
    topic_id: null,
    visible: true,
    record_revision: 2,
    updated_at: "2026-11-19T08:00:00+00:00",
    ...overrides,
  };
}

type Call = { method: string; path: string; body?: unknown };

function transport(result: ApiResult<unknown>): ApiTransport & { calls: Call[] } {
  const calls: Call[] = [];
  const reply = <T,>(value: ApiResult<unknown>): Promise<ApiResult<T>> => Promise.resolve(value as ApiResult<T>);
  return {
    calls,
    get: <T,>(path: string) => { calls.push({ method: "GET", path }); return reply<T>(result); },
    post: <TRequest, TResponse>(path: string, request: TRequest) => {
      calls.push({ method: "POST", path, body: request });
      return reply<TResponse>(result);
    },
    patch: <TRequest, TResponse>(path: string, request: TRequest) => {
      calls.push({ method: "PATCH", path, body: request });
      return reply<TResponse>(result);
    },
    delete: <TRequest, TResponse>(path: string, request: TRequest) => {
      calls.push({ method: "DELETE", path, body: request });
      return reply<TResponse>(result);
    },
  } as ApiTransport & { calls: Call[] };
}

test("parses a persisted curtain with its revision and colour", () => {
  const parsed = parseGanttAttachment(record());
  assert.equal(parsed.kind, "curtain");
  assert.equal(parsed.startDate, "2026-03-02");
  assert.equal(parsed.endDate, "2026-03-20");
  assert.equal(parsed.color, "#b45309");
  assert.equal(parsed.recordRevision, 2);
  assert.equal(parsed.visible, true);
});

test("parses text and notebook marks that anchor to an activity", () => {
  const text = parseGanttAttachment(record({ attachment_id: "ga-2", kind: "text", label: "Inspection", start_date: null, end_date: null, activity_id: "A130" }));
  assert.equal(text.activityId, "A130");
  assert.equal(text.startDate, null);
  const notebook = parseGanttAttachment(record({ attachment_id: "ga-3", kind: "notebook", label: "Kickoff", activity_id: "A130", topic_id: "topic-1", visible: false }));
  assert.equal(notebook.topicId, "topic-1");
  assert.equal(notebook.visible, false);
});

test("rejects an unknown kind, an empty label and a missing revision", () => {
  assert.throws(() => parseGanttAttachment(record({ kind: "bar" })), /INVALID_GANTT_ATTACHMENT/);
  assert.throws(() => parseGanttAttachment(record({ label: "  " })), /INVALID_GANTT_ATTACHMENT/);
  assert.throws(() => parseGanttAttachment(record({ record_revision: 0 })), /INVALID_GANTT_ATTACHMENT/);
  assert.throws(() => parseGanttAttachmentList({ contract_version: "other", attachments: [] }), /INVALID_GANTT_ATTACHMENT_LIST/);
});

test("loads the list from the project-scoped attachment path", async () => {
  const api = transport({ ok: true, data: { contract_version: GANTT_ATTACHMENT_API_VERSION, kind: "p6_gantt_attachment_list", attachments: [record()] } });
  const result = await loadGanttAttachments(api, CONTEXT);
  assert.equal(result.ok, true);
  if (!result.ok) return;
  assert.equal(result.data.length, 1);
  assert.deepEqual(api.calls, [{ method: "GET", path: "/api/projects/preview-rps-01/p6/gantt/attachments" }]);
});

test("create posts the server payload without a revision", async () => {
  const api = transport({ ok: true, data: { contract_version: GANTT_ATTACHMENT_API_VERSION, attachment: record({ record_revision: 1 }) } });
  const result = await createGanttAttachment(api, CONTEXT, {
    kind: "curtain", label: "  Permit window  ", startDate: "2026-03-02", endDate: "2026-03-20",
    color: "#b45309", activityId: null, topicId: null, visible: true,
  });
  assert.equal(result.ok, true);
  const body = api.calls[0].body as Record<string, unknown>;
  assert.equal(api.calls[0].method, "POST");
  assert.equal(body.label, "Permit window");
  assert.equal(body.kind, "curtain");
  assert.equal("expected_record_revision" in body, false);
});

test("update carries the record revision so a stale editor is rejected", async () => {
  const api = transport({ ok: true, data: { attachment: record({ record_revision: 3 }) } });
  const result = await updateGanttAttachment(api, CONTEXT, "ga-1", {
    kind: "curtain", label: "Permit window", startDate: "2026-03-02", endDate: "2026-03-21",
    color: "#b45309", activityId: null, topicId: null, visible: false, expectedRevision: 2,
  });
  assert.equal(result.ok, true);
  const body = api.calls[0].body as Record<string, unknown>;
  assert.equal(api.calls[0].path, "/api/projects/preview-rps-01/p6/gantt/attachments/ga-1");
  assert.equal(body.expected_record_revision, 2);
  assert.equal(body.visible, false);
});

test("delete uses the attachment path and reports a server conflict unchanged", async () => {
  const api = transport({
    ok: false,
    error: { code: "REVISION_CONFLICT", retryable: false, message_key: "error.revision.conflict", available_actions: [] },
  });
  const conflict = await deleteGanttAttachment(api, CONTEXT, "ga-1", 4);
  assert.equal(conflict.ok, false);
  if (!conflict.ok) assert.equal(conflict.error.code, "REVISION_CONFLICT");
  assert.deepEqual(api.calls[0], {
    method: "DELETE",
    path: "/api/projects/preview-rps-01/p6/gantt/attachments/ga-1",
    body: { expected_record_revision: 4 },
  });
});

test("a malformed server payload becomes a typed client error", async () => {
  const api = transport({ ok: true, data: { attachments: [record({ record_revision: -1 })] } });
  const result = await loadGanttAttachments(api, CONTEXT);
  assert.equal(result.ok, false);
  if (!result.ok) assert.match(result.error.code, /INVALID_GANTT_ATTACHMENT/);
});
