import assert from "node:assert/strict";
import test from "node:test";

import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";
import {
  ISSUE_API_VERSION,
  addIssueComment,
  buildIssuePayload,
  deleteIssue,
  loadIssueHistory,
  loadIssues,
  parseIssue,
  saveIssue,
  updateIssue,
} from "./workspace-issues.js";

const CONTEXT: ProjectContext = { tenant_id: "t1", project_id: "project-1", revision: 4 };

const ISSUE = {
  issue_id: "ISSUE-100",
  title: "Late structural drawings",
  description: "Drawing package issued after the planned start.",
  issue_type: "schedule",
  status: "open",
  priority: "high",
  owner: "u-owner",
  responsible_manager: null,
  date_identified: "2026-11-01",
  due_date: "2026-11-20",
  wbs_id: "WBS-1",
  activity_id: "A100",
  document_refs: ["DOC-1"],
  resolution_note: null,
  record_revision: 2,
  created_at: "2026-11-01T08:00:00+00:00",
  updated_at: "2026-11-02T08:00:00+00:00",
};

function envelope(issue: unknown = ISSUE) {
  return {
    contract_version: ISSUE_API_VERSION,
    kind: "p6_issue",
    scope: { tenant_id: "t1", project_id: "project-1", project_revision: 4 },
    issue,
  };
}

type Calls = {
  gets: string[];
  posts: { path: string; request: unknown; idempotencyKey?: string }[];
  puts: { path: string; request: unknown }[];
  deletes: { path: string; request: unknown }[];
};

function transportWith(result: ApiResult<unknown>, calls: Calls): ApiTransport {
  return {
    async get(path) {
      calls.gets.push(path);
      return result as ApiResult<never>;
    },
    async post(path, request, _context, idempotencyKey) {
      calls.posts.push({ path, request, idempotencyKey });
      return result as ApiResult<never>;
    },
    async put(path, request) {
      calls.puts.push({ path, request });
      return result as ApiResult<never>;
    },
    async delete(path, request) {
      calls.deletes.push({ path, request });
      return result as ApiResult<never>;
    },
  };
}

function emptyCalls(): Calls {
  return { gets: [], posts: [], puts: [], deletes: [] };
}

function input(overrides: Record<string, unknown> = {}) {
  return {
    issueId: "ISSUE-100",
    title: "Late structural drawings",
    description: "Drawing package issued after the planned start.",
    issueType: "schedule",
    status: "open",
    priority: "high",
    owner: "u-owner",
    responsibleManager: null,
    dateIdentified: "2026-11-01",
    dueDate: "2026-11-20",
    wbsId: "WBS-1",
    activityId: "A100",
    documentRefs: ["DOC-1"],
    resolutionNote: null,
    ...overrides,
  };
}

test("issue parsing keeps the stored revision and document links", () => {
  const parsed = parseIssue(envelope());
  assert.equal(parsed.issueId, "ISSUE-100");
  assert.equal(parsed.recordRevision, 2);
  assert.deepEqual(parsed.documentRefs, ["DOC-1"]);
  assert.equal(parsed.dueDate, "2026-11-20");
});

test("issue parsing rejects a different contract or a missing revision", () => {
  assert.throws(() => parseIssue({ ...envelope(), contract_version: "p6-expense-api.v1" }), /INVALID_ISSUE_RESPONSE/);
  assert.throws(() => parseIssue(envelope({ ...ISSUE, record_revision: 0 })), /INVALID_ISSUE_RECORD/);
  assert.throws(() => parseIssue(envelope({ ...ISSUE, issue_id: "  " })), /INVALID_ISSUE_RECORD/);
});

test("issue list carries active filters into the request path", async () => {
  const calls = emptyCalls();
  const result = await loadIssues(
    transportWith({ ok: true, data: { contract_version: ISSUE_API_VERSION, issues: [envelope()] } }, calls),
    CONTEXT,
    { status: "open", priority: "high", issueType: "schedule", search: "drawings" },
  );
  assert.ok(result.ok);
  assert.equal(
    calls.gets[0],
    "/api/projects/project-1/p6/issues?status=open&priority=high&issue_type=schedule&search=drawings",
  );
});

test("issue list surfaces an invalid payload instead of inventing records", async () => {
  const calls = emptyCalls();
  const result = await loadIssues(
    transportWith({ ok: true, data: { contract_version: ISSUE_API_VERSION, issues: [{ bad: true }] } }, calls),
    CONTEXT,
  );
  assert.equal(result.ok, false);
  assert.equal((result as { ok: false; error: { code: string } }).error.code, "INVALID_ISSUE_RESPONSE");
});

test("issue payload validates enums, dates and required identity", () => {
  const payload = buildIssuePayload(input() as never);
  assert.equal(payload.contract_version, ISSUE_API_VERSION);
  assert.deepEqual(payload.document_refs, ["DOC-1"]);
  assert.equal(payload.responsible_manager, null);

  assert.throws(() => buildIssuePayload(input({ issueId: " " }) as never), /ISSUE_FIELDS_REQUIRED/);
  assert.throws(() => buildIssuePayload(input({ priority: "urgent" }) as never), /INVALID_ISSUE_PRIORITY/);
  assert.throws(() => buildIssuePayload(input({ status: "done" }) as never), /INVALID_ISSUE_STATUS/);
  assert.throws(() => buildIssuePayload(input({ dateIdentified: "2026/11/01" }) as never), /INVALID_ISSUE_DATE/);
});

test("issue create posts the authoritative payload with an idempotency key", async () => {
  const calls = emptyCalls();
  const result = await saveIssue(
    transportWith({ ok: true, data: envelope() }, calls),
    CONTEXT,
    input() as never,
  );
  assert.ok(result.ok);
  assert.equal(calls.posts[0].path, "/api/projects/project-1/p6/issues");
  assert.ok(calls.posts[0].idempotencyKey);
  assert.equal((calls.posts[0].request as Record<string, unknown>).issue_id, "ISSUE-100");
});

test("issue update sends the expected revision and surfaces a conflict", async () => {
  const calls = emptyCalls();
  const ok = await updateIssue(
    transportWith({ ok: true, data: envelope() }, calls),
    CONTEXT,
    input() as never,
    2,
  );
  assert.ok(ok.ok);
  assert.equal(calls.puts[0].path, "/api/projects/project-1/p6/issues/ISSUE-100");
  assert.equal((calls.puts[0].request as Record<string, unknown>).expected_revision, 2);

  const conflictCalls = emptyCalls();
  const conflict = await updateIssue(
    transportWith(
      { ok: false, error: { code: "ISSUE_REVISION_CONFLICT", retryable: false, message_key: "error.p6.issue.conflict", available_actions: [] } },
      conflictCalls,
    ),
    CONTEXT,
    input() as never,
    1,
  );
  assert.equal(conflict.ok, false);
  assert.equal((conflict as { ok: false; error: { code: string } }).error.code, "ISSUE_REVISION_CONFLICT");
});

test("issue comment posts the comment and revision, and history parses events", async () => {
  const calls = emptyCalls();
  const commented = await addIssueComment(
    transportWith({ ok: true, data: envelope({ ...ISSUE, record_revision: 3 }) }, calls),
    CONTEXT,
    "ISSUE-100",
    "  Sample reissued  ",
    2,
  );
  assert.ok(commented.ok);
  assert.equal(calls.posts[0].path, "/api/projects/project-1/p6/issues/ISSUE-100/comments");
  assert.deepEqual(calls.posts[0].request, { comment: "Sample reissued", expected_revision: 2 });

  const historyCalls = emptyCalls();
  const history = await loadIssueHistory(
    transportWith({
      ok: true,
      data: {
        contract_version: ISSUE_API_VERSION,
        events: [
          {
            contract_version: ISSUE_API_VERSION,
            kind: "p6_issue_event",
            issue_id: "ISSUE-100",
            event: {
              issue_id: "ISSUE-100",
              event_sequence: 1,
              event_type: "created",
              actor_id: "u1",
              occurred_at: "2026-11-01T08:00:00+00:00",
              detail: { status: "open" },
            },
          },
        ],
      },
    }, historyCalls),
    CONTEXT,
    "ISSUE-100",
  );
  assert.ok(history.ok);
  assert.equal(history.data[0].eventType, "created");
  assert.equal(historyCalls.gets[0], "/api/projects/project-1/p6/issues/ISSUE-100/history");
});

test("issue delete sends the revision and requires a truthful response", async () => {
  const calls = emptyCalls();
  const result = await deleteIssue(
    transportWith({ ok: true, data: { contract_version: ISSUE_API_VERSION, deleted: true } }, calls),
    CONTEXT,
    "ISSUE-100",
    3,
  );
  assert.ok(result.ok);
  assert.deepEqual(calls.deletes[0], {
    path: "/api/projects/project-1/p6/issues/ISSUE-100",
    request: { expected_revision: 3 },
  });

  const bad = await deleteIssue(
    transportWith({ ok: true, data: { contract_version: ISSUE_API_VERSION, deleted: false } }, emptyCalls()),
    CONTEXT,
    "ISSUE-100",
    3,
  );
  assert.equal(bad.ok, false);
  assert.equal((bad as { ok: false; error: { code: string } }).error.code, "INVALID_ISSUE_DELETE_RESPONSE");
});
