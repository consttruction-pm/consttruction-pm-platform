import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import test from "node:test";

import type { ApiResult, ApiTransport, DownloadedBinary, ProjectContext } from "./client.js";
import {
  DOCUMENT_API_VERSION,
  DOCUMENT_CONTENT_API_VERSION,
  buildDocumentPayload,
  createDocument,
  documentContentHash,
  downloadDocumentContent,
  downloadFilename,
  formatBytes,
  loadDocumentContentVersions,
  loadDocumentHistory,
  loadDocuments,
  mountWorkspaceDocumentsPage,
  parseDocument,
  parseDocumentContentUpload,
  parseDocumentContentVersion,
  parseDocumentHistory,
  prepareDocumentContent,
  resolveDocumentContentType,
  statusTransitions,
  transitionDocument,
  updateDocument,
  uploadDocumentContent,
  validateDocumentContent,
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

const PDF_BYTES = new TextEncoder().encode("%PDF-1.7\npreview evidence\n%%EOF\n");
const PDF_HASH = "sha256:" + createHash("sha256").update(PDF_BYTES).digest("hex");

function selectedPdf() {
  return {
    blob: new Blob([PDF_BYTES], { type: "application/pdf" }),
    name: "evidence.pdf",
    contentType: "application/pdf",
    byteSize: PDF_BYTES.byteLength,
    contentHash: PDF_HASH,
  };
}

function contentVersion(overrides: Record<string, unknown> = {}) {
  return {
    document_id: "DOC-100",
    version: 1,
    document_revision: 2,
    content_hash: PDF_HASH,
    content_type: "application/pdf",
    byte_size: PDF_BYTES.byteLength,
    original_filename: "evidence.pdf",
    uploaded_at: "2026-11-12T10:00:00+00:00",
    uploaded_by: "user-1",
    ...overrides,
  };
}

test("content version parsing keeps only server-derived facts", () => {
  const parsed = parseDocumentContentVersion(contentVersion());
  assert.equal(parsed.version, 1);
  assert.equal(parsed.contentHash, PDF_HASH);
  assert.equal(parsed.byteSize, PDF_BYTES.byteLength);
  assert.throws(() => parseDocumentContentVersion(contentVersion({ version: 0 })), /INVALID_DOCUMENT_CONTENT_VERSION/);
  assert.throws(() => parseDocumentContentVersion(contentVersion({ content_hash: "md5:1" })), /INVALID_DOCUMENT_CONTENT_VERSION/);
  assert.throws(
    () => parseDocumentContentUpload({
      contract_version: DOCUMENT_CONTENT_API_VERSION,
      document_id: "DOC-OTHER",
      content: contentVersion(),
      storage_ref: "local:v1/x",
      idempotent_replay: false,
    }),
    /INVALID_DOCUMENT_CONTENT_RESPONSE/,
  );
});

test("local file validation mirrors the documented allow-list and size limit", () => {
  assert.equal(validateDocumentContent("a.pdf", "application/pdf", 10), null);
  assert.equal(validateDocumentContent("a.pdf", "application/pdf", 0), "EMPTY_DOCUMENT_CONTENT");
  assert.equal(validateDocumentContent("a.pdf", "application/pdf", 25 * 1024 * 1024 + 1), "DOCUMENT_CONTENT_TOO_LARGE");
  assert.equal(validateDocumentContent("a.html", "text/html", 10), "DOCUMENT_CONTENT_TYPE_REJECTED");
  // Browsers may leave type empty; the extension is then the documented hint.
  assert.equal(resolveDocumentContentType("scan.PNG", ""), "image/png");
  assert.equal(resolveDocumentContentType("notes.unknown", ""), null);
  assert.equal(formatBytes(1536), "1.5 KB");
});

test("preparing a file derives the digest from its bytes, not from an input", async () => {
  const ok = await prepareDocumentContent({
    name: "evidence.pdf",
    type: "application/pdf",
    size: PDF_BYTES.byteLength,
    arrayBuffer: async () => PDF_BYTES.buffer as ArrayBuffer,
  });
  assert.equal(ok.ok, true);
  if (!ok.ok) return;
  assert.equal(ok.data.contentHash, PDF_HASH);
  assert.equal(ok.data.contentType, "application/pdf");
  assert.equal(await documentContentHash(PDF_BYTES.buffer as ArrayBuffer), PDF_HASH);

  const rejected = await prepareDocumentContent({
    name: "page.html",
    type: "text/html",
    size: 4,
    arrayBuffer: async () => new TextEncoder().encode("<p>").buffer as ArrayBuffer,
  });
  assert.equal(rejected.ok, false);
  if (!rejected.ok) assert.equal(rejected.error.code, "DOCUMENT_CONTENT_TYPE_REJECTED");
});

test("upload sends the revision, content type, filename and idempotency key", async () => {
  let captured: { path: string; body: Blob; contentType: string; headers?: Record<string, string> } | null = null;
  const transport: ApiTransport = {
    async get() { throw new Error("unused"); },
    async post() { throw new Error("unused"); },
    async postBytes(path, body, contentType, _context, headers) {
      captured = { path, body, contentType, headers };
      return {
        ok: true,
        data: {
          contract_version: DOCUMENT_CONTENT_API_VERSION,
          document_id: "DOC-100",
          content: contentVersion(),
          storage_ref: "local:v1/aa/bb/cc/" + "a".repeat(64) + ".pdf",
          idempotent_replay: false,
        },
      } as ApiResult<unknown>;
    },
  } as ApiTransport;
  const result = await uploadDocumentContent(transport, CONTEXT, "DOC-100", selectedPdf(), {
    expectedRevision: 2,
    idempotencyKey: "upload-1",
  });
  assert.equal(result.ok, true);
  assert.ok(captured);
  const call = captured as { path: string; body: Blob; contentType: string; headers?: Record<string, string> };
  assert.equal(call.contentType, "application/pdf");
  assert.equal(call.headers?.["Idempotency-Key"], "upload-1");
  assert.equal(call.headers?.["X-Expected-Revision"], "2");
  const params = new URL(call.path, "http://localhost").searchParams;
  assert.equal(params.get("expected_revision"), "2");
  assert.equal(params.get("filename"), "evidence.pdf");
  assert.equal(params.get("content_type"), "application/pdf");
  assert.equal(params.get("idempotency_key"), "upload-1");
  assert.equal((call.body as Blob).size, PDF_BYTES.byteLength);
});

test("upload refuses to report success when the server digest differs", async () => {
  const transport: ApiTransport = {
    async get() { throw new Error("unused"); },
    async post() { throw new Error("unused"); },
    async postBytes() {
      return {
        ok: true,
        data: {
          contract_version: DOCUMENT_CONTENT_API_VERSION,
          document_id: "DOC-100",
          content: contentVersion({ content_hash: "sha256:" + "b".repeat(64) }),
          storage_ref: "local:v1/x",
          idempotent_replay: false,
        },
      } as ApiResult<unknown>;
    },
  } as ApiTransport;
  const result = await uploadDocumentContent(transport, CONTEXT, "DOC-100", selectedPdf(), {
    expectedRevision: 1,
    idempotencyKey: "upload-2",
  });
  assert.equal(result.ok, false);
  if (!result.ok) assert.equal(result.error.code, "DOCUMENT_CONTENT_HASH_MISMATCH");
});

test("version listing parses the versioned envelope for the same document", async () => {
  const paths: string[] = [];
  const transport = {
    async get(path: string) {
      paths.push(path);
      return {
        ok: true,
        data: {
          contract_version: DOCUMENT_CONTENT_API_VERSION,
          document_id: "DOC-100",
          versions: [contentVersion(), contentVersion({ version: 2, document_revision: 4 })],
        },
      } as ApiResult<unknown>;
    },
    async post() { throw new Error("unused"); },
  } as unknown as ApiTransport;
  const result = await loadDocumentContentVersions(transport, CONTEXT, "DOC-100");
  assert.equal(paths[0], "/api/projects/project-1/documents/DOC-100/content/versions");
  assert.equal(result.ok, true);
  if (result.ok) assert.deepEqual(result.data.map((item) => item.version), [1, 2]);
});

test("download verifies the server digest against the received bytes", async () => {
  const binary = (contentSha256: string): DownloadedBinary => ({
    blob: new Blob([PDF_BYTES], { type: "application/pdf" }),
    contentType: "application/pdf",
    contentDisposition: "attachment; filename*=UTF-8''evidence.pdf",
    contentSha256,
    documentVersion: "2",
  });
  const paths: string[] = [];
  const matching: ApiTransport = {
    async get() { throw new Error("unused"); },
    async post() { throw new Error("unused"); },
    async download(path) {
      paths.push(path);
      return { ok: true, data: binary(PDF_HASH) };
    },
  };
  const ok = await downloadDocumentContent(matching, CONTEXT, "DOC-100", 2);
  assert.equal(paths[0], "/api/projects/project-1/documents/DOC-100/content/2");
  assert.equal(ok.ok, true);
  if (ok.ok) {
    assert.equal(ok.data.filename, "evidence.pdf");
    assert.equal(ok.data.contentHash, PDF_HASH);
  }
  assert.equal(downloadFilename("attachment; filename=\"report.pdf\"", "x"), "report.pdf");

  const tampered = await downloadDocumentContent({
    async get() { throw new Error("unused"); },
    async post() { throw new Error("unused"); },
    async download() { return { ok: true, data: binary("sha256:" + "c".repeat(64)) }; },
  }, CONTEXT, "DOC-100", 2);
  assert.equal(tampered.ok, false);
  if (!tampered.ok) assert.equal(tampered.error.code, "DOCUMENT_CONTENT_HASH_MISMATCH");

  const missing = await downloadDocumentContent({
    async get() { throw new Error("unused"); },
    async post() { throw new Error("unused"); },
    async download() { return { ok: true, data: binary("") }; },
  }, CONTEXT, "DOC-100", null);
  assert.equal(missing.ok, false);
  if (!missing.ok) assert.equal(missing.error.code, "DOCUMENT_CONTENT_HASH_MISSING");
});

function mountHost() {
  const listeners = new Map<string, (event: Event) => void>();
  const host = {
    dataset: {} as Record<string, string>,
    innerHTML: "",
    addEventListener: (type: string, listener: (event: Event) => void) => listeners.set(type, listener),
    querySelectorAll: () => [],
    querySelector: () => null,
    contains: () => true,
  };
  const fire = (type: string, target: Record<string, unknown>): void => {
    const dataset = (target.dataset ?? {}) as Record<string, string>;
    const wrapper = {
      ...target,
      dataset,
      closest: (selector: string) => {
        if (selector === "[data-document-row]" && dataset.documentId) return wrapper;
        if (selector === "[data-document-tab]" && dataset.documentTab) return wrapper;
        if (selector.startsWith("[data-document-action]") && dataset.documentAction) return wrapper;
        if (selector === "[data-document-transition]" && dataset.documentTransition) return wrapper;
        return null;
      },
    };
    listeners.get(type)?.({ target: wrapper } as unknown as Event);
  };
  return {
    host: host as unknown as HTMLElement,
    click: (target: Record<string, unknown>) => fire("click", target),
  };
}

const tick = (): Promise<void> => new Promise((resolve) => setTimeout(resolve, 0));

test("the mounted register reads versions only when the Content tab is opened", async () => {
  const paths: string[] = [];
  const transport = {
    async get(path: string) {
      paths.push(path);
      if (path.endsWith("/content/versions")) {
        return {
          ok: true,
          data: {
            contract_version: DOCUMENT_CONTENT_API_VERSION,
            document_id: "DOC-100",
            versions: [contentVersion()],
          },
        } as ApiResult<unknown>;
      }
      if (path.endsWith("/history")) {
        return { ok: true, data: { contract_version: DOCUMENT_API_VERSION, events: [] } } as ApiResult<unknown>;
      }
      return { ok: true, data: { contract_version: DOCUMENT_API_VERSION, documents: [DOCUMENT] } } as ApiResult<unknown>;
    },
    async post() { throw new Error("unused"); },
  } as unknown as ApiTransport;
  const { host, click } = mountHost();
  mountWorkspaceDocumentsPage(host, {
    transport,
    context: CONTEXT,
    locale: "en",
    canWrite: true,
    canApprove: true,
  });
  await tick();
  assert.equal((host as unknown as { dataset: Record<string, string> }).dataset.documentsStatus, "loaded");
  assert.match(host.innerHTML, /data-document-row data-document-id="DOC-100"/);
  assert.equal(paths.filter((path) => path.endsWith("/content/versions")).length, 0);

  click({ dataset: { documentId: "DOC-100" } });
  await tick();
  click({ dataset: { documentTab: "content" } });
  await tick();
  await tick();
  assert.ok(paths.some((path) => path.endsWith("/documents/DOC-100/content/versions")));
  assert.match(host.innerHTML, /data-document-content/);
  assert.match(host.innerHTML, /data-document-version="1"/);
  assert.match(host.innerHTML, /evidence\.pdf/);
  assert.match(host.innerHTML, /Upload as new version/);
});
