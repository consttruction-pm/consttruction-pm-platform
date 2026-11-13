import assert from "node:assert/strict";
import test from "node:test";

import { createVisualDemoState, renderVisualDemo } from "./workspace-visual-demo.js";

import {
  liveWorkspaceProjectHref,
  resolveWorkspaceLoginPath,
  shouldRenderVisualWorkspaceDemo,
  workspaceLoginNextPath,
  VISUAL_WORKSPACE_PREVIEW_PROJECT_ID,
} from "./workspace-visual-demo-route.js";


test("every app entry uses the single authenticated workspace shell", () => {
  assert.equal(shouldRenderVisualWorkspaceDemo("/app", ""), false);
  assert.equal(shouldRenderVisualWorkspaceDemo("/app", "?locale=fa"), false);
  assert.equal(shouldRenderVisualWorkspaceDemo("/app", "?view=visual"), false);
  assert.equal(shouldRenderVisualWorkspaceDemo("/app", "?project=preview-rps-01"), false);
});

test("session recovery always returns to the authenticated workspace", () => {
  assert.equal(workspaceLoginNextPath(null), "/app?view=live");
  assert.equal(
    workspaceLoginNextPath(VISUAL_WORKSPACE_PREVIEW_PROJECT_ID),
    `/app?project=${VISUAL_WORKSPACE_PREVIEW_PROJECT_ID}&view=live`,
  );
  assert.equal(
    workspaceLoginNextPath("project-123"),
    "/app?project=project-123&view=live",
  );
});

test("the shared preview project opens the authenticated workspace, not a second demo shell", () => {
  assert.equal(
    shouldRenderVisualWorkspaceDemo(
      "/app",
      `?project=${VISUAL_WORKSPACE_PREVIEW_PROJECT_ID}`,
    ),
    false,
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

test("legacy visual-demo URLs resolve to the authenticated workspace", () => {
  assert.equal(shouldRenderVisualWorkspaceDemo("/app", "?view=visual"), false);
  assert.equal(
    shouldRenderVisualWorkspaceDemo(
      "/app",
      "?project=another-project&view=visual",
    ),
    false,
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
    ["cost-control", "Cost &amp; Financial Control"],
    ["progress-control", "Progress &amp; Field Control"],
    ["procurement", "Procurement &amp; Materials"],
    ["changes-claims", "Changes &amp; Claims"],
    ["form-builder", "Form Builder"],
    ["organization", "Organization"],
    ["smart-guide", "Smart Guide"],
    ["assistant", "Engineering Intelligence Assistant"],
    ["search", "Global Search"],
    ["comments", "Comments &amp; Notebook"],
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
  for (const windowId of ["cost-control", "progress-control", "procurement", "changes-claims", "organization", "search", "comments"]) {
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

test("module registers expose page commands, selectable rows, and contextual Details tabs", () => {
  const state = createVisualDemoState("en");
  state.window = "procurement";
  const markup = renderVisualDemo(state);
  assert.match(markup, /aria-label="Page commands"/);
  assert.match(markup, /data-vd-module-row="0"/);
  assert.match(markup, /data-vd-module-tab="general"/);
  assert.match(markup, /data-vd-module-tab="status"/);
  assert.match(markup, /data-vd-module-tab="relationships"/);
  assert.match(markup, /data-vd-module-tab="comments"/);
  assert.match(markup, /data-vd-module-tab="history"/);
  assert.match(markup, /cp-vd-module-details/);
});
test("module registers expose searchable and sortable row controls with an empty state", () => {
  const state = createVisualDemoState("en");
  state.window = "procurement";
  state.moduleSearch = "no-match";
  state.moduleSort = "ascending";
  const markup = renderVisualDemo(state);
  assert.match(markup, /data-vd-module-search value="no-match"/);
  assert.match(markup, /data-vd-module-sort/);
  assert.match(markup, /data-vd-module-sort-field/);
  assert.match(markup, /value="ascending" selected/);
  assert.match(markup, /No records match this search/);
});

test("workspace navigation groups are collapsible and active pages retain their group", () => {
  const state = createVisualDemoState("en");
  state.window = "procurement";
  state.collapsedNavGroups = ["controls"];
  const markup = renderVisualDemo(state);
  assert.match(markup, /data-vd-nav-group="controls" aria-expanded="false"/);
  assert.match(markup, /class="cp-vd-nav-group-items" hidden/);
  assert.match(markup, /data-vd-window="procurement" aria-current="page"/);
});
test("project-control and administration modules expose dedicated overview dashboards", () => {
  for (const windowId of ["cost-control", "progress-control", "procurement", "changes-claims", "form-builder", "organization", "smart-guide", "assistant", "search", "comments"] as const) {
    const state = createVisualDemoState("en");
    state.window = windowId;
    const markup = renderVisualDemo(state);
    assert.match(markup, /cp-vd-module-overview/);
    assert.match(markup, /cp-vd-metric-grid/);
    assert.match(markup, /cp-vd-module-chart/);
  }
});

test("WBS and Form Builder expose dedicated preview creation dialogs", () => {
  const wbs = renderVisualDemo(createVisualDemoState("en"));
  assert.match(wbs, /data-vd-dialog="new-wbs"/);
  assert.match(wbs, /name="wbsCode"/);
  assert.match(wbs, /name="wbsName"/);
  const forms = createVisualDemoState("en");
  forms.window = "form-builder";
  const formMarkup = renderVisualDemo(forms);
  assert.match(formMarkup, /data-vd-dialog="new-form"/);
  assert.match(formMarkup, /name="formId"/);
  assert.match(formMarkup, /Organization library/);
  assert.match(formMarkup, /Project library/);
});
test("every registered workspace window renders a concrete page surface", () => {
  const windows = [
    "projects", "wbs", "activities", "assignments", "resources", "roles", "calendars", "reports",
    "tracking", "documents", "expenses", "thresholds", "issues", "risks", "administration",
    "network", "trace", "timeline", "activity-profile", "resource-profile", "activity-sheet", "resource-sheet",
    "cost-control", "progress-control", "procurement", "changes-claims", "form-builder", "organization",
    "engineering-analysis", "project-watchdog", "scenario-lab", "optimization-studio", "project-quality",
    "construction-productivity", "data-reconciliation", "portfolio-capacity", "automation-center",
    "engineering-standards", "project-templates", "decision-register", "deadline-monitor", "data-quality",
    "recovery-center", "command-dictionaries", "smart-guide", "assistant", "search", "comments",
  ] as const;
  for (const windowId of windows) {
    const state = createVisualDemoState("en");
    state.window = windowId;
    const markup = renderVisualDemo(state);
    assert.match(markup, /class="cp-vd-windowbody/);
    assert.match(markup, /class="[^"]*cp-vd-winhead[^"]*"/);
    assert.ok(markup.length > 12000, `expected a fully rendered workspace for ${windowId}`);
  }
});
test("register column chooser uses the current page fields instead of activity fields", () => {
  const state = createVisualDemoState("en");
  state.window = "procurement";
  const markup = renderVisualDemo(state);
  assert.match(markup, /name="Package"/);
  assert.match(markup, /name="Material \/ Equipment"/);
  assert.doesNotMatch(markup, /name="Activity ID"/);
});
test("scheduling dialogs expose the key CPM handling and baseline options", () => {
  const markup = renderVisualDemo(createVisualDemoState("en"));
  for (const value of ["Retained Logic", "Progress Override", "Actual Dates", "Total Float → Activity Priority", "Primary baseline", "Secondary baseline", "Tertiary baseline"]) {
    assert.ok(markup.includes(value), `expected scheduling option: ${value}`);
  }
  for (const relationship of ["FS — Finish to Start", "SS — Start to Start", "FF — Finish to Finish", "SF — Start to Finish"]) {
    assert.ok(markup.includes(relationship), `expected relationship type: ${relationship}`);
  }
  assert.match(markup, /Lag calendar/);
  assert.match(markup, /Level only within available total float/);
});
test("Form Builder has separate organization and project libraries and a visual form designer", () => {
  const state = createVisualDemoState("en");
  state.window = "form-builder";
  const markup = renderVisualDemo(state);
  assert.match(markup, /data-vd-form-library="organization"/);
  assert.match(markup, /data-vd-form-library="project"/);
  assert.match(markup, /data-vd-form-tab="design"/);
  assert.match(markup, /data-vd-form-tab="fields"/);
  assert.match(markup, /data-vd-form-tab="workflow"/);
  assert.match(markup, /data-vd-form-tab="permissions"/);
  assert.match(markup, /data-vd-form-tab="versions"/);
  assert.match(markup, /accept="image\/jpeg,image\/png"/);
  assert.match(markup, /Transparent PNG logos retain their transparency/);
  state.formTab = "workflow";
  const workflowMarkup = renderVisualDemo(state);
  assert.match(workflowMarkup, /Publish to project record/);
});
test("Engineering Assistant shows project context, text, voice, file and approval surfaces", () => {
  const state = createVisualDemoState("en");
  state.window = "assistant";
  const markup = renderVisualDemo(state);
  assert.match(markup, /Current context/);
  assert.match(markup, /data-vd-window="trace"/);
  assert.match(markup, /data-vd-dialog="module-actions"/);
  assert.match(markup, /accept="\.xlsx,.xls,.docx,.doc,.mpp,.xer,.xml,.pdf,.csv"/);
  assert.match(markup, /Voice/);
  assert.match(markup, /requires your approval/i);
});

test("Smart Guide shows staged project setup and schedule quality checks", () => {
  const state = createVisualDemoState("en");
  state.window = "smart-guide";
  const markup = renderVisualDemo(state);
  assert.match(markup, /cp-vd-guide-steps/);
  assert.match(markup, /Connect logic/);
  assert.match(markup, /Review activities with no predecessors or successors/);
  assert.match(markup, /data-vd-window="assignments"/);
});

test("production login path is declared by the served shell, not hard-coded", () => {
  assert.equal(resolveWorkspaceLoginPath({ querySelector: () => null }), "/login");
  assert.equal(
    resolveWorkspaceLoginPath({
      querySelector: (selector) =>
        selector === 'meta[name="cubi-login-path"]'
          ? { getAttribute: () => "/preview/login" }
          : null,
    }),
    "/preview/login",
  );
});

test("a hostile login path declaration falls back to /login", () => {
  for (const declared of ["https://evil.example/login", "//evil.example", "/a\\b", ""]) {
    assert.equal(
      resolveWorkspaceLoginPath({
        querySelector: () => ({ getAttribute: () => declared }),
      }),
      "/login",
      declared,
    );
  }
});
