import assert from "node:assert/strict";
import test from "node:test";

import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";
import {
  DOCUMENT_API_VERSION,
  buildDocumentPayload,
  createDocument,
  loadDocumentHistory,
  loadDocuments,
  parseDocument,
  parseDocumentHistory,
  statusTransitions,
  transitionDocument,
  updateDocument,
} from "./workspace-documents.js";

const CONTEXT: ProjectContext = { tenant_id: "t1", project_id: "project-1", revision: 4 };
const HASH = "sha256:" + "a".repeat(64);

const DOCUMENT = {
  contract_version: DOCUMENT_API_VERSION,
  document_id: "DOC-100",
  tenant_id: "t1",
  project_id: "project-1",
  resource_type: "drawing",
  title: "Structural plan revision B",
  status: "submitted",
  storage_ref: "object://documents/DOC-100/rev-2",
  content_hash: HASH,
  linked_entity_refs: ["A100", "WBS-1"],
  revision: 2,
};

type Calls = {
  gets: string[];
  posts: { path: string; request: unknown; idempotencyKey?: string }[];
  puts: { path: string; request: unknown }[];
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
  };
}

function emptyCalls(): Calls {
  return { gets: [], posts: [], puts: [] };
}

function input(overrides: Record<string, unknown> = {}) {
  return {
    documentId: "DOC-100",
    resourceType: "drawing",
    title: "Structural plan revision B",
    storageRef: "object://documents/DOC-100/rev-2",
    contentHash: HASH,
    linkedEntityRefs: ["A100", "WBS-1"],
    ...overrides,
  };
}

test("document parsing keeps the stored revision and never invents a hash", () => {
  const parsed = parseDocument(DOCUMENT);
  assert.equal(parsed.documentId, "DOC-100");
  assert.equal(parsed.revision, 2);
  assert.equal(parsed.contentHash, HASH);
  assert.deepEqual(parsed.linkedEntityRefs, ["A100", "WBS-1"]);
});

test("document parsing rejects a different contract, unknown status or missing revision", () => {
  assert.throws(() => parseDocument({ ...DOCUMENT, contract_version: "2.0" }), /INVALID_DOCUMENT_RESPONSE/);
  assert.throws(() => parseDocument({ ...DOCUMENT, status: "unknown" }), /INVALID_DOCUMENT_RECORD/);
  assert.throws(() => parseDocument({ ...DOCUMENT, revision: 0 }), /INVALID_DOCUMENT_RECORD/);
  assert.throws(() => parseDocument({ ...DOCUMENT, content_hash: "" }), /INVALID_DOCUMENT_RECORD/);
});

test("history parsing requires the versioned event envelope", () => {
  const events = parseDocumentHistory({
    contract_version: DOCUMENT_API_VERSION,
    events: [
      {
        document_id: "DOC-100",
        revision: 2,
        event_type: "status_transition",
        actor_id: "u-1",
        occurred_at: "2026-11-12T10:00:00+00:00",
        reason: "accepted",
      },
    ],
  });
  assert.equal(events[0].eventType, "status_transition");
  assert.equal(events[0].reason, "accepted");
  assert.throws(
    () => parseDocumentHistory({ contract_version: "2.0", events: [] }),
    /INVALID_DOCUMENT_HISTORY/,
  );
});

test("only the declared status transitions are offered", () => {
  assert.deepEqual(statusTransitions("draft"), ["submitted"]);
  assert.deepEqual(statusTransitions("submitted"), ["approved", "rejected"]);
  assert.deepEqual(statusTransitions("rejected"), ["submitted"]);
  assert.deepEqual(statusTransitions("approved"), ["superseded"]);
  assert.deepEqual(statusTransitions("superseded"), []);
  assert.deepEqual(statusTransitions("unknown"), []);
});

test("document payload validates the hash before any request is sent", () => {
  assert.throws(() => buildDocumentPayload(input({ contentHash: "md5:bad" }), "draft"), /INVALID_DOCUMENT_CONTENT_HASH/);
  assert.throws(() => buildDocumentPayload(input({ resourceType: "unknown" }), "draft"), /INVALID_DOCUMENT_RESOURCE_TYPE/);
  assert.throws(() => buildDocumentPayload(input({ title: " " }), "draft"), /DOCUMENT_FIELDS_REQUIRED/);
  const payload = buildDocumentPayload(input(), "draft");
  assert.equal(payload.status, "draft");
  assert.equal(payload.content_hash, HASH);
  assert.deepEqual(payload.linked_entity_refs, ["A100", "WBS-1"]);
});

test("document list carries active filters into the request path", async () => {
  const calls = emptyCalls();
  const result = await loadDocuments(
    transportWith({ ok: true, data: { contract_version: DOCUMENT_API_VERSION, documents: [DOCUMENT] } }, calls),
    CONTEXT,
    { resourceType: "drawing", status: "submitted", search: "structural" },
  );
  assert.equal(result.ok, true);
  assert.equal(
    calls.gets[0],
    "/api/projects/project-1/documents?resource_type=drawing&status=submitted&search=structural",
  );
});

test("history loading uses the dedicated document history route", async () => {
  const calls = emptyCalls();
  await loadDocumentHistory(
    transportWith({ ok: true, data: { contract_version: DOCUMENT_API_VERSION, events: [] } }, calls),
    CONTEXT,
    "DOC-100",
  );
  assert.deepEqual(calls.gets, ["/api/projects/project-1/documents/DOC-100/history"]);
});

test("creating a document always starts as a draft and sends an idempotency key", async () => {
  const calls = emptyCalls();
  const result = await createDocument(
    transportWith({ ok: true, data: DOCUMENT }, calls),
    CONTEXT,
    input(),
  );
  assert.equal(result.ok, true);
  assert.equal(calls.posts.length, 1);
  assert.equal(calls.posts[0].path, "/api/projects/project-1/documents");
  assert.equal((calls.posts[0].request as Record<string, unknown>).status, "draft");
  assert.ok(calls.posts[0].idempotencyKey);
});

test("updating metadata preserves the stored status and sends the expected revision", async () => {
  const calls = emptyCalls();
  await updateDocument(
    transportWith({ ok: true, data: DOCUMENT }, calls),
    CONTEXT,
    input(),
    "submitted",
    2,
  );
  assert.equal(calls.puts[0].path, "/api/projects/project-1/documents/DOC-100");
  const request = calls.puts[0].request as Record<string, unknown>;
  assert.equal(request.status, "submitted");
  assert.equal(request.expected_revision, 2);
});

test("status transitions use the dedicated endpoint with a reason and revision", async () => {
  const calls = emptyCalls();
  const result = await transitionDocument(
    transportWith({ ok: true, data: { ...DOCUMENT, status: "approved", revision: 3 } }, calls),
    CONTEXT,
    "DOC-100",
    "approved",
    2,
    "accepted",
  );
  assert.equal(result.ok, true);
  assert.equal(calls.posts[0].path, "/api/projects/project-1/documents/DOC-100/status");
  assert.deepEqual(calls.posts[0].request, {
    status: "approved",
    expected_revision: 2,
    reason: "accepted",
  });
  assert.ok(calls.posts[0].idempotencyKey);
});
