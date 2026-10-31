import assert from "node:assert/strict";
import test from "node:test";

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
