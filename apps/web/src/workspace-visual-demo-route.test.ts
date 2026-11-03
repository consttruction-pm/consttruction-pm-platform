import assert from "node:assert/strict";
import test from "node:test";

import { createVisualDemoState, renderVisualDemo } from "./workspace-visual-demo.js";

import {
  liveWorkspaceProjectHref,
  shouldRenderVisualWorkspaceDemo,
  VISUAL_WORKSPACE_PREVIEW_PROJECT_ID,
} from "./workspace-visual-demo-route.js";

test("the shared preview project opens the visual workspace at its canonical URL", () => {
  assert.equal(
    shouldRenderVisualWorkspaceDemo(
      "/app",
      `?project=${VISUAL_WORKSPACE_PREVIEW_PROJECT_ID}`,
    ),
    true,
  );
});

test("the visual preview route does not replace the data-backed workspace", () => {
  assert.equal(
    shouldRenderVisualWorkspaceDemo(
      "/app",
      `?project=${VISUAL_WORKSPACE_PREVIEW_PROJECT_ID}&view=live`,
    ),
    false,
  );
  assert.equal(
    shouldRenderVisualWorkspaceDemo("/app", "?project=another-project"),
    false,
  );
});

test("the explicit visual-demo switch remains supported", () => {
  assert.equal(shouldRenderVisualWorkspaceDemo("/app", "?view=visual"), true);
  assert.equal(
    shouldRenderVisualWorkspaceDemo(
      "/app",
      "?project=another-project&view=visual",
    ),
    true,
  );
});

test("the shared preview project ID does not hijack the landing page", () => {
  assert.equal(
    shouldRenderVisualWorkspaceDemo(
      "/",
      `?project=${VISUAL_WORKSPACE_PREVIEW_PROJECT_ID}`,
    ),
    false,
  );
});

test("real project URLs preserve live mode across refresh and unrelated query parameters", () => {
  const href = new URL(
    "https://preview.example/app?locale=fa&view=visual",
  );
  const next = new URL(
    liveWorkspaceProjectHref(href.href, VISUAL_WORKSPACE_PREVIEW_PROJECT_ID),
  );
  assert.equal(next.searchParams.get("project"), VISUAL_WORKSPACE_PREVIEW_PROJECT_ID);
  assert.equal(next.searchParams.get("view"), "live");
  assert.equal(next.searchParams.get("locale"), "fa");
});

test("all expanded control modules render as navigable visual workspace windows", () => {
  const modules = [
    ["cost-control", "Cost & Financial Control"],
    ["progress-control", "Progress & Field Control"],
    ["procurement", "Procurement & Materials"],
    ["changes-claims", "Changes & Claims"],
    ["form-builder", "Form Builder"],
    ["organization", "Organization"],
    ["smart-guide", "Smart Guide"],
    ["assistant", "Engineering Intelligence Assistant"],
    ["search", "Global Search"],
    ["comments", "Comments & Notebook"],
  ] as const;
  for (const [windowId, heading] of modules) {
    const state = createVisualDemoState("en");
    state.window = windowId;
    const markup = renderVisualDemo(state);
    assert.match(markup, new RegExp(heading.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
    assert.match(markup, new RegExp(`data-vd-window="${windowId}"`));
  }
});

test("the visual workspace View > Layouts menu links to the added module windows", () => {
  const markup = renderVisualDemo(createVisualDemoState("en"));
  for (const windowId of ["cost-control", "progress-control", "procurement", "changes-claims", "form-builder", "organization", "smart-guide", "assistant", "search", "comments"]) {
    assert.ok(markup.includes(`"window":"${windowId}"`));
  }
});

test("visual workspace exposes the hierarchical navigation tree and right-side Add rail", () => {
  const markup = renderVisualDemo(createVisualDemoState("en"));
  assert.match(markup, /aria-label="Workspace navigation"/);
  assert.match(markup, /aria-label="Context commands"/);
  assert.match(markup, /class="cp-vd-rail-add" data-vd-dialog="module-actions"/);
  assert.match(markup, /data-vd-dialog="module-actions"/);
  assert.match(markup, /data-vd-window="comments"/);
});

test("the Add command opens a clearly preview-only item editor with typed fields", () => {
  const markup = renderVisualDemo(createVisualDemoState("en"));
  assert.match(markup, /data-vd-dialog="module-actions"/);
  assert.match(markup, /name="objectType"/);
  assert.match(markup, /name="objectName"/);
  assert.match(markup, /name="objectCode"/);
  assert.match(markup, /Visual preview only/);
});
