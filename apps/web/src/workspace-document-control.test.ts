import assert from "node:assert/strict";
import test from "node:test";

import {
  DOCUMENT_OCR_VERSION,
  DOCUMENT_RESOURCE_VERSION,
  DOCUMENT_SEARCH_INDEX_VERSION,
  projectDocument,
  projectOcrResult,
  projectSearchIndex,
} from "./workspace-document-control.js";

const context = {
  tenant_id: "tenant-1",
  project_id: "project-1",
};

const document = {
  contract_version: DOCUMENT_RESOURCE_VERSION,
  resource_type: "rfi" as const,
  resource_id: "RFI-001",
  tenant_id: "tenant-1",
  project_id: "project-1",
  revision: 2,
  payload: {
    title: "RFI — structural opening",
    status: "submitted" as const,
    storage_ref: "object://documents/rfi-001",
    content_hash: "sha256:" + "a".repeat(64),
    linked_entity_refs: ["A-101", "D-44"],
  },
};

const ocr = {
  contract_version: DOCUMENT_OCR_VERSION,
  tenant_id: "tenant-1",
  project_id: "project-1",
  document_id: "RFI-001",
  revision: 2,
  text: "Please confirm the structural opening detail.",
  provider: "reference-ocr",
};

const index = {
  contract_version: DOCUMENT_SEARCH_INDEX_VERSION,
  tenant_id: "tenant-1",
  project_id: "project-1",
  document_id: "RFI-001",
  revision: 2,
  content_hash: "sha256:" + "a".repeat(64),
  text: "Please confirm the structural opening detail.",
};

test("document projection preserves revision, links and OCR/search availability", () => {
  const result = projectDocument(document, context, ocr, index);
  assert.equal(result.resourceType, "rfi");
  assert.equal(result.title, "RFI — structural opening");
  assert.equal(result.status, "submitted");
  assert.deepEqual(result.linkedEntityRefs, ["A-101", "D-44"]);
  assert.equal(result.ocrAvailable, true);
  assert.equal(result.indexed, true);
});

test("document projection works without optional OCR/search results", () => {
  const result = projectDocument(document, context);
  assert.equal(result.ocrAvailable, false);
  assert.equal(result.indexed, false);
});

test("OCR and index projectors preserve typed transport semantics", () => {
  const ocrResult = projectOcrResult(ocr, context);
  const indexResult = projectSearchIndex(index, context);
  assert.equal(ocrResult.textLength, ocr.text.length);
  assert.equal(indexResult.indexedTextLength, index.text.length);
  assert.equal(indexResult.contentHash, document.payload.content_hash);
});

test("document projection rejects stale scope, revision mismatch and hash mismatch", () => {
  assert.throws(
    () => projectDocument(document, { ...context, tenant_id: "tenant-2" }),
    /STALE_DOCUMENT_RESOURCE_SCOPE/,
  );

  assert.throws(
    () => projectDocument(
      document,
      context,
      { ...ocr, revision: 4 },
      index,
    ),
    /STALE_DOCUMENT_OCR_SCOPE/,
  );

  assert.throws(
    () => projectDocument(
      document,
      context,
      ocr,
      { ...index, content_hash: "sha256:" + "b".repeat(64) },
    ),
    /DOCUMENT_INDEX_CONTENT_HASH_MISMATCH/,
  );
});

test("document projectors reject unsupported versions and invalid hashes", () => {
  assert.throws(
    () => projectDocument(
      { ...document, contract_version: "2.0" } as never,
      context,
    ),
    /UNSUPPORTED_DOCUMENT_RESOURCE_CONTRACT/,
  );

  assert.throws(
    () => projectSearchIndex(
      { ...index, content_hash: "sha1:bad" },
      context,
    ),
    /INVALID_DOCUMENT_SEARCH_INDEX/,
  );
});
