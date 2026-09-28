import assert from "node:assert/strict";
import test from "node:test";

import { renderMainWorkspace } from "./workspace-view.js";
import { createWorkspaceState, setDocuments } from "./workspace-model.js";

test("main workspace renders documents even when commercial records are empty", () => {
  const context = {
    tenant_id: "tenant-1",
    project_id: "project-1",
    revision: 4,
  };
  const state = setDocuments(createWorkspaceState(context), [{
    documentId: "DOC-1",
    resourceType: "rfi",
    title: "RFI — foundation reinforcement",
    status: "submitted",
    revision: 4,
    contentHash: "sha256:" + "a".repeat(64),
    linkedEntityRefs: ["A-101", "RFI-1"],
    hasStorageRef: true,
  }]);

  const container = {
    innerHTML: "",
    querySelectorAll: () => [],
  } as unknown as HTMLElement;

  renderMainWorkspace(container, state);

  assert.match(container.innerHTML, /data-section="documents"/);
  assert.match(container.innerHTML, /DOC-1/);
  assert.match(container.innerHTML, /RFI — foundation reinforcement/);
});


test("main workspace localizes the document section in Persian", () => {
  const context = { tenant_id: "tenant-1", project_id: "project-1", revision: 4 };
  const state = setDocuments(createWorkspaceState(context, "fa"), [{
    documentId: "DOC-1",
    resourceType: "rfi",
    title: "RFI — foundation reinforcement",
    status: "submitted",
    revision: 4,
    contentHash: "sha256:" + "a".repeat(64),
    linkedEntityRefs: ["A-101"],
    hasStorageRef: true,
  }]);
  const container = { innerHTML: "", querySelectorAll: () => [] } as unknown as HTMLElement;
  renderMainWorkspace(container, state);
  assert.match(container.innerHTML, /<h2>اسناد<\/h2>/);
  assert.match(container.innerHTML, /نسخه 4/);
});
