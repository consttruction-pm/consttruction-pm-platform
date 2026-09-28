import assert from "node:assert/strict";
import test from "node:test";

import { projectDocument } from "./workspace-document.js";

const scope = {
  tenant_id: "tenant-1",
  project_id: "project-1",
  project_revision: 5,
};

const snapshot = {
  document_id: "DOC-1",
  tenant_id: "tenant-1",
  project_id: "project-1",
  resource_type: "rfi",
  title: "RFI — foundation reinforcement",
  status: "submitted",
  storage_ref: "object://documents/DOC-1",
  content_hash: "sha256:" + "a".repeat(64),
  linked_entity_refs: ["A-101", "RFI-1"],
  revision: 5,
};

test("document projection preserves typed lifecycle metadata and links", () => {
  const projected = projectDocument(snapshot, scope);

  assert.equal(projected.documentId, "DOC-1");
  assert.equal(projected.resourceType, "rfi");
  assert.equal(projected.status, "submitted");
  assert.equal(projected.revision, 5);
  assert.equal(projected.hasStorageRef, true);
  assert.deepEqual(projected.linkedEntityRefs, ["A-101", "RFI-1"]);
});

test("document revision must match project revision", () => {
  assert.throws(
    () => projectDocument({ ...snapshot, revision: 4 }, scope),
    /STALE_DOCUMENT_SCOPE/,
  );
});

test("document projection rejects stale tenant or project scope", () => {
  assert.throws(
    () => projectDocument({ ...snapshot, tenant_id: "tenant-2" }, scope),
    /STALE_DOCUMENT_SCOPE/,
  );
});

test("document projection rejects invalid revision values", () => {
  assert.throws(
    () => projectDocument({ ...snapshot, revision: -1 }, scope),
    /INVALID_DOCUMENT_REVISION/,
  );
});

test("document projection rejects unsupported document types and statuses", () => {
  assert.throws(
    () => projectDocument({ ...snapshot, resource_type: "memo" }, scope),
    /UNSUPPORTED_DOCUMENT_TYPE/,
  );
  assert.throws(
    () => projectDocument({ ...snapshot, status: "archived" }, scope),
    /UNSUPPORTED_DOCUMENT_STATUS/,
  );
});

test("document projection rejects invalid content hashes and links", () => {
  assert.throws(
    () => projectDocument({ ...snapshot, content_hash: "bad" }, scope),
    /INVALID_DOCUMENT_CONTENT_HASH/,
  );
  assert.throws(
    () => projectDocument({ ...snapshot, content_hash: "sha256:" + "z".repeat(64) }, scope),
    /INVALID_DOCUMENT_CONTENT_HASH/,
  );
  assert.throws(
    () => projectDocument({ ...snapshot, content_hash: "sha256:" + "g".repeat(64) }, scope),
    /INVALID_DOCUMENT_CONTENT_HASH/,
  );
  assert.throws(
    () => projectDocument({ ...snapshot, linked_entity_refs: [""] }, scope),
    /INVALID_DOCUMENT_LINKS/,
  );
});
