import assert from "node:assert/strict";
import test from "node:test";

import { isWorkspaceTopLayoutAvailable, isWorkspaceTraceLogicAvailable, readWorkspaceBottomLayout, renderMainWorkspace, workspaceMenuItems } from "./workspace-view.js";
import type { WorkspaceMenuKey } from "./workspace-model.js";
import type { WorkspaceControlSummary } from "./workspace-control-intelligence.js";
import { createWorkspaceState, setP6Presentation, withActivities, withRelationships, withWbsNodes } from "./workspace-model.js";
import { DEFAULT_PRESENTATION, normalizePresentation } from "./workspace-presentation.js";import type { ProjectSummary } from "./session-api.js";
import { setCollapsedWbsIds } from "./workspace-wbs-display.js";

type RenderContainer = {
  innerHTML: string;
  querySelectorAll: () => HTMLElement[];
};

function render(locale: "en" | "fa", activeMenu: WorkspaceMenuKey): string {
  const state = {
    ...createWorkspaceState(
      { tenant_id: "tenant-1", project_id: "project-1", revision: 3 },
      locale,
    ),
    activeMenu,
  };
  const container: RenderContainer = {
    innerHTML: "",
    querySelectorAll: () => [],
  };
  renderMainWorkspace(container as unknown as HTMLElement, state);
  return container.innerHTML;
}

test("workspace shell uses the canonical CUBI logo and focused module layout contracts", () => {
  for (const menu of ["project", "wbs", "schedule", "progress", "resources", "assignments", "roles", "calendars", "cost", "expenses", "documents", "reports", "tracking", "issues", "risks", "thresholds", "control", "settings", "administration", "exchange", "backup"] as const) {
    const html = render("en", menu);
    assert.match(html, new RegExp(`data-active-menu="${menu}"`));
    assert.ok(html.includes('class="cp-brand-logo"'));
    assert.ok(html.includes("cubi-platform-logo-primary.svg"));
    assert.ok(!html.includes(">Construction PM</div>"));
  }
  const html = render("en", "schedule");
  assert.match(html, /data-workspace-menu="project schedule"/);
  assert.match(html, /data-workspace-menu="schedule"/);
  assert.match(html, /data-workspace-menu="resources"/);
  assert.match(html, /id="cp-activity-grid"/);
  assert.match(html, /id="cp-gantt"/);
});
test("Gantt keeps one row per filtered activity even when none has schedule dates", () => {
  const base = createWorkspaceState({ tenant_id: "tenant-1", project_id: "project-1", revision: 3 }, "en");
  const withRows = withActivities(base, [
    { id: "A-1", wbsId: "W1", code: "A-1", name: "Unscheduled one" },
    { id: "A-2", wbsId: "W1", code: "A-2", name: "Unscheduled two" },
  ]);
  const state = {
    ...withWbsNodes(withRows, [
      { id: "W1", parentKind: "project" as const, parentWbsId: null, localCode: "W1", name: "Work", sequenceNumber: 1, recordRevision: 1 },
    ]),
    activeMenu: "schedule" as const,
  };
  const container: RenderContainer = { innerHTML: "", querySelectorAll: () => [] };
  renderMainWorkspace(container as unknown as HTMLElement, state);
  const html = container.innerHTML;
  assert.match(html, /data-gantt-activity-id="A-1"/);
  assert.match(html, /data-gantt-activity-id="A-2"/);
  assert.ok(!html.includes("No scheduled activities"));
});

test("the activity grid keeps one roving tab stop on the primary activity row", () => {
  const base = createWorkspaceState({ tenant_id: "tenant-1", project_id: "project-1", revision: 3 }, "en");
  const withRows = withActivities(base, [
    { id: "A-1", wbsId: "W1", code: "A-1", name: "First" },
    { id: "A-2", wbsId: "W1", code: "A-2", name: "Second" },
  ]);
  const state = {
    ...withWbsNodes(withRows, [
      { id: "W1", parentKind: "project" as const, parentWbsId: null, localCode: "W1", name: "Work", sequenceNumber: 1, recordRevision: 1 },
    ]),
    activeMenu: "schedule" as const,
  };
  const tabStops = (candidate: typeof state): Array<[string, string]> => {
    const container: RenderContainer = { innerHTML: "", querySelectorAll: () => [] };
    renderMainWorkspace(container as unknown as HTMLElement, candidate);
    return [...container.innerHTML.matchAll(/<tr role="row" data-activity-id="([^"]+)"[^>]*tabindex="(-?\d+)"/g)]
      .map((match) => [match[1], match[2]] as [string, string]);
  };
  assert.deepEqual(tabStops(state), [["A-1", "0"], ["A-2", "-1"]], "with no selection the first activity carries the tab stop");
  assert.deepEqual(tabStops({ ...state, selectedActivityId: "A-2" }), [["A-1", "-1"], ["A-2", "0"]], "the primary selection owns the tab stop");
});

test("WBS panel renders localized create controls and permits creating a project root", () => {
  const english = render("en", "project");
  assert.match(english, /data-wbs-create-form/);
  assert.match(english, /Project root/);
  assert.match(english, /name="sequence_number"/);

  const persian = render("fa", "project");
  assert.match(persian, /افزودن ساختار شکست/);
  assert.match(persian, /ریشهٔ پروژه/);
});

test("WBS create form dispatches validated fields to its workspace callback", () => {
  const listeners = new Map<string, (event: Event) => void>();
  const container = {
    innerHTML: "",
    querySelectorAll: () => [],
    addEventListener: (type: string, listener: (event: Event) => void) => listeners.set(type, listener),
  };
  let created: { code: string; name: string; sequenceNumber: number; parentWbsId: string | null } | null = null;
  renderMainWorkspace(
    container as unknown as HTMLElement,
    createWorkspaceState({ tenant_id: "tenant-1", project_id: "project-1", revision: 3 }, "en"),
    { onWbsCreate: (input) => { created = input; } },
  );
  const values: Record<string, { value: string }> = {
    '[name="code"]': { value: "  STR-01 " },
    '[name="name"]': { value: " Structure " },
    '[name="sequence_number"]': { value: "4" },
    '[name="parent_wbs_id"]': { value: "WBS-ROOT" },
  };
  const form = {
    matches: (selector: string) => selector === "[data-wbs-create-form]",
    querySelector: (selector: string) => values[selector] ?? null,
  };
  let prevented = false;
  listeners.get("submit")?.({ target: form, preventDefault: () => { prevented = true; } } as unknown as Event);
  assert.equal(prevented, true);
  assert.deepEqual(created, {
    code: "STR-01",
    name: "Structure",
    sequenceNumber: 4,
    parentWbsId: "WBS-ROOT",
  });
});

test("Calendar Register displays only authenticated project calendar records", () => {
  const state = {
    ...createWorkspaceState(
      { tenant_id: "tenant-1", project_id: "project-1", revision: 3 },
      "en",
    ),
    activeMenu: "calendars" as const,
    calendarCatalog: {
      status: "loaded" as const,
      calendars: [{
        calendarId: "CAL-01",
        calendarVersion: "v2",
        kind: "working-time",
        calendarType: "project",
        name: "Project Standard",
        recordRevision: 5,
      }],
      errorCode: null,
    },
  };
  const container = { innerHTML: "", querySelectorAll: () => [] };
  renderMainWorkspace(container as unknown as HTMLElement, state);
  assert.match(container.innerHTML, /CAL-01/);
  assert.match(container.innerHTML, /Project Standard/);
  assert.match(container.innerHTML, /working-time/);
  assert.doesNotMatch(container.innerHTML, />0<\/span>/);
});

test("WBS register exposes connected add, delete and view controls", () => {
  const html = render("en", "wbs");
  assert.match(html, /data-rail-action="wbs"/);
  assert.match(html, /data-rail-action="wbs">Add WBS/);
  assert.match(html, /data-wbs-delete disabled/);
  assert.match(html, /data-wbs-view="table"/);
  assert.match(html, /data-wbs-view="chart"/);
  assert.doesNotMatch(html, /WBS chart view is not connected yet/);
});

test("WBS chart view draws the loaded hierarchy and keeps selection on the same records", () => {
  const listeners = new Map<string, (event: Event) => void>();
  const hierarchy = { innerHTML: "" };
  const chartButton = {
    dataset: { wbsView: "chart" } as Record<string, string>,
    setAttribute: () => undefined,
    classList: { toggle: () => undefined },
  };
  const container = {
    innerHTML: "",
    querySelector: (selector: string) => (selector === "[data-wbs-hierarchy]" ? hierarchy : null),
    querySelectorAll: () => [chartButton],
    addEventListener: (type: string, listener: (event: Event) => void) => listeners.set(type, listener),
  };
  const state = withWbsNodes(
    createWorkspaceState({ tenant_id: "tenant-1", project_id: "project-1", revision: 3 }, "en"),
    [
      { id: "WBS-1", parentKind: "project", parentWbsId: null, localCode: "1", name: "Project management", sequenceNumber: 1, recordRevision: 2 },
      { id: "WBS-2", parentKind: "wbs", parentWbsId: "WBS-1", localCode: "2", name: "Civil works", sequenceNumber: 1, recordRevision: 4 },
    ],
  );
  renderMainWorkspace(container as unknown as HTMLElement, state);
  const clickTarget = {
    dataset: { wbsView: "chart" },
    closest: (selector: string) => (selector.includes("[data-wbs-view]") ? chartButton : null),
  };
  listeners.get("click")?.({ target: clickTarget } as unknown as Event);
  assert.match(hierarchy.innerHTML, /data-wbs-chart/);
  assert.match(hierarchy.innerHTML, /1<\/span>\s*<strong>Project management<\/strong>/);
  assert.match(hierarchy.innerHTML, /2<\/span>\s*<strong>Civil works<\/strong>/);
  assert.match(hierarchy.innerHTML, /data-wbs-id="WBS-2"/);
});

test("Documents surface is a live register page instead of a static read-model table", () => {
  const html = render("en", "documents");
  assert.match(html, /data-documents-page/);
  assert.match(html, /Project Documents/);
  assert.doesNotMatch(html, /id="cp-documents-register"/);
  assert.doesNotMatch(html, /data-document-detail-tab/);
});

test("Control page states honestly when no control-intelligence snapshot is loaded", () => {
  const html = render("en", "control");
  assert.match(html, /cp-control-window/);
  assert.match(html, /No control-intelligence snapshot is loaded for this project revision/);
  assert.match(html, /no analysis is calculated in the browser/);
});

test("Control page renders the stored control-room metrics, findings and actions", () => {
  const source = { source_id: "SRC-1", source_type: "activity", locator: "A-100", revision: 3 };
  const summary: WorkspaceControlSummary = {
    resultId: "CR-RESULT-1",
    generatedAt: "2026-11-04T10:00:00Z",
    summaryKey: "CONTROL_SUMMARY",
    metrics: { schedule_variance_days: 3, open_findings: 1 },
    findings: [{
      finding_id: "F-1",
      domain: "schedule",
      severity: "warning",
      title_key: "Schedule slip detected",
      detail_key: "Finish date moved beyond the stored baseline",
      source_refs: [source],
    }],
    proposedActions: [{
      action_id: "PA-1",
      action_type: "review",
      title_key: "Review the recovery plan",
      source_refs: [source],
      requires_approval: true,
    }],
  };
  const state = {
    ...createWorkspaceState({ tenant_id: "tenant-1", project_id: "project-1", revision: 3 }, "en"),
    activeMenu: "control" as const,
    controlSummary: summary,
  };
  const container: RenderContainer = { innerHTML: "", querySelectorAll: () => [] };
  renderMainWorkspace(container as unknown as HTMLElement, state);
  const html = container.innerHTML;
  assert.match(html, /CR-RESULT-1/);
  assert.match(html, /2026-11-04T10:00:00Z/);
  assert.match(html, /schedule_variance_days/);
  assert.match(html, /<strong>3<\/strong>/);
  assert.match(html, /Schedule slip detected/);
  assert.match(html, /Finish date moved beyond the stored baseline/);
  assert.match(html, /Review the recovery plan/);
  assert.match(html, /Approval Required/);
  assert.match(html, /performs no client-side analysis/);
});

test("Activity Group and Sort defaults to WBS in English and Persian", () => {
  const english = render("en", "schedule");
  assert.match(english, /<select data-activity-group aria-label="Group by">\s*<option value="none">No grouping<\/option>\s*<option value="wbs" selected>WBS<\/option>/);
  assert.match(english, /<select data-activity-sort aria-label="Sort by">\s*<option value="">Original order<\/option>\s*<option value="wbs" selected>WBS<\/option>/);

  const persian = render("fa", "schedule");
  assert.match(persian, /گروه‌بندی بر اساس/);
  assert.match(persian, /<option value="wbs" selected>ساختار شکست<\/option>/);
});

test("Activity entry is localized and requires an authoritative WBS selection", () => {
  const empty = render("en", "schedule");
  assert.match(empty, /data-activity-create-form/);
  assert.match(empty, /name="activity_id"/);
  assert.match(empty, /name="duration_value"/);
  assert.match(empty, /name="wbs_id" required disabled/);
  const persian = render("fa", "schedule");
  assert.match(persian, /افزودن فعالیت/);
  assert.match(persian, /واحد مدت/);
  assert.match(persian, /name="activity_type"/);
  assert.match(persian, /نوع درصد تکمیل/);
  assert.match(persian, /وابسته به منابع/);
  assert.match(empty, /name="percent_complete_type"/);
  assert.match(empty, /name="leveling_priority"/);
});

test("Activity create form dispatches typed fields and selected WBS to its callback", () => {
  const listeners = new Map<string, (event: Event) => void>();
  const container = {
    innerHTML: "",
    querySelectorAll: () => [],
    addEventListener: (type: string, listener: (event: Event) => void) => listeners.set(type, listener),
  };
  const state = withWbsNodes(
    createWorkspaceState({ tenant_id: "tenant-1", project_id: "project-1", revision: 3 }, "en"),
    [{ id: "WBS-1", parentKind: "project", parentWbsId: null, localCode: "1", name: "Root", sequenceNumber: 0, recordRevision: 1 }],
  );
  let created: { activityId: string; name: string; durationValue: number; durationUnit: string; wbsId: string; activityType: string; status: string; statusCode: string; percentCompleteType: string; levelingPriority: string } | null = null;
  renderMainWorkspace(container as unknown as HTMLElement, state, {
    onActivityCreate: (input) => { created = input; },
  });
  const values: Record<string, { value: string }> = {
    '[name="activity_id"]': { value: " A-101 " },
    '[name="name"]': { value: " Foundation " },
    '[name="duration_value"]': { value: "2.5" },
    '[name="duration_unit"]': { value: "working-day" },
    '[name="wbs_id"]': { value: "WBS-1" },
    '[name="activity_type"]': { value: "Resource Dependent" },
    '[name="status"]': { value: "In Progress" },
    '[name="status_code"]': { value: "Active" },
    '[name="percent_complete_type"]': { value: "PHYSICAL" },
    '[name="leveling_priority"]': { value: "High" },
  };
  const form = {
    matches: (selector: string) => selector === "[data-activity-create-form]",
    querySelector: (selector: string) => values[selector] ?? null,
  };
  let prevented = false;
  listeners.get("submit")?.({ target: form, preventDefault: () => { prevented = true; } } as unknown as Event);
  assert.equal(prevented, true);
  assert.deepEqual(created, {
    activityId: "A-101",
    name: "Foundation",
    durationValue: 2.5,
    durationUnit: "working-day",
    wbsId: "WBS-1",
    activityType: "Resource Dependent",
    status: "In Progress",
    statusCode: "Active",
    percentCompleteType: "PHYSICAL",
    levelingPriority: "High",
  });
});

test("rendered schedule surface exposes localized label and implemented status", () => {
  const html = render("en", "schedule");

  assert.match(html, /<strong>Schedule<\/strong>/);
  assert.match(html, /data-surface-status="implemented">Implemented<\/span>/);
  assert.match(html, /Activity Grid/);
  assert.match(html, /Gantt Chart/);
});

test("Activities window exposes a real Layout Options dialog with current timescale and relationship visibility", () => {
  const english = render("en", "schedule");
  assert.match(english, /data-layout-options-open/);
  assert.match(english, /data-layout-options-dialog/);
  assert.match(english, /data-layout-timescale/);
  assert.match(english, /data-layout-links/);
  assert.match(english, /Show relationship lines/);
  assert.match(english, /Display interval/);

  const persian = render("fa", "schedule");
  assert.match(persian, /گزینه‌های چیدمان/);
  assert.match(persian, /مقیاس زمانی/);
  assert.match(persian, /نمایش خطوط روابط/);
});

test("Activity Details exposes the Bottom Layout Options tab customization dialog", () => {
  const html = render("en", "schedule");
  assert.match(html, /data-activity-details-options-open/);
  assert.match(html, /data-activity-details-options-dialog/);
  assert.match(html, /data-activity-detail-visible="general" checked/);
  assert.match(html, /data-activity-detail-visible="risks" checked/);
  assert.match(html, /Customize Activity Details/);
  assert.match(html, /Choose which detail tabs are visible/);
});

test("Activities Layout Options inventories top and bottom chart layouts without enabling unimplemented renderers", () => {
  const html = render("en", "schedule");
  assert.match(html, /data-top-layout/);
  assert.match(html, /Activity Table \+ Gantt Chart/);
  assert.match(html, /Activity Network/);
  assert.match(html, /Activity Usage Spreadsheet/);
  assert.match(html, /Resource Usage Profile/);
  assert.match(html, /data-bottom-layout/);
  assert.match(html, /Show critical path/);
  assert.match(html, /Show progress line/);
  assert.match(html, /Show baseline bars/);
  assert.match(html, /disabled>Activity Network/);
});

test("Activities Details renders the complete Version 26 tab inventory without fabricating unloaded records", () => {
  const html = render("en", "schedule");
  for (const tab of ["general", "status", "resources", "predecessors", "successors", "relationships", "codes", "notebook", "steps", "wps-docs", "expenses", "issues", "risks", "summary", "udfs", "update-history", "calendar"]) {
    assert.ok(html.includes(`data-activity-detail-tab="${tab}"`), `missing Activity Details tab: ${tab}`);
  }
  assert.match(html, /Select an activity in the table or Gantt chart/);
});
test("workspace view leaves window tabs to the single desktop tab bar instead of duplicating them", () => {
  const state = createWorkspaceState({ tenant_id: "tenant-1", project_id: "project-1", revision: 3 }, "en");
  const container: RenderContainer = { innerHTML: "", querySelectorAll: () => [] };
  renderMainWorkspace(container as unknown as HTMLElement, state, {
    openWindows: ["project", "schedule"],
  });
  assert.doesNotMatch(container.innerHTML, /class="cp-window-tabs"/);
  assert.doesNotMatch(container.innerHTML, /data-window-tab=/);
  assert.doesNotMatch(container.innerHTML, /class="cp-window-tab/);
});

test("View menu Timescale command opens the current window Layout Options dialog", () => {
  const listeners = new Map<string, (event: Event) => void>();
  let opened = false;
  const dialog = { showModal: () => { opened = true; }, setAttribute: () => {} };
  const container = {
    innerHTML: "",
    querySelectorAll: () => [],
    querySelector: (selector: string) => selector === "[data-layout-options-dialog]" ? dialog : null,
    addEventListener: (type: string, listener: (event: Event) => void) => listeners.set(type, listener),
  };
  renderMainWorkspace(
    container as unknown as HTMLElement,
    createWorkspaceState({ tenant_id: "tenant-1", project_id: "project-1", revision: 3 }, "en"),
  );
  const target = { dataset: { shellCommand: "Timescale" }, closest: () => target };
  listeners.get("click")?.({ target } as unknown as Event);
  assert.equal(opened, true);
});

test("rendered preview surfaces remain explicitly marked", () => {
  const html = render("en", "reports");

  assert.match(html, /<strong>Reports<\/strong>/);
  assert.match(html, /data-surface-status="preview">Preview<\/span>/);
  assert.match(html, /Reports/);
  assert.match(html, /Print/);
});

test("rendered navigation surface follows Persian locale and RTL direction", () => {
  const html = render("fa", "schedule");

  assert.match(html, /dir="rtl"/);
  assert.match(html, /<strong>زمان‌بندی<\/strong>/);
  assert.match(html, /جدول فعالیت‌ها/);
  assert.match(html, /گانت/);
  assert.match(html, /data-surface-status="implemented">پیاده‌سازی‌شده<\/span>/);
});


test("menu selection wiring forwards the selected workspace surface", () => {
  const state = createWorkspaceState(
    { tenant_id: "tenant-1", project_id: "project-1", revision: 3 },
    "en",
  );
  const selected: WorkspaceMenuKey[] = [];
  let clickListener: ((event: Event) => void) | undefined;
  const reportsButton = {
    dataset: { menu: "reports" },
    closest: () => reportsButton,
  };
  const container: RenderContainer & { addEventListener: (event: string, listener: (event: Event) => void) => void } = {
    innerHTML: "",
    querySelectorAll: () => [],
    addEventListener: (event, listener) => { if (event === "click") clickListener = listener; },
  };
  renderMainWorkspace(container as unknown as HTMLElement, state, {
    onMenuSelect: (menu) => selected.push(menu),
  });
  clickListener?.({ target: reportsButton } as unknown as Event);
  assert.deepEqual(selected, ["reports"]);
});


test("selection-only rerenders update DOM incrementally", () => {
  const base = createWorkspaceState(
    { tenant_id: "tenant-1", project_id: "project-1", revision: 3 },
    "en",
  );
  const attributes: Array<[string, string]> = [];
  const activityRow = {
    dataset: { activityId: "A-1" },
    classList: { toggled: [] as Array<[string, boolean]>, toggle(name: string, value: boolean) { this.toggled.push([name, value]); } },
    setAttribute(name: string, value: string) { attributes.push([name, value]); },
  };
  const ganttRow = {
    dataset: { ganttActivityId: "A-1" },
    classList: { toggled: [] as Array<[string, boolean]>, toggle(name: string, value: boolean) { this.toggled.push([name, value]); } },
    setAttribute(name: string, value: string) { attributes.push([name, value]); },
  };
  const details = { innerHTML: "" };
  const container = {
    innerHTML: "",
    querySelectorAll: (selector: string) => selector === "[data-activity-id]"
      ? [activityRow]
      : selector === "[data-gantt-activity-id]"
        ? [ganttRow]
        : [],
    querySelector: (selector: string) => selector === "#cp-details" ? details : null,
    addEventListener: () => {},
  };

  renderMainWorkspace(container as unknown as HTMLElement, base);
  const initialHtml = container.innerHTML;
  renderMainWorkspace(container as unknown as HTMLElement, { ...base, selectedActivityId: "A-1" });

  assert.equal(container.innerHTML, initialHtml);
  assert.deepEqual(activityRow.classList.toggled, [["is-selected", true]]);
  assert.deepEqual(ganttRow.classList.toggled, [["is-selected", true]]);
  assert.ok(attributes.some(([name, value]) => name === "aria-selected" && value === "true"));
  assert.ok(attributes.some(([name, value]) => name === "aria-pressed" && value === "true"));
  assert.match(details.innerHTML, /A-1/);
});

test("activity deselection also stays incremental", () => {
  const base = { ...createWorkspaceState(
    { tenant_id: "tenant-1", project_id: "project-1", revision: 3 },
    "en",
  ), selectedActivityId: "A-1" };
  const activityRow = {
    dataset: { activityId: "A-1" },
    classList: { toggled: [] as Array<[string, boolean]>, toggle(name: string, value: boolean) { this.toggled.push([name, value]); } },
    setAttribute: () => {},
  };
  const ganttRow = {
    dataset: { ganttActivityId: "A-1" },
    classList: { toggled: [] as Array<[string, boolean]>, toggle(name: string, value: boolean) { this.toggled.push([name, value]); } },
    setAttribute: () => {},
  };
  const details = { innerHTML: "" };
  const container = {
    innerHTML: "",
    querySelectorAll: (selector: string) => selector === "[data-activity-id]"
      ? [activityRow]
      : selector === "[data-gantt-activity-id]"
        ? [ganttRow]
        : [],
    querySelector: (selector: string) => selector === "#cp-details" ? details : null,
    addEventListener: () => {},
  };

  renderMainWorkspace(container as unknown as HTMLElement, base);
  const initialHtml = container.innerHTML;
  renderMainWorkspace(container as unknown as HTMLElement, { ...base, selectedActivityId: null });

  assert.equal(container.innerHTML, initialHtml);
  assert.deepEqual(activityRow.classList.toggled, [["is-selected", false]]);
  assert.deepEqual(ganttRow.classList.toggled, [["is-selected", false]]);
  assert.match(details.innerHTML, /—/);
});

test("full rerenders do not accumulate delegated workspace listeners", () => {
  const base = createWorkspaceState(
    { tenant_id: "tenant-1", project_id: "project-1", revision: 3 },
    "en",
  );
  const registrations: string[] = [];
  const container = {
    innerHTML: "",
    querySelectorAll: () => [],
    addEventListener: (type: string) => { registrations.push(type); },
  };

  renderMainWorkspace(container as unknown as HTMLElement, base);
  renderMainWorkspace(container as unknown as HTMLElement, { ...base, locale: "fa", direction: "rtl" });

  assert.deepEqual(registrations, [
    "click", "click", "contextmenu", "pointerdown", "keydown",
    "scroll", "focusout", "toggle", "pointerdown", "input", "submit", "click", "contextmenu", "dblclick", "keydown", "change",
  ]);
});

test("delegated activity events use the latest render callbacks after incremental updates", () => {
  const base = createWorkspaceState(
    { tenant_id: "tenant-1", project_id: "project-1", revision: 3 },
    "en",
  );
  let clickListener: ((event: Event) => void) | undefined;
  const activityTarget = {
    dataset: { activityId: "A-1" },
    closest: () => activityTarget,
  };
  const container = {
    innerHTML: "",
    querySelectorAll: () => [],
    querySelector: () => null,
    addEventListener: (type: string, listener: (event: Event) => void) => {
      if (type === "click") clickListener = listener;
    },
  };

  const firstSelected: string[] = [];
  const secondSelected: string[] = [];
  renderMainWorkspace(container as unknown as HTMLElement, base, {
    onActivitySelect: (activityId) => firstSelected.push(activityId),
  });
  renderMainWorkspace(container as unknown as HTMLElement, {
    ...base,
    selectedActivityId: "A-1",
  }, {
    onActivitySelect: (activityId) => secondSelected.push(activityId),
  });

  clickListener?.({ target: activityTarget } as unknown as Event);

  assert.deepEqual(firstSelected, []);
  assert.deepEqual(secondSelected, ["A-1"]);
});

test("menu-only rerenders replace only the navigation surface", () => {
  const base = createWorkspaceState(
    { tenant_id: "tenant-1", project_id: "project-1", revision: 3 },
    "en",
  );
  const navigation = { outerHTML: "" };
  const addMenu = { outerHTML: "" };
  const menuButtons = [
    { dataset: { menu: "schedule" }, setAttribute: () => {} },
    { dataset: { menu: "reports" }, setAttribute: () => {} },
  ];
  const container = {
    innerHTML: "",
    querySelectorAll: (selector: string) => selector === "[data-menu]" ? menuButtons : [],
    querySelector: (selector: string) => selector === ".cp-navigation-surface"
      ? navigation
      : selector === "[data-context-add]" ? addMenu : null,
    addEventListener: () => {},
  };

  renderMainWorkspace(container as unknown as HTMLElement, base);
  const initialHtml = container.innerHTML;
  renderMainWorkspace(container as unknown as HTMLElement, { ...base, activeMenu: "reports" });

  assert.equal(container.innerHTML, initialHtml);
  assert.ok(navigation.outerHTML.includes("<strong>Reports</strong>"));
  assert.ok(navigation.outerHTML.includes('data-surface-status="preview"'));
  // The incremental path repaints the contextual Add menu for the new window.
  assert.match(addMenu.outerHTML, /This window has no create action\./);
  assert.doesNotMatch(addMenu.outerHTML, /project\.add-activity/);
});

test("incremental selection rerenders avoid workspace innerHTML replacement", () => {
  const base = createWorkspaceState(
    { tenant_id: "tenant-1", project_id: "project-1", revision: 3 },
    "en",
  );
  let html = "";
  let innerHtmlWrites = 0;
  const container = {
    get innerHTML() {
      return html;
    },
    set innerHTML(value: string) {
      innerHtmlWrites += 1;
      html = value;
    },
    querySelectorAll: () => [],
    querySelector: () => null,
    addEventListener: () => {},
  };

  renderMainWorkspace(container as unknown as HTMLElement, base);
  assert.equal(innerHtmlWrites, 1);

  renderMainWorkspace(container as unknown as HTMLElement, {
    ...base,
    selectedActivityId: "A-1",
  });

  assert.equal(innerHtmlWrites, 1);
});

test("representative activity sets avoid full workspace replacement on selection", () => {
  const base = createWorkspaceState(
    { tenant_id: "tenant-1", project_id: "project-1", revision: 3 },
    "en",
  );
  const activities = Array.from({ length: 500 }, (_, index) => ({
    id: `A-${index + 1}`,
    wbsId: "WBS-1",
    code: `ACT-${index + 1}`,
    name: `Activity ${index + 1}`,
    cells: {},
  }));
  const state = { ...base, activities };
  let html = "";
  let innerHtmlWrites = 0;
  let initialHtmlLength = 0;
  const container = {
    get innerHTML() {
      return html;
    },
    set innerHTML(value: string) {
      innerHtmlWrites += 1;
      html = value;
      if (innerHtmlWrites === 1) initialHtmlLength = value.length;
    },
    querySelectorAll: () => [],
    querySelector: () => null,
    addEventListener: () => {},
  };

  renderMainWorkspace(container as unknown as HTMLElement, state);
  renderMainWorkspace(container as unknown as HTMLElement, {
    ...state,
    selectedActivityId: "A-250",
  });

  assert.equal(activities.length, 500);
  assert.ok(initialHtmlLength > 5000);
  assert.equal(innerHtmlWrites, 1);
  assert.equal(container.innerHTML.length, initialHtmlLength);
});

test("WBS selection still uses a full render because it clears activity selection", () => {
  const base = {
    ...createWorkspaceState(
      { tenant_id: "tenant-1", project_id: "project-1", revision: 3 },
      "en",
    ),
    selectedActivityId: "A-1",
  };
  let html = "";
  let innerHtmlWrites = 0;
  const container = {
    get innerHTML() {
      return html;
    },
    set innerHTML(value: string) {
      innerHtmlWrites += 1;
      html = value;
    },
    querySelectorAll: () => [],
    querySelector: () => null,
    addEventListener: () => {},
  };

  renderMainWorkspace(container as unknown as HTMLElement, base);
  assert.equal(innerHtmlWrites, 1);

  renderMainWorkspace(container as unknown as HTMLElement, {
    ...base,
    selectedWbsId: "WBS-1",
    selectedActivityId: null,
  });

  assert.equal(innerHtmlWrites, 2);
});

test("renderer honors visible workspace panel flags", () => {
  const state = {
    ...createWorkspaceState(
      { tenant_id: "tenant-1", project_id: "project-1", revision: 3 },
      "en",
    ),
    visiblePanels: {
      project_wbs: false,
      activity_grid: true,
      gantt: false,
      details: false,
    },
  };
  const container: RenderContainer = {
    innerHTML: "",
    querySelectorAll: () => [],
  };
  renderMainWorkspace(container as unknown as HTMLElement, state);

  assert.match(container.innerHTML, /class="cp-panel cp-wbs" hidden/);
  assert.match(container.innerHTML, /class="cp-panel cp-gantt" hidden/);
  assert.match(container.innerHTML, /class="cp-panel cp-details" hidden/);
  assert.match(container.innerHTML, /class="cp-panel cp-grid"/);
});


test("Persian workspace localizes accessibility and chooser labels", () => {
  const state = {
    ...createWorkspaceState(
      { tenant_id: "tenant-1", project_id: "project-1", revision: 3 },
      "fa",
    ),
    p6FieldRegistry: {
      registry_version: "p6-field-registry.v1",
      reference_product: "Oracle Primavera P6 Professional",
      reference_version: "V1",
      status: "verified",
      fields: [
        {
          field_id: "activity.activity_id",
          subject_area: "activity",
          p6_field: "Activity ID",
          display_name: "شناسه فعالیت",
          data_type: "string",
          writable: false,
          computed: false,
          disposition: "verified",
        },
      ],
    } as const,
    p6Layout: {
      schema_version: "p6-layout.v1",
      scope: "project",
      view_id: "activity",
      revision: 1,
      columns: [
        {
          field_id: "activity.activity_id",
          visible: true,
          order: 0,
          width: 120,
          label: undefined,
          alignment: "start",
          pinned: false,
          frozen: false,
        },
      ],
    } as const,
  };
  const container: RenderContainer = { innerHTML: "", querySelectorAll: () => [] };
  renderMainWorkspace(container as unknown as HTMLElement, state);

  assert.match(container.innerHTML, /aria-label="منوی اصلی"/);
  assert.match(container.innerHTML, /aria-label="انتخاب‌گر فیلد"/);
  assert.match(container.innerHTML, /<strong>فیلدها<\/strong>/);
  assert.match(container.innerHTML, /aria-label="حذف: شناسه فعالیت"/);
  assert.doesNotMatch(container.innerHTML, /aria-label="Main Menu"/);
  assert.doesNotMatch(container.innerHTML, /P6 Field Chooser/);
  assert.doesNotMatch(container.innerHTML, /aria-label="حذف"/);
  const visibleText = container.innerHTML.replace(/<[^>]*>/g, " ");
  assert.doesNotMatch(visibleText, /Oracle|Primavera|P6/i);
});


test("P6 chooser width controls forward authoritative presentation changes", () => {
  const state = {
    ...createWorkspaceState(
      { tenant_id: "tenant-1", project_id: "project-1", revision: 3 },
      "en",
    ),
    p6FieldRegistry: {
      registry_version: "p6-field-registry.v1",
      reference_product: "Oracle Primavera P6 Professional",
      reference_version: "26",
      status: "active",
      fields: [{
        field_id: "activity.activity_id",
        subject_area: "activity",
        p6_field: "Activity ID",
        display_name: "Activity ID",
        data_type: "string",
        writable: false,
        computed: false,
        disposition: "supported",
      }],
    } as const,
    p6Layout: {
      schema_version: "p6-layout.v1",
      scope: "project",
      view_id: "activity-grid",
      revision: 1,
      columns: [{
        field_id: "activity.activity_id",
        visible: true,
        order: 0,
        width: 120,
        alignment: "start",
        pinned: false,
        frozen: false,
      }],
    } as const,
  };
  const changes: Array<{ fieldId: string; width: number }> = [];
  let clickListener: ((event: Event) => void) | undefined;
  const widthButton = {
    dataset: { p6FieldWidth: "activity.activity_id", p6FieldWidthDelta: "increase" },
    closest: () => widthButton,
  };
  const container: RenderContainer & { addEventListener: (event: string, listener: (event: Event) => void) => void } = {
    innerHTML: "",
    querySelectorAll: () => [],
    addEventListener: (event, listener) => { if (event === "click") clickListener = listener; },
  };

  renderMainWorkspace(container as unknown as HTMLElement, state, {
    onP6FieldWidthChange: (fieldId, width) => changes.push({ fieldId, width }),
  });
  clickListener?.({ target: widthButton } as unknown as Event);

  assert.deepEqual(changes, [{ fieldId: "activity.activity_id", width: 140 }]);
  assert.match(container.innerHTML, /title="Wider"/);
  assert.match(container.innerHTML, /aria-label="Wider"/);
  assert.match(container.innerHTML, /title="Narrower"/);
  assert.match(container.innerHTML, /aria-label="Narrower"/);
  assert.ok(container.innerHTML.includes('data-p6-field-alignment="activity.activity_id"'));
  assert.match(container.innerHTML, /aria-label="Align left"/);
  assert.match(container.innerHTML, /aria-label="Align center"/);
  assert.match(container.innerHTML, /aria-label="Align right"/);
  assert.ok(container.innerHTML.includes('data-p6-field-pin="activity.activity_id"'));
  assert.match(container.innerHTML, /aria-label="Pin"/);
  assert.ok(container.innerHTML.includes('data-p6-field-freeze="activity.activity_id"'));
  assert.match(container.innerHTML, /aria-label="Freeze"/);
});


test("layout history controls render localized state and dispatch undo, redo and restore", () => {
  const state = {
    ...createWorkspaceState({ tenant_id: "tenant-1", project_id: "project-1", revision: 3 }, "en"),
    p6FieldRegistry: {
      registry_version: "p6-field-registry.v1",
      reference_product: "Oracle Primavera P6 Professional",
      reference_version: "26",
      status: "active",
      fields: [{
        field_id: "activity.activity_id",
        subject_area: "activity",
        p6_field: "Activity ID",
        display_name: "Activity ID",
        data_type: "string",
        writable: false,
        computed: false,
        disposition: "supported",
      }],
    } as const,
    p6Layout: {
      schema_version: "p6-layout.v1",
      scope: "project",
      view_id: "activity-grid",
      revision: 4,
      columns: [{
        field_id: "activity.activity_id",
        visible: true,
        order: 0,
        width: 120,
        alignment: "start",
        pinned: false,
        frozen: false,
      }],
    } as const,
  };
  const events: string[] = [];
  let clickListener: ((event: Event) => void) | undefined;
  const undoButton = {
    dataset: { p6LayoutUndo: "" },
    closest: () => undoButton,
  };
  const redoButton = {
    dataset: { p6LayoutRedo: "" },
    closest: () => redoButton,
  };
  const restoreButton = {
    dataset: { p6LayoutRestore: "" },
    closest: () => restoreButton,
  };
  const revisionSelect = { value: "3" };
  const container: RenderContainer & {
    addEventListener: (event: string, listener: (event: Event) => void) => void;
    querySelector: (selector: string) => unknown;
  } = {
    innerHTML: "",
    querySelectorAll: () => [],
    addEventListener: (event, listener) => { if (event === "click") clickListener = listener; },
    querySelector: (selector) => selector === "[data-p6-layout-revision-select]" ? revisionSelect : null,
  };

  renderMainWorkspace(container as unknown as HTMLElement, state, {
    layoutHistory: {
      canUndo: true,
      canRedo: false,
      noticeKey: "restored",
      revisions: [
        { revision: 4, columnCount: 1 },
        { revision: 3, columnCount: 2 },
        { revision: 1, columnCount: 1 },
      ],
    },
    onP6LayoutUndo: () => events.push("undo"),
    onP6LayoutRedo: () => events.push("redo"),
    onP6LayoutRestore: (revision) => events.push(`restore:${revision}`),
  });

  assert.ok(container.innerHTML.includes("data-p6-layout-undo"));
  assert.ok(container.innerHTML.includes("data-p6-layout-redo"));
  assert.match(container.innerHTML, /Layout revision restored\./);
  assert.match(container.innerHTML, /aria-label="Layout history"/);
  assert.match(container.innerHTML, /data-p6-layout-revision-select/);
  assert.match(container.innerHTML, /<option value="3">R3 · 2 column\(s\)<\/option>/);
  assert.match(container.innerHTML, /<option value="1">R1 · 1 column\(s\)<\/option>/);
  assert.doesNotMatch(container.innerHTML, /<option value="4">/);
  const undoMarkup = container.innerHTML.match(/<button[^>]*data-p6-layout-undo[^>]*>/)?.[0] ?? "";
  const redoMarkup = container.innerHTML.match(/<button[^>]*data-p6-layout-redo[^>]*>/)?.[0] ?? "";
  const restoreMarkup = container.innerHTML.match(/<button[^>]*data-p6-layout-restore[^>]*>/)?.[0] ?? "";
  assert.ok(!undoMarkup.includes("disabled"), "undo must be enabled when canUndo is true");
  assert.ok(redoMarkup.includes("disabled"), "redo must be disabled when canRedo is false");
  assert.ok(!restoreMarkup.includes("disabled"), "restore must be enabled when older revisions exist");

  clickListener?.({ target: undoButton } as unknown as Event);
  clickListener?.({ target: redoButton } as unknown as Event);
  clickListener?.({ target: restoreButton } as unknown as Event);
  assert.deepEqual(events, ["undo", "redo", "restore:3"]);
});

test("layout restore control stays disabled without an older revision", () => {
  const state = {
    ...createWorkspaceState({ tenant_id: "tenant-1", project_id: "project-1", revision: 3 }, "en"),
    p6FieldRegistry: {
      registry_version: "p6-field-registry.v1",
      reference_product: "Oracle Primavera P6 Professional",
      reference_version: "26",
      status: "active",
      fields: [{
        field_id: "activity.activity_id",
        subject_area: "activity",
        p6_field: "Activity ID",
        display_name: "Activity ID",
        data_type: "string",
        writable: false,
        computed: false,
        disposition: "supported",
      }],
    } as const,
    p6Layout: {
      schema_version: "p6-layout.v1",
      scope: "project",
      view_id: "activity-grid",
      revision: 1,
      columns: [{
        field_id: "activity.activity_id",
        visible: true,
        order: 0,
        width: 120,
        alignment: "start",
        pinned: false,
        frozen: false,
      }],
    } as const,
  };
  const container: RenderContainer = { innerHTML: "", querySelectorAll: () => [] };
  renderMainWorkspace(container as unknown as HTMLElement, state, {
    layoutHistory: { canUndo: true, canRedo: false, revisions: [{ revision: 1, columnCount: 1 }] },
  });
  const selectMarkup = container.innerHTML.match(/<select[^>]*data-p6-layout-revision-select[^>]*>/)?.[0] ?? "";
  const restoreMarkup = container.innerHTML.match(/<button[^>]*data-p6-layout-restore[^>]*>/)?.[0] ?? "";
  assert.ok(selectMarkup.includes("disabled"));
  assert.ok(restoreMarkup.includes("disabled"));
  assert.match(container.innerHTML, /No earlier layout revision is available\./);
});

test("P6 chooser exposes hidden authoritative fields", () => {  const state = { ...createWorkspaceState({ tenant_id: "tenant-1", project_id: "project-1", revision: 3 }, "en"), p6FieldRegistry: { registry_version: "p6-field-registry.v1", reference_product: "Oracle Primavera P6 Professional", reference_version: "26", status: "active", fields: [{ field_id: "activity.activity_id", subject_area: "activity", p6_field: "Activity ID", display_name: "Activity ID", data_type: "string", writable: false, computed: false, disposition: "supported" }] } as const, p6Layout: { schema_version: "p6-layout.v1", scope: "project", view_id: "activity-grid", revision: 1, columns: [{ field_id: "activity.activity_id", visible: false, order: 0, width: 120, alignment: "start", pinned: false, frozen: false }] } as const };
  const container: RenderContainer = { innerHTML: "", querySelectorAll: () => [] };
  renderMainWorkspace(container as unknown as HTMLElement, state);
  assert.match(container.innerHTML, /data-p6-field-visibility="activity\.activity_id"/);
  assert.match(container.innerHTML, /data-p6-field-visible="true"/);
  assert.match(container.innerHTML, /aria-label="Show: Activity ID"/);
  assert.match(container.innerHTML, /aria-label="Remove: Activity ID"/);
  assert.doesNotMatch(container.innerHTML, /aria-label="Remove"/);
});


test("P6 field chooser offers Add all only while fields are available", () => {
  const registry = {
    registry_version: "p6-field-registry.v1",
    reference_product: "Oracle Primavera P6 Professional",
    reference_version: "26",
    status: "active",
    fields: [
      { field_id: "activity.activity_id", subject_area: "activity", p6_field: "Activity ID", display_name: "Activity ID", data_type: "string", writable: false, computed: false, disposition: "supported" },
      { field_id: "activity.duration", subject_area: "activity", p6_field: "Duration", display_name: "Duration", data_type: "duration", writable: false, computed: true, disposition: "supported" },
    ],
  } as const;
  const layout = {
    schema_version: "p6-layout.v1",
    scope: "project",
    view_id: "activity-grid",
    revision: 1,
    columns: [{ field_id: "activity.activity_id", visible: true, order: 0, width: 120, alignment: "start", pinned: false, frozen: false }],
  } as const;
  const partial = { ...createWorkspaceState({ tenant_id: "tenant-1", project_id: "project-1", revision: 3 }, "en"), p6FieldRegistry: registry, p6Layout: layout };
  const partialContainer: RenderContainer = { innerHTML: "", querySelectorAll: () => [] };
  renderMainWorkspace(partialContainer as unknown as HTMLElement, partial);
  assert.match(partialContainer.innerHTML, /data-p6-field-add-all/);
  assert.match(partialContainer.innerHTML, /aria-label="Add all"/);
  assert.match(partialContainer.innerHTML, /data-p6-field-add="activity\.duration"/);

  const complete = {
    ...partial,
    p6Layout: { ...layout, revision: 2, columns: [...layout.columns, { field_id: "activity.duration", visible: true, order: 1, width: 120, alignment: "start" as const, pinned: false, frozen: false }] },
  };
  const completeContainer: RenderContainer = { innerHTML: "", querySelectorAll: () => [] };
  renderMainWorkspace(completeContainer as unknown as HTMLElement, complete);
  assert.doesNotMatch(completeContainer.innerHTML, /data-p6-field-add-all/);
});

test("P6 field chooser Add all forwards only fields missing from the layout", () => {
  const registry = {
    registry_version: "p6-field-registry.v1",
    reference_product: "Oracle Primavera P6 Professional",
    reference_version: "26",
    status: "active",
    fields: [
      { field_id: "activity.activity_id", subject_area: "activity", p6_field: "Activity ID", display_name: "Activity ID", data_type: "string", writable: false, computed: false, disposition: "supported" },
      { field_id: "activity.duration", subject_area: "activity", p6_field: "Duration", display_name: "Duration", data_type: "duration", writable: false, computed: true, disposition: "supported" },
      { field_id: "activity.status", subject_area: "activity", p6_field: "Status", display_name: "Status", data_type: "string", writable: false, computed: false, disposition: "supported" },
    ],
  } as const;
  const state = {
    ...createWorkspaceState({ tenant_id: "tenant-1", project_id: "project-1", revision: 3 }, "en"),
    p6FieldRegistry: registry,
    p6Layout: {
      schema_version: "p6-layout.v1",
      scope: "project",
      view_id: "activity-grid",
      revision: 1,
      columns: [{ field_id: "activity.activity_id", visible: true, order: 0, width: 120, alignment: "start", pinned: false, frozen: false }],
    } as const,
  };
  const added: string[][] = [];
  let clickListener: ((event: Event) => void) | undefined;
  const target = { dataset: { p6FieldAddAll: "" }, closest: () => target };
  const container: RenderContainer & { addEventListener: (event: string, listener: (event: Event) => void) => void } = {
    innerHTML: "",
    querySelectorAll: () => [],
    addEventListener: (event, listener) => { if (event === "click") clickListener = listener; },
  };
  renderMainWorkspace(container as unknown as HTMLElement, state, { onP6FieldAddMany: (fieldIds) => added.push([...fieldIds]) });
  clickListener?.({ target } as unknown as Event);
  assert.deepEqual(added, [["activity.duration", "activity.status"]]);
});


test("P6 chooser rename control forwards the persisted presentation label", () => {
  const state = { ...createWorkspaceState({ tenant_id: "tenant-1", project_id: "project-1", revision: 3 }, "en"), p6FieldRegistry: { registry_version: "p6-field-registry.v1", reference_product: "Oracle Primavera P6 Professional", reference_version: "26", status: "active", fields: [{ field_id: "activity.activity_id", subject_area: "activity", p6_field: "Activity ID", display_name: "Activity ID", data_type: "string", writable: false, computed: false, disposition: "supported" }] } as const, p6Layout: { schema_version: "p6-layout.v1", scope: "project", view_id: "activity-grid", revision: 1, columns: [{ field_id: "activity.activity_id", visible: true, order: 0, width: 120, alignment: "start", pinned: false, frozen: false }] } as const };
  const changes: Array<{ fieldId: string; label: string }> = [];
  let changeListener: ((event: Event) => void) | undefined;
  const input = { value: "Activity ID", dataset: { p6FieldRename: "activity.activity_id" }, closest: () => input };
  const container: RenderContainer & { addEventListener: (event: string, listener: (event: Event) => void) => void } = {
    innerHTML: "",
    querySelectorAll: () => [],
    addEventListener: (event, listener) => { if (event === "change") changeListener = listener; },
  };
  renderMainWorkspace(container as unknown as HTMLElement, state, { onP6FieldPresentationChange: (fieldId, patch) => { if (patch.label) changes.push({ fieldId, label: patch.label }); } });
  input.value = " Activity title ";
  changeListener?.({ target: input } as unknown as Event);
  assert.deepEqual(changes, [{ fieldId: "activity.activity_id", label: "Activity title" }]);
  assert.match(container.innerHTML, /data-p6-field-rename="activity\.activity_id"/);
  assert.match(container.innerHTML, /aria-label="Rename"/);
});


test("Gantt activity selection forwards to the shared Activity selection callback", () => {
  const state = {
    ...createWorkspaceState(
      { tenant_id: "tenant-1", project_id: "project-1", revision: 3 },
      "en",
    ),
    activities: [{
      id: "A-1",
      wbsId: "W-1",
      code: "01",
      name: "Foundation",
      gantt: {
        start: "2026-09-01T00:00:00Z",
        finish: "2026-09-03T00:00:00Z",
        progressPercent: 25,
        critical: false,
      },
    }],
  };
  const selected: string[] = [];
  let clickListener: ((event: Event) => void) | undefined;
  const ganttRow = {
    dataset: { ganttActivityId: "A-1" },
    closest: () => ganttRow,
  };
  const container: RenderContainer & { addEventListener: (event: string, listener: (event: Event) => void) => void } = {
    innerHTML: "",
    querySelectorAll: () => [],
    addEventListener: (event, listener) => { if (event === "click") clickListener = listener; },
  };
  renderMainWorkspace(container as unknown as HTMLElement, state, {
    onGanttActivitySelect: (activityId) => selected.push(activityId),
  });
  clickListener?.({ target: ganttRow } as unknown as Event);
  assert.deepEqual(selected, ["A-1"]);
  assert.match(container.innerHTML, /data-gantt-activity-id="A-1"/);
  assert.match(container.innerHTML, /tabindex="0"/);
});


test("interactive Gantt board is exposed as a region instead of an image", () => {
  const state = {
    ...createWorkspaceState(
      { tenant_id: "tenant-1", project_id: "project-1", revision: 3 },
      "en",
    ),
    activities: [{
      id: "A-1", wbsId: "W-1", code: "01", name: "Foundation",
      gantt: { start: "2026-09-01T00:00:00Z", finish: "2026-09-03T00:00:00Z", progressPercent: 25, critical: false },
    }],
  };
  const container: RenderContainer = { innerHTML: "", querySelectorAll: () => [] };
  renderMainWorkspace(container as unknown as HTMLElement, state);
  assert.match(container.innerHTML, /class="cp-gantt-board" role="region" aria-label="Gantt Chart"/);
  assert.doesNotMatch(container.innerHTML, /class="cp-gantt-board" role="img"/);
});


test("details complementary landmark is named by its heading", () => {
  const state = createWorkspaceState(
    { tenant_id: "tenant-1", project_id: "project-1", revision: 3 },
    "en",
  );
  const container: RenderContainer = { innerHTML: "", querySelectorAll: () => [] };
  renderMainWorkspace(container as unknown as HTMLElement, state);
  assert.match(container.innerHTML, /class="cp-panel cp-details"[^>]*aria-labelledby="cp-details-heading"/);
  assert.match(container.innerHTML, /<h2 id="cp-details-heading">Details<\/h2>/);
});


test("interactive Gantt rows expose button selection semantics", () => {
  const state = {
    ...createWorkspaceState(
      { tenant_id: "tenant-1", project_id: "project-1", revision: 3 },
      "en",
    ),
    activities: [{
      id: "A-1", wbsId: "W-1", code: "01", name: "Foundation",
      gantt: { start: "2026-09-01T00:00:00Z", finish: "2026-09-03T00:00:00Z", progressPercent: 25, critical: false },
    }],
    selectedActivityId: "A-1",
  };
  const container: RenderContainer = { innerHTML: "", querySelectorAll: () => [] };
  renderMainWorkspace(container as unknown as HTMLElement, state);
  assert.match(container.innerHTML, /class="cp-gantt-row is-selected is-group-end" role="button" data-gantt-activity-id="A-1" tabindex="0" aria-pressed="true" aria-label="A-1 — Foundation"/);
  assert.doesNotMatch(container.innerHTML, /cp-gantt-row[^>]*aria-selected=/);
});


test("interactive Activity Grid exposes grid row selection semantics", () => {
  const state = {
    ...createWorkspaceState(
      { tenant_id: "tenant-1", project_id: "project-1", revision: 3 },
      "en",
    ),
    activities: [{
      id: "A-1", wbsId: "W-1", code: "01", name: "Foundation",
      cells: { activity_name: "Foundation" },
    }],
    selectedActivityId: "A-1",
  };
  const container: RenderContainer = { innerHTML: "", querySelectorAll: () => [] };
  renderMainWorkspace(container as unknown as HTMLElement, state);
  assert.match(container.innerHTML, /<table role="grid" aria-label="Activity Grid" aria-multiselectable="true"[^>]*>/);
  assert.match(container.innerHTML, /<thead><tr role="row">/);
  assert.match(container.innerHTML, /<th role="columnheader" scope="col"/);
  assert.match(container.innerHTML, /<tr role="row" data-activity-id="A-1" data-activity-kind="task" tabindex="0" aria-selected="true" aria-label="A-1"/);
  assert.match(container.innerHTML, /<td role="gridcell"[^>]*><span class="cp-p6-tree-guides"[^>]*><span class="cp-p6-activity-cell">.*A-1<\/span><\/span><\/td>/);
});


test("the activity grid marks every row in the shared selection", () => {
  const state = {
    ...createWorkspaceState(
      { tenant_id: "tenant-1", project_id: "project-1", revision: 3 },
      "en",
    ),
    activities: [
      { id: "A-1", wbsId: "W-1", code: "01", name: "Foundation", cells: { activity_name: "Foundation" } },
      { id: "A-2", wbsId: "W-1", code: "02", name: "Walls", cells: { activity_name: "Walls" } },
      { id: "A-3", wbsId: "W-1", code: "03", name: "Roof", cells: { activity_name: "Roof" } },
    ],
    selectedActivityId: "A-2",
    selectedActivityIds: ["A-1", "A-2"],
    selectionAnchorId: "A-1",
  };
  const container: RenderContainer = { innerHTML: "", querySelectorAll: () => [] };
  renderMainWorkspace(container as unknown as HTMLElement, state);
  const selected = [...container.innerHTML.matchAll(/data-activity-id="(A-\d)"[^>]*aria-selected="true"/g)].map((match) => match[1]);
  assert.deepEqual(selected, ["A-1", "A-2"]);
  assert.match(container.innerHTML, /data-activity-id="A-3"[^>]*aria-selected="false"/);
});

test("Gantt activity selection responds to Enter and Space keyboard activation", () => {
  const state = {
    ...createWorkspaceState(
      { tenant_id: "tenant-1", project_id: "project-1", revision: 3 },
      "en",
    ),
    activities: [{
      id: "A-1",
      wbsId: "W-1",
      code: "01",
      name: "Foundation",
      gantt: {
        start: "2026-09-01T00:00:00Z",
        finish: "2026-09-03T00:00:00Z",
        progressPercent: 25,
        critical: false,
      },
    }],
  };
  const selected: string[] = [];
  let keydownListener: ((event: Event) => void) | undefined;
  const ganttRow = {
    dataset: { ganttActivityId: "A-1" },
    closest: () => ganttRow,
  };
  const container: RenderContainer & { addEventListener: (event: string, listener: (event: Event) => void) => void } = {
    innerHTML: "",
    querySelectorAll: () => [],
    addEventListener: (event, listener) => { if (event === "keydown") keydownListener = listener; },
  };

  renderMainWorkspace(container as unknown as HTMLElement, state, {
    onGanttActivitySelect: (activityId) => selected.push(activityId),
  });

  const preventDefaultCalls: string[] = [];
  keydownListener?.({ key: "Enter", target: ganttRow, preventDefault: () => { preventDefaultCalls.push("Enter"); } } as unknown as KeyboardEvent);
  keydownListener?.({ key: " ", target: ganttRow, preventDefault: () => { preventDefaultCalls.push("Space"); } } as unknown as KeyboardEvent);

  assert.deepEqual(selected, ["A-1", "A-1"]);
  assert.deepEqual(preventDefaultCalls, ["Enter", "Space"]);
});

test("Activity Grid selection responds to Enter and Space keyboard activation", () => {
  const state = {
    ...createWorkspaceState(
      { tenant_id: "tenant-1", project_id: "project-1", revision: 3 },
      "en",
    ),
    activities: [{
      id: "A-1",
      wbsId: "W-1",
      code: "01",
      name: "Foundation",
      cells: { activity_name: "Foundation" },
    }],
  };
  const selected: string[] = [];
  let keydownListener: ((event: Event) => void) | undefined;
  const gridRow = {
    dataset: { activityId: "A-1" },
    closest: () => gridRow,
  };
  const container: RenderContainer & { addEventListener: (event: string, listener: (event: Event) => void) => void } = {
    innerHTML: "",
    querySelectorAll: () => [],
    addEventListener: (event, listener) => { if (event === "keydown") keydownListener = listener; },
  };

  renderMainWorkspace(container as unknown as HTMLElement, state, {
    onActivitySelect: (activityId) => selected.push(activityId),
  });

  const preventDefaultCalls: string[] = [];
  keydownListener?.({ key: "Enter", target: gridRow, preventDefault: () => { preventDefaultCalls.push("Enter"); } } as unknown as KeyboardEvent);
  keydownListener?.({ key: " ", target: gridRow, preventDefault: () => { preventDefaultCalls.push("Space"); } } as unknown as KeyboardEvent);

  assert.deepEqual(selected, ["A-1", "A-1"]);
  assert.deepEqual(preventDefaultCalls, ["Enter", "Space"]);
});

test("Activity Grid renders P6 alignment, pinned, and frozen presentation", () => {
  const registry = {
    registry_version: "p6-field-registry.v1" as const,
    reference_product: "Oracle Primavera P6 Professional" as const,
    reference_version: "26",
    status: "active",
    fields: [
      { field_id: "code", subject_area: "activity", p6_field: "ActivityId", display_name: "Code", data_type: "string" as const, writable: false, computed: false, disposition: "supported" },
      { field_id: "duration", subject_area: "activity", p6_field: "OriginalDuration", display_name: "Duration", data_type: "duration" as const, writable: false, computed: true, disposition: "supported" },
    ],
  };
  const layout = {
    schema_version: "p6-layout.v1" as const,
    scope: "project" as const,
    view_id: "activity-grid",
    revision: 1,
    columns: [
      { field_id: "code", visible: true, order: 0, width: 140, alignment: "center" as const, pinned: true, frozen: true },
      { field_id: "duration", visible: true, order: 1, width: 110, alignment: "end" as const, pinned: false, frozen: false },
    ],
  };
  let state = setP6Presentation(createWorkspaceState(
    { tenant_id: "tenant-1", project_id: "project-1", revision: 3 },
    "en",
  ), registry, layout);
  state = {
    ...state,
    activities: [{ id: "A-1", wbsId: "W-1", code: "01", name: "Foundation", cells: { duration: 4 } }],
  };
  const container: RenderContainer = { innerHTML: "", querySelectorAll: () => [] };
  renderMainWorkspace(container as unknown as HTMLElement, state);
  assert.match(container.innerHTML, /data-column-alignment="center"/);
  assert.match(container.innerHTML, /data-column-pinned="true"/);
  assert.match(container.innerHTML, /data-column-frozen="true"/);
  assert.match(container.innerHTML, /class="cp-p6-column is-pinned is-frozen"/);
  assert.match(container.innerHTML, /style="text-align:center;width:140px;--cp-wbs-level:#[0-9a-f]{6};--cp-p6-sticky-offset:0px"/);
});


test("Activity Grid offsets multiple pinned/frozen columns without overlap", () => {
  const registry = {
    registry_version: "p6-field-registry.v1" as const,
    reference_product: "Oracle Primavera P6 Professional" as const,
    reference_version: "26",
    status: "active",
    fields: [
      { field_id: "code", subject_area: "activity", p6_field: "ActivityId", display_name: "Code", data_type: "string" as const, writable: false, computed: false, disposition: "supported" },
      { field_id: "name", subject_area: "activity", p6_field: "ActivityName", display_name: "Name", data_type: "string" as const, writable: false, computed: false, disposition: "supported" },
      { field_id: "duration", subject_area: "activity", p6_field: "OriginalDuration", display_name: "Duration", data_type: "duration" as const, writable: false, computed: true, disposition: "supported" },
    ],
  };
  const layout = {
    schema_version: "p6-layout.v1" as const,
    scope: "project" as const,
    view_id: "activity-grid",
    revision: 1,
    columns: [
      { field_id: "code", visible: true, order: 0, width: 140, alignment: "start" as const, pinned: true, frozen: false },
      { field_id: "name", visible: true, order: 1, width: 200, alignment: "start" as const, pinned: true, frozen: false },
      { field_id: "duration", visible: true, order: 2, width: 110, alignment: "end" as const, pinned: false, frozen: true },
    ],
  };
  let state = setP6Presentation(createWorkspaceState(
    { tenant_id: "tenant-1", project_id: "project-1", revision: 3 },
    "en",
  ), registry, layout);
  state = { ...state, activities: [{ id: "A-1", wbsId: "W-1", code: "01", name: "Foundation", cells: { duration: 4 } }] };
  const container: RenderContainer = { innerHTML: "", querySelectorAll: () => [] };
  renderMainWorkspace(container as unknown as HTMLElement, state);

  assert.match(container.innerHTML, /data-column-pinned="true"[^>]*style="[^"]*--cp-p6-sticky-offset:140px/);
  assert.match(container.innerHTML, /data-column-frozen="true"[^>]*style="[^"]*--cp-p6-sticky-offset:340px/);
  assert.match(container.innerHTML, /<td role="gridcell"[^>]*data-column-pinned="true"[^>]*style="[^"]*--cp-p6-sticky-offset:140px/);
  assert.match(container.innerHTML, /<td role="gridcell"[^>]*data-column-frozen="true"[^>]*style="[^"]*--cp-p6-sticky-offset:340px/);
});

test("WBS panel renders the persisted hierarchy including nodes with no activities", () => {
  let state = createWorkspaceState(
    { tenant_id: "tenant-1", project_id: "project-1", revision: 3 },
    "en",
  );
  state = withWbsNodes(state, [
    {
      id: "W-ROOT", parentKind: "project", parentWbsId: null,
      localCode: "1", name: "Project <Root>", sequenceNumber: 0, recordRevision: 1,
    },
    {
      id: "W-FOUNDATION", parentKind: "wbs", parentWbsId: "W-ROOT",
      localCode: "2", name: "Foundation", sequenceNumber: 10, recordRevision: 1,
    },
    {
      id: "W-EMPTY", parentKind: "wbs", parentWbsId: "W-ROOT",
      localCode: "3", name: "Package with no activities", sequenceNumber: 20, recordRevision: 1,
    },
  ]);
  const container: RenderContainer = { innerHTML: "", querySelectorAll: () => [] };
  renderMainWorkspace(container as unknown as HTMLElement, state);
  assert.match(container.innerHTML, /class="cp-wbs-table" data-wbs-table role="treegrid"/);
  assert.match(container.innerHTML, /data-wbs-id="W-ROOT"/);
  assert.match(container.innerHTML, /data-wbs-id="W-FOUNDATION"/);
  assert.match(container.innerHTML, /data-wbs-id="W-EMPTY"/);
  assert.match(container.innerHTML, /aria-level="2"/);
  assert.match(container.innerHTML, /Project &lt;Root&gt;/);
  assert.ok(container.innerHTML.indexOf("Foundation") < container.innerHTML.indexOf("Package with no activities"));
  assert.doesNotMatch(container.innerHTML, /data-wbs-id="A-/);
});

test("WBS table and chart render the same persisted nodes in the same order", () => {
  const listeners = new Map<string, (event: Event) => void>();
  const hierarchy = { innerHTML: "" };
  const chartButton = {
    dataset: { wbsView: "chart" } as Record<string, string>,
    setAttribute: () => undefined,
    classList: { toggle: () => undefined },
  };
  const container = {
    innerHTML: "",
    querySelector: (selector: string) => (selector === "[data-wbs-hierarchy]" ? hierarchy : null),
    querySelectorAll: (selector: string) => (selector === "[data-wbs-view]" ? [chartButton] : []),
    addEventListener: (type: string, listener: (event: Event) => void) => listeners.set(type, listener),
  };
  let state = withWbsNodes(
    createWorkspaceState({ tenant_id: "tenant-1", project_id: "project-1", revision: 3 }, "en"),
    [
      { id: "W-B", parentKind: "wbs", parentWbsId: "W-ROOT", localCode: "B", name: "Second package", sequenceNumber: 30, recordRevision: 1 },
      { id: "W-ROOT", parentKind: "project", parentWbsId: null, localCode: "1", name: "Project root", sequenceNumber: 1, recordRevision: 1 },
      { id: "W-A1", parentKind: "wbs", parentWbsId: "W-A", localCode: "A.1", name: "Sub package", sequenceNumber: 5, recordRevision: 1 },
      { id: "W-A", parentKind: "wbs", parentWbsId: "W-ROOT", localCode: "A", name: "First package", sequenceNumber: 10, recordRevision: 1 },
    ],
  );
  state = withActivities(state, [
    { id: "ACT-1", wbsId: "W-A", code: "A100", name: "Activity one" },
    { id: "ACT-2", wbsId: "W-A", code: "A110", name: "Activity two" },
    { id: "ACT-3", wbsId: "W-ROOT", code: "A010", name: "Root activity" },
  ]);
  renderMainWorkspace(container as unknown as HTMLElement, state);
  const tableOrder = [...container.innerHTML.matchAll(/class="cp-wbs-node[^"]*" data-wbs-id="([^"]+)"/g)].map((match) => match[1]);
  assert.deepEqual(tableOrder, ["W-ROOT", "W-A", "W-A1", "W-B"]);
  assert.match(container.innerHTML, /<td class="cp-wbs-count-cell">2<\/td>/);
  const clickTarget = {
    dataset: { wbsView: "chart" },
    closest: (selector: string) => (selector.includes("[data-wbs-view]") ? chartButton : null),
  };
  listeners.get("click")?.({ target: clickTarget } as unknown as Event);
  const chartOrder = [...hierarchy.innerHTML.matchAll(/class="cp-wbs-chart-node[^"]*" data-wbs-id="([^"]+)"/g)].map((match) => match[1]);
  assert.deepEqual(chartOrder, tableOrder);
});

test("activity grid date cells follow the selected display calendar without changing stored values", () => {
  const base = createWorkspaceState(
    { tenant_id: "tenant-1", project_id: "project-1", revision: 3 },
    "en",
    "gregorian",
  );
  const dateColumn = {
    id: "start",
    label: "Start",
    dataType: "date" as const,
    editable: false,
    formula: null,
    width: 120,
    alignment: "center" as const,
    pinned: false,
    frozen: false,
  };
  const row = {
    id: "A130",
    wbsId: "civil",
    code: "A130",
    name: "Earthworks",
    cells: { start: "2026-10-07" },
  };
  const container: RenderContainer = { innerHTML: "", querySelectorAll: () => [] };

  renderMainWorkspace(
    container as unknown as HTMLElement,
    { ...base, columns: [dateColumn], activities: [row] },
  );
  assert.match(container.innerHTML, /data-column-id="start"[^>]*>(?:<span class="cp-p6-tree-guides"[^>]*>)?2026-10-07/);

  renderMainWorkspace(
    container as unknown as HTMLElement,
    { ...base, calendarMode: "jalali", columns: [dateColumn], activities: [row] },
  );
  assert.match(container.innerHTML, /data-column-id="start"[^>]*>(?:<span class="cp-p6-tree-guides"[^>]*>)?۱۴۰۵\/۰۷\/۱۵/);
  assert.doesNotMatch(container.innerHTML, />2026-10-07<\/td>/);
});

test("Activity Grid exposes a localized edit action for persisted activity rows", () => {
  const state = {
    ...createWorkspaceState(
      { tenant_id: "tenant-1", project_id: "project-1", revision: 3 },
      "en",
    ),
    activities: [{
      id: "A-101",
      wbsId: "WBS-1",
      code: "A-101",
      name: "Foundation",
      cells: { activity_name: "Foundation" },
    }],
  };
  const container: RenderContainer = {
    innerHTML: "",
    querySelectorAll: () => [],
  };
  renderMainWorkspace(container as unknown as HTMLElement, state);
  assert.match(container.innerHTML, /data-activity-edit="A-101"/);
  assert.match(container.innerHTML, /Edit activity/);
});

test("logic panel renders persisted relationships and the grid shows predecessors", () => {
  let state = createWorkspaceState({ tenant_id: "t", project_id: "p", revision: 1 }, "en");
  state = withActivities(state, [
    { id: "A-1", wbsId: "W-1", code: "01", name: "Excavate", cells: {} },
    { id: "A-2", wbsId: "W-1", code: "02", name: "Concrete", cells: {} },
  ]);
  state = withRelationships(state, [{
    id: "R-1", predecessorId: "A-1", successorId: "A-2", type: "SS",
    lagValue: "1", lagUnit: "working-day", recordRevision: 1,
  }]);
  const container = { innerHTML: "", querySelectorAll: () => [] };
  renderMainWorkspace(container as unknown as HTMLElement, state);
  assert.match(container.innerHTML, /id="cp-logic"/);
  assert.match(container.innerHTML, /data-relationship-create-form/);
  assert.match(container.innerHTML, /data-relationship-id="R-1"/);
  assert.match(container.innerHTML, /data-relationship-edit-form="R-1"/);
  assert.match(container.innerHTML, /data-relationship-revision="1"/);
  assert.match(container.innerHTML, /A-1 → A-2/);
  assert.match(container.innerHTML, /data-predecessors="A-2"[^>]*>A-1 SS\+1d</);
});

test("relationship create form dispatches the exact predecessor, successor, type and lag", () => {
  const listeners = new Map<string, (event: Event) => void>();
  const container = {
    innerHTML: "",
    querySelectorAll: () => [],
    addEventListener: (type: string, listener: (event: Event) => void) => listeners.set(type, listener),
  };
  let created: { predecessorId: string; successorId: string; type: string; lagValue: string; lagUnit: string } | null = null;
  renderMainWorkspace(
    container as unknown as HTMLElement,
    createWorkspaceState({ tenant_id: "t", project_id: "p", revision: 1 }, "en"),
    { onRelationshipCreate: (input) => { created = input; } },
  );
  const values: Record<string, { value: string }> = {
    '[name="predecessor_id"]': { value: "A-1" },
    '[name="successor_id"]': { value: "A-2" },
    '[name="relationship_type"]': { value: "SS" },
    '[name="lag_value"]': { value: " 1 " },
    '[name="lag_unit"]': { value: "working-day" },
  };
  const form = {
    matches: (selector: string) => selector === "[data-relationship-create-form]",
    querySelector: (selector: string) => values[selector] ?? null,
  };
  let prevented = false;
  listeners.get("submit")?.({ target: form, preventDefault: () => { prevented = true; } } as unknown as Event);
  assert.equal(prevented, true);
  assert.deepEqual(created, {
    predecessorId: "A-1",
    successorId: "A-2",
    type: "SS",
    lagValue: "1",
    lagUnit: "working-day",
  });
});

test("relationship edit form dispatches the stored id, revision and edited logic", () => {
  const listeners = new Map<string, (event: Event) => void>();
  const container = {
    innerHTML: "",
    querySelectorAll: () => [],
    addEventListener: (type: string, listener: (event: Event) => void) => listeners.set(type, listener),
  };
  let updated: {
    relationshipId: string;
    recordRevision: number;
    input: { predecessorId: string; successorId: string; type: string; lagValue: string; lagUnit: string };
  } | null = null;
  renderMainWorkspace(
    container as unknown as HTMLElement,
    createWorkspaceState({ tenant_id: "t", project_id: "p", revision: 1 }, "en"),
    {
      onRelationshipUpdate: (relationshipId, recordRevision, input) => {
        updated = { relationshipId, recordRevision, input };
      },
    },
  );
  const values: Record<string, { value: string }> = {
    '[name="predecessor_id"]': { value: "A-1" },
    '[name="successor_id"]': { value: "A-2" },
    '[name="relationship_type"]': { value: "FF" },
    '[name="lag_value"]': { value: " 2.5 " },
    '[name="lag_unit"]': { value: "working-hour" },
  };
  const form = {
    dataset: { relationshipEditForm: "R-1", relationshipRevision: "3" },
    matches: (selector: string) => selector === "[data-relationship-edit-form]",
    querySelector: (selector: string) => values[selector] ?? null,
  };
  let prevented = false;
  listeners.get("submit")?.({ target: form, preventDefault: () => { prevented = true; } } as unknown as Event);
  assert.equal(prevented, true);
  assert.deepEqual(updated, {
    relationshipId: "R-1",
    recordRevision: 3,
    input: {
      predecessorId: "A-1",
      successorId: "A-2",
      type: "FF",
      lagValue: "2.5",
      lagUnit: "working-hour",
    },
  });
});

function scheduledGanttState(locale: "en" | "fa" = "en", calendarMode: "gregorian" | "jalali" = "gregorian") {
  let state = createWorkspaceState({ tenant_id: "t", project_id: "p", revision: 1 }, locale, calendarMode);
  state = withActivities(state, [
    {
      id: "A-1", wbsId: "W-1", code: "01", name: "Excavate",
      gantt: { start: "2026-09-01T00:00:00Z", finish: "2026-09-03T00:00:00Z", progressPercent: 0, critical: true },
    },
    {
      id: "A-2", wbsId: "W-1", code: "02", name: "Concrete",
      gantt: { start: "2026-09-03T00:00:00Z", finish: "2026-09-05T00:00:00Z", progressPercent: 0, critical: true },
    },
    {
      id: "M-1", wbsId: "W-1", code: "M1", name: "Inspection milestone",
      gantt: { start: "2026-09-05T00:00:00Z", finish: "2026-09-05T00:00:00Z", progressPercent: 0, critical: true },
    },
  ]);
  return withRelationships(state, [
    { id: "R-FS", predecessorId: "A-1", successorId: "A-2", type: "FS", lagValue: "0", lagUnit: "working-day", recordRevision: 1 },
    { id: "R-SS", predecessorId: "A-1", successorId: "A-2", type: "SS", lagValue: "1", lagUnit: "working-day", recordRevision: 1 },
  ]);
}

test("Gantt renders persisted dependency arrows, a dated axis and milestone markers", () => {
  const container: RenderContainer = { innerHTML: "", querySelectorAll: () => [] };
  renderMainWorkspace(container as unknown as HTMLElement, scheduledGanttState());
  assert.match(container.innerHTML, /data-gantt-link="R-FS"/);
  assert.match(container.innerHTML, /data-link-type="FS"[^>]*data-link-from="A-1"[^>]*data-link-to="A-2"/);
  assert.match(container.innerHTML, /data-gantt-link="R-SS"/);
  assert.match(container.innerHTML, /data-link-type="SS"/);
  assert.match(container.innerHTML, /class="cp-gantt-link is-critical"[^>]*data-gantt-link="R-FS"/);
  assert.match(container.innerHTML, /marker-end="url\(#cp-gantt-arrow-critical\)"/);
  assert.match(container.innerHTML, /data-gantt-tick="2026-09-01"/);
  // The default month timescale prints the month over its period, like the
  // desktop reference, while the tick keeps the canonical ISO date.
  assert.match(container.innerHTML, /data-gantt-tick="2026-09-01"[^>]*>Sep</);
  assert.match(container.innerHTML, /data-gantt-grid="2026-09-01"/);
  assert.match(container.innerHTML, /data-gantt-scale-mode="month"/);
  assert.match(container.innerHTML, /data-gantt-scale="month" aria-pressed="true"/);
  assert.match(container.innerHTML, /data-gantt-scale="day" aria-pressed="false"/);
  assert.match(container.innerHTML, /data-gantt-bar-kind="critical" data-gantt-bar-row="1"/);
  assert.match(container.innerHTML, /data-gantt-bar-kind="milestone" data-gantt-bar-row="1" data-gantt-bar-shape="triangle-down"/);
  assert.equal((container.innerHTML.match(/class="cp-gantt-row/g) ?? []).length, 3);
  // Layout commands live once, in the application toolbar; the chart board
  // keeps only chart-local scale presets and the relationship toggle.
  assert.doesNotMatch(container.innerHTML, /data-gantt-command/);
  assert.match(container.innerHTML, /data-gantt-scale="day"/);
  assert.match(container.innerHTML, /data-gantt-relationships-toggle/);
});

test("Gantt axis shows the Jalali display date while keeping canonical tick dates", () => {
  const container: RenderContainer = { innerHTML: "", querySelectorAll: () => [] };
  renderMainWorkspace(container as unknown as HTMLElement, scheduledGanttState("fa", "jalali"));
  // The canonical ISO date stays on the tick, while the visible month label and
  // the tooltip use the Jalali display date.
  assert.match(container.innerHTML, /data-gantt-tick="2026-09-01"[^>]*title="۱۴۰۵\/۰۶\/۱۰"[^>]*>شهریور</);
});

test("Gantt scale buttons dispatch day/week/month/quarter/year and reject unknown modes", () => {
  const listeners = new Map<string, (event: Event) => void>();
  const container = {
    innerHTML: "",
    querySelectorAll: () => [],
    addEventListener: (type: string, listener: (event: Event) => void) => listeners.set(type, listener),
  };
  const chosen: string[] = [];
  renderMainWorkspace(
    container as unknown as HTMLElement,
    scheduledGanttState(),
    { onGanttScaleChange: (mode) => chosen.push(mode) },
  );
  for (const mode of ["week", "month", "quarter", "year", "financial-period"]) {
    const button = { dataset: { ganttScale: mode }, closest: () => button };
    listeners.get("click")?.({ target: button } as unknown as Event);
  }
  assert.deepEqual(chosen, ["week", "month", "quarter", "year"]);
});

test("Gantt dependency line visibility is an accessible selectable presentation control", () => {
  const listeners = new Map<string, (event: Event) => void>();
  const container = {
    innerHTML: "",
    querySelectorAll: () => [],
    addEventListener: (type: string, listener: (event: Event) => void) => listeners.set(type, listener),
  };
  const chosen: boolean[] = [];
  const state = scheduledGanttState();
  renderMainWorkspace(container as unknown as HTMLElement, state, {
    onGanttRelationshipsChange: (visible) => chosen.push(visible),
  });
  assert.match(container.innerHTML, /data-gantt-relationships-toggle="false" aria-pressed="true"/);
  const hideButton = { dataset: { ganttRelationshipsToggle: "false" }, closest: () => hideButton };
  listeners.get("click")?.({ target: hideButton } as unknown as Event);
  const showButton = { dataset: { ganttRelationshipsToggle: "true" }, closest: () => showButton };
  listeners.get("click")?.({ target: showButton } as unknown as Event);
  assert.deepEqual(chosen, [false, true]);

  const hiddenContainer = { innerHTML: "", querySelectorAll: () => [] };
  renderMainWorkspace(hiddenContainer as unknown as HTMLElement, {
    ...state,
    showGanttRelationships: false,
  });
  assert.match(hiddenContainer.innerHTML, /data-gantt-relationships-toggle="true" aria-pressed="false"/);
  assert.doesNotMatch(hiddenContainer.innerHTML, /class="cp-gantt-links"/);
});

test("the saved table presentation styles the real grid, rows, icons and line numbers", () => {
  const container: RenderContainer = { innerHTML: "", querySelectorAll: () => [] };
  const presentation = normalizePresentation({
    table: {
      fontFamily: "cairo",
      fontSize: 14,
      textColor: "#102030",
      backgroundColor: "#eef4f9",
      rowHeight: 30,
      rowHeightMode: "content",
      showIcons: true,
      lineNumbers: true,
    },
  });
  renderMainWorkspace(container as unknown as HTMLElement, scheduledGanttState(), { presentation });
  assert.match(container.innerHTML, /data-table-row-mode="content"/);
  assert.match(container.innerHTML, /data-show-icons="true"/);
  assert.match(container.innerHTML, /data-line-numbers="true"/);
  assert.match(container.innerHTML, /--cp-p6-row-height:30px/);
  assert.match(container.innerHTML, /--cp-p6-font-size:14px/);
  assert.match(container.innerHTML, /--cp-p6-text-color:#102030/);
  assert.match(container.innerHTML, /--cp-p6-bg-color:#eef4f9/);
  assert.match(container.innerHTML, /class="cp-p6-line-number">#</);
  assert.match(container.innerHTML, /class="cp-p6-line-number">1</);
  assert.match(container.innerHTML, /class="cp-p6-activity-icon is-task"/);
  assert.match(container.innerHTML, /class="cp-gantt-row[^"]*" role="button" data-gantt-activity-id="A-1"/);
});

test("bar styles change the real bar layers while the schedule facts stay untouched", () => {
  const container: RenderContainer = { innerHTML: "", querySelectorAll: () => [] };
  const presentation = normalizePresentation({
    bars: {
      task: { bodyColor: "#123456", borderColor: "#0a0b0c", height: 8, pattern: "hatched", labelField: "activity-name", labelPosition: "right" },
      critical: { visible: false },
      milestone: { visible: false },
      progress: { visible: false },
    },
  });
  const state = scheduledGanttState();
  renderMainWorkspace(container as unknown as HTMLElement, state, { presentation });
  assert.match(container.innerHTML, /data-gantt-bar-kind="task"[^>]*data-gantt-bar-shape="bar"[^>]*data-gantt-bar-pattern="hatched"/);
  assert.match(container.innerHTML, /--cp-bar-body:#123456/);
  assert.match(container.innerHTML, /class="cp-gantt-bar-label is-right"[^>]*>Excavate</);
  assert.doesNotMatch(container.innerHTML, /data-gantt-bar-kind="milestone"/);
  // The three activity rows and their persisted dependency links are unchanged.
  assert.equal((container.innerHTML.match(/class="cp-gantt-row/g) ?? []).length, 3);
  assert.match(container.innerHTML, /data-gantt-link="R-FS"/);
});

test("bar labels mirror to the left of bars that reach the plotted right edge", () => {
  const container: RenderContainer = { innerHTML: "", querySelectorAll: () => [] };
  const presentation = normalizePresentation({
    bars: {
      task: { labelField: "activity-name", labelPosition: "right" },
      critical: { visible: false },
      milestone: { visible: false },
      progress: { visible: false },
    },
  });
  renderMainWorkspace(container as unknown as HTMLElement, scheduledGanttState(), { presentation });
  // A-1 finishes at the mid-timeline (Sep 3) and keeps its configured right
  // label; A-2 runs to the plotted finish (Sep 5) and is mirrored left so the
  // scrollable chart never clips it.
  assert.match(container.innerHTML, /class="cp-gantt-bar-label is-right" data-gantt-label-position="right">Excavate</);
  assert.match(container.innerHTML, /class="cp-gantt-bar-label is-left" data-gantt-label-position="left">Concrete</);
});

test("Gantt shades non-working periods from the persisted project calendar", () => {
  const container: RenderContainer = { innerHTML: "", querySelectorAll: () => [] };
  const base = scheduledGanttState();
  const state = {
    ...base,
    // The helper's timeline ends on Saturday 5 Sep, so move the milestone to
    // Tuesday 8 Sep to expose the full weekend inside the plotted range.
    activities: base.activities.map((activity) => activity.id === "M-1"
      ? { ...activity, gantt: { ...activity.gantt!, start: "2026-09-08T00:00:00Z", finish: "2026-09-08T00:00:00Z" } }
      : activity),
    projectCalendar: {
      status: "loaded" as const,
      calendarId: "CAL-1",
      calendarVersion: "1",
      workingWeekdays: [0, 1, 2, 3, 4],
      holidays: ["2026-09-03"],
      errorCode: null,
    },
  };
  renderMainWorkspace(container as unknown as HTMLElement, state);
  assert.match(container.innerHTML, /class="cp-gantt-nonworking"/);
  assert.match(container.innerHTML, /data-gantt-nonworking="holiday" data-nonworking-from="2026-09-03" data-nonworking-to="2026-09-03"/);
  assert.match(container.innerHTML, /data-gantt-nonworking="weekend" data-nonworking-from="2026-09-05" data-nonworking-to="2026-09-06"/);
});

test("Gantt does not shade any day without loaded calendar facts", () => {
  const container: RenderContainer = { innerHTML: "", querySelectorAll: () => [] };
  renderMainWorkspace(container as unknown as HTMLElement, scheduledGanttState());
  assert.doesNotMatch(container.innerHTML, /data-gantt-nonworking=/);
});

test("Gantt chart options drive labels, legend, sight lines and the progress line", () => {
  const container: RenderContainer = { innerHTML: "", querySelectorAll: () => [] };
  const state = {
    ...withWbsNodes(scheduledGanttState(), [
      { id: "W-1", parentKind: "project" as const, parentWbsId: null, localCode: "1", name: "Civil", sequenceNumber: 1, recordRevision: 1 },
    ]),
    // Day zoom exposes more than one tick, so the minor vertical sight lines exist.
    ganttScale: "day" as const,
  };
  const presentation = normalizePresentation({
    bars: { milestone: { visible: false }, progress: { visible: false } },
    gantt: {
      showBarLabels: false,
      labelFontSize: 13,
      labelColor: "#223344",
      sightLines: { beforeSummaries: true, rowInterval: 2, minorVertical: true },
      legend: { visible: true, position: "top" },
      progressLine: { visible: true, color: "#ff8800", thickness: 3 },
    },
  });
  renderMainWorkspace(container as unknown as HTMLElement, state, { presentation });
  assert.match(container.innerHTML, /data-bar-labels="false"/);
  assert.match(container.innerHTML, /--cp-bar-label-size:13px/);
  assert.match(container.innerHTML, /--cp-bar-label-color:#223344/);
  assert.match(container.innerHTML, /data-gantt-legend="top"/);
  assert.match(container.innerHTML, /cp-gantt-legend-item" data-gantt-legend-kind="task"/);
  assert.match(container.innerHTML, /class="cp-gantt-sight-line is-horizontal is-major"/);
  assert.match(container.innerHTML, /class="cp-gantt-sight-line is-horizontal is-minor"/);
  assert.match(container.innerHTML, /data-gantt-grid-minor=/);
  assert.match(container.innerHTML, /data-gantt-progress-line="\d+"/);
  assert.match(container.innerHTML, /--cp-progress-color:#ff8800/);
  // The read model exposes no Data Date, so no fabricated line is drawn.
  assert.doesNotMatch(container.innerHTML, /data-gantt-data-date=/);
});

test("an authoritative Data Date draws the line with the saved style", () => {
  const container: RenderContainer = { innerHTML: "", querySelectorAll: () => [] };
  const presentation = normalizePresentation({
    gantt: { dataDateLine: { visible: true, style: "dashed", thickness: 2, color: "#00aa55" } },
  });
  renderMainWorkspace(container as unknown as HTMLElement, scheduledGanttState(), { presentation, dataDate: "2026-09-03" });
  assert.match(container.innerHTML, /data-gantt-data-date="2026-09-03"/);
  assert.match(container.innerHTML, /cp-gantt-data-date is-dashed/);
  assert.match(container.innerHTML, /--cp-data-date-color:#00aa55/);
});

test("progress points are classified against the authoritative Data Date", () => {
  const container: RenderContainer = { innerHTML: "", querySelectorAll: () => [] };
  const presentation = normalizePresentation({ gantt: { progressLine: { visible: true } } });
  renderMainWorkspace(container as unknown as HTMLElement, scheduledGanttState(), { presentation, dataDate: "2026-09-03" });
  // A-1 starts before the date, A-2 starts on it, the milestone sits after it.
  assert.match(container.innerHTML, /data-gantt-progress-data-date="2026-09-03"/);
  assert.match(container.innerHTML, /data-gantt-progress-behind="1"/);
  assert.match(container.innerHTML, /data-gantt-progress-on="1"/);
  assert.match(container.innerHTML, /data-gantt-progress-ahead="1"/);
});

test("summary bars consume the configured summary style", () => {
  const container: RenderContainer = { innerHTML: "", querySelectorAll: () => [] };
  const presentation = normalizePresentation({
    bars: {
      summary: {
        bodyColor: "#0b5fa5",
        borderColor: "#063b69",
        height: 16,
        pattern: "hatched",
        startShape: "diamond",
        finishShape: "diamond",
        labelField: "activity-name",
        labelPosition: "right",
      },
    },
  });
  const state = withWbsNodes(scheduledGanttState(), [
    { id: "W-1", parentKind: "project", parentWbsId: null, localCode: "1", name: "Civil works", sequenceNumber: 1, recordRevision: 1 },
  ]);
  renderMainWorkspace(container as unknown as HTMLElement, state, { presentation });
  assert.match(container.innerHTML, /class="cp-gantt-summary-bar is-body-bar is-pattern-hatched"/);
  assert.match(container.innerHTML, /data-gantt-bar-pattern="hatched"/);
  assert.match(container.innerHTML, /height:16px/);
  assert.match(container.innerHTML, /--cp-bar-body:#0b5fa5/);
  assert.match(container.innerHTML, /cp-gantt-endpoint is-start is-diamond/);
  assert.match(container.innerHTML, /cp-gantt-endpoint is-finish is-diamond/);
  // The summary spans the whole plotted range, so it has no room for an
  // outside label and keeps it inside the finish edge.
  assert.match(container.innerHTML, /class="cp-gantt-bar-label is-inside-right" data-gantt-label-position="inside-right">Civil works</);
});

test("actual and baseline bars are drawn only from persisted date facts", () => {
  const planned: RenderContainer = { innerHTML: "", querySelectorAll: () => [] };
  renderMainWorkspace(planned as unknown as HTMLElement, scheduledGanttState());
  assert.doesNotMatch(planned.innerHTML, /data-gantt-bar-kind="actual"/);
  assert.doesNotMatch(planned.innerHTML, /data-gantt-bar-kind="baseline"/);

  let state = createWorkspaceState({ tenant_id: "t", project_id: "p", revision: 1 });
  state = withActivities(state, [{
    id: "A-1", wbsId: "W-1", code: "01", name: "Excavate",
    gantt: { start: "2026-09-02T00:00:00Z", finish: "2026-09-04T00:00:00Z", progressPercent: 50, critical: false },
    cells: {
      "activity.actual_start": "2026-09-02T00:00:00Z",
      "activity.actual_finish": "2026-09-03T00:00:00Z",
      "activity.baseline_start": "2026-09-01T00:00:00Z",
      "activity.baseline_finish": "2026-09-04T00:00:00Z",
    },
  }]);
  const progressed: RenderContainer = { innerHTML: "", querySelectorAll: () => [] };
  renderMainWorkspace(progressed as unknown as HTMLElement, state);
  assert.match(progressed.innerHTML, /data-gantt-bar-kind="actual" data-gantt-bar-row="2"/);
  assert.match(progressed.innerHTML, /data-gantt-bar-kind="baseline" data-gantt-bar-row="3"/);
  assert.match(progressed.innerHTML, /class="cp-gantt-progress"/);
});

test("Gantt board keeps chart-local controls and does not duplicate layout commands", () => {
  const listeners = new Map<string, (event: Event) => void>();
  const container = {
    innerHTML: "",
    querySelectorAll: () => [],
    addEventListener: (type: string, listener: (event: Event) => void) => listeners.set(type, listener),
  };
  const commands: string[] = [];
  const scales: string[] = [];
  const relationships: boolean[] = [];
  renderMainWorkspace(container as unknown as HTMLElement, scheduledGanttState(), {
    onGanttCommand: (command) => commands.push(command),
    onGanttScaleChange: (mode) => scales.push(mode),
    onGanttRelationshipsChange: (visible) => relationships.push(visible),
  });
  for (const [key, value] of [["ganttCommand", "bars"], ["ganttScale", "week"], ["ganttRelationshipsToggle", "false"]] as const) {
    const button = { dataset: { [key]: value }, closest: () => button };
    listeners.get("click")?.({ target: button } as unknown as Event);
  }
  // Bars/font/preferences are owned once by the application toolbar; the
  // chart board only answers for scale presets and link visibility.
  assert.deepEqual(commands, []);
  assert.deepEqual(scales, ["week"]);
  assert.deepEqual(relationships, [false]);
});

test("project settings button dispatches a single open request", () => {
  const listeners = new Map<string, (event: Event) => void>();
  const container = {
    innerHTML: "",
    querySelectorAll: () => [],
    addEventListener: (type: string, listener: (event: Event) => void) => listeners.set(type, listener),
  };
  let opened = 0;
  renderMainWorkspace(
    container as unknown as HTMLElement,
    scheduledGanttState(),
    { onProjectSettings: () => { opened += 1; } },
  );
  assert.match(container.innerHTML, /data-project-settings/);
  const button = { dataset: { projectSettings: "true" }, closest: () => button };
  listeners.get("click")?.({ target: button } as unknown as Event);
  assert.equal(opened, 1);
});

test("WBS keeps its register window", () => {
  const html = render("en", "wbs");
  assert.ok(html.includes("Work Breakdown Structure"));
  assert.match(html, /No records are loaded for this project|WBS hierarchy/);
});

test("Risks is a first-class window mounted on the real risk register", () => {
  const html = render("en", "risks");
  assert.match(html, /data-risks-page/);
  assert.match(html, /Project Risks/);
  assert.doesNotMatch(html, /No records are loaded for this project/);
});

test("Thresholds is a first-class window mounted on the real monitoring register", () => {
  const html = render("en", "thresholds");
  assert.match(html, /data-thresholds-page/);
  assert.match(html, /Project Thresholds/);
  assert.doesNotMatch(html, /No records are loaded for this project/);
});

test("Issues is a first-class window mounted on the real issue register", () => {
  const html = render("en", "issues");
  assert.match(html, /data-issues-page/);
  assert.match(html, /Project Issues/);
  assert.doesNotMatch(html, /No records are loaded for this project/);
  // The window owns its details tabs; the shared bottom pane must not add a
  // second, generic surface underneath it.
  assert.match(html, /data-details-collapsed="true"/);
  assert.match(html, /<aside id="cp-details"[^>]*hidden/);
});

test("Expenses is a first-class window mounted on the real expense and cost-account registers", () => {
  const html = render("en", "expenses");
  assert.match(html, /data-expenses-page/);
  assert.match(html, /Project Expenses/);
  assert.doesNotMatch(html, /data-register-tab="expenses:costs"/);
});

test("Progress is a first-class window mounted on the shared activity progress service", () => {
  const html = render("en", "progress");
  assert.match(html, /data-progress-page/);
  assert.match(html, /Activity Progress/);
  assert.doesNotMatch(html, /Progress presentation reads the field records/);
});

test("Cost is a first-class window mounted on the shared cost and earned-value reads", () => {
  const html = render("en", "cost");
  assert.match(html, /data-cost-page/);
  assert.match(html, /Cost Overview/);
  assert.doesNotMatch(html, /procurement, change and claim records already loaded/i);
});

test("Resource Assignments is a first-class window mounted on the real assignment register", () => {
  const html = render("en", "assignments");
  assert.match(html, /data-assignments-page/);
  assert.doesNotMatch(html, /data-register-tab="assignments:costs"/);
});

test("Roles is a first-class window mounted on the real role register", () => {
  const roles = render("en", "roles");
  assert.match(roles, /data-roles-page/);
  assert.doesNotMatch(roles, /data-register-tab="roles:rates"/);
  assert.doesNotMatch(roles, /Role management is a visual shell only/);
  const tracking = render("en", "tracking");
  assert.match(tracking, /data-tracking-page/);
  assert.match(tracking, /aria-label="Project Tracking"/);
  assert.doesNotMatch(tracking, /data-tracking-layout/);
  assert.doesNotMatch(tracking, /not connected yet/);
});

test("Calendar Register opens as a first-class window with documented editor controls", () => {
  const html = render("en", "calendars");
  assert.match(html, /data-active-menu="calendars"/);
  assert.match(html, /Calendar Register/);
  assert.match(html, /Calendar Scope/);
  assert.match(html, /Workweek/);
  assert.match(html, /Exceptions and Holidays/);
  assert.match(html, /Assignments/);
  assert.match(html, /split shifts, multiple work intervals, overnight shifts/);
  assert.match(html, /Editing and saving are disabled until the authoritative calendar service/i);
});

test("Project and WBS Details use their Version 26 tab inventories and switch by window context", () => {
  const project = render("en", "project");
  for (const tab of ["general", "dates", "notebook", "budget-log", "spending-plan", "budget-summary", "funding", "codes", "defaults", "resources", "settings", "calculations", "planning-resources", "contract-management", "udfs"]) {
    assert.ok(project.includes(`data-project-detail-tab="${tab}"`), `missing Project Details tab: ${tab}`);
  }
  const reports = render("en", "reports");
  assert.doesNotMatch(reports, /data-activity-detail-tab=/);
  assert.doesNotMatch(reports, /data-project-detail-tab=/);
  assert.match(reports, /Select a record in this window to display its details/);

  const base = withWbsNodes(
    createWorkspaceState({ tenant_id: "tenant-1", project_id: "project-1", revision: 3 }, "en"),
    [{ id: "WBS-1", parentKind: "project", parentWbsId: null, localCode: "1.1", name: "Structure", sequenceNumber: 1, recordRevision: 2 }],
  );
  const wbsState = { ...base, selectedWbsId: "WBS-1" };
  const container = { innerHTML: "", querySelectorAll: () => [], addEventListener: () => {} };
  renderMainWorkspace(container as unknown as HTMLElement, wbsState);
  for (const tab of ["general", "notebook", "budget-log", "spending-plan", "budget-summary", "milestones", "documents", "earned-value", "planning-resources", "udfs"]) {
    assert.ok(container.innerHTML.includes(`data-wbs-detail-tab="${tab}"`), `missing WBS Details tab: ${tab}`);
  }
  assert.match(container.innerHTML, /WBS Details/);
  assert.match(container.innerHTML, /Structure/);
});

test("empty and preview-only modules show an explicit truthful surface", () => {
  const reports = render("en", "reports");
  assert.match(reports, /data-workspace-menu="reports"/);
  assert.match(reports, /data-reports-page/);

  const progress = render("fa", "progress");
  assert.match(progress, /data-workspace-menu="progress"/);
  assert.match(progress, /data-progress-page/);
  assert.match(progress, /پیشرفت هر فعالیت از سرویس مشترک فعالیت/);

  const documents = render("en", "documents");
  assert.match(documents, /data-documents-page/);

  const settings = render("en", "settings");
  assert.match(settings, /id="cp-settings-panel"[^>]*data-workspace-menu="settings"/);
});


test("desktop workbench renders one compact navigation rail, a full menu flyout and no artificial command strip", () => {
  const html = render("en", "schedule");
  assert.match(html, /class="[^"]*cp-navigation-tree/);
  const navigationStart = html.indexOf('data-tool-rail="left"');
  const navigationEnd = html.indexOf("</nav>", navigationStart);
  const navigationMarkup = html.slice(navigationStart, navigationEnd + 6);
  // The left rail is a registry-driven tool rail with its own families, not a
  // second copy of the 21-destination navigation tree.
  assert.equal((navigationMarkup.match(/data-tool-family="/g) ?? []).length, 6);
  assert.match(navigationMarkup, /data-tool-family="navigation"/);
  assert.match(navigationMarkup, /data-tool-add-remove/);
  assert.match(navigationMarkup, /data-nav-flyout-toggle/);
  const flyoutStart = html.indexOf('<div class="cp-p6-flyout" data-nav-flyout hidden>');
  assert.ok(flyoutStart > -1, "the full navigation flyout must be rendered");
  const flyoutEnd = html.indexOf('<div class="cp-p6-drawer', flyoutStart);
  const flyoutMarkup = html.slice(flyoutStart, flyoutEnd);
  assert.equal((flyoutMarkup.match(/data-menu=/g) ?? []).length, 21);
  assert.match(flyoutMarkup, /class="cp-p6-flyout-tree"/);
  assert.match(html, /Project workspace/);
  assert.match(html, /Planning &amp; execution/);
  assert.match(html, /Resources &amp; cost/);
  assert.doesNotMatch(html, /cp-context-command-bar/);
  assert.doesNotMatch(html, /cp-p6-activity-header/);
  assert.doesNotMatch(html, /Current window commands/);
  assert.match(html, /data-activity-create-open/);
  assert.match(html, /data-columns-open/);
  assert.match(html, /class="cp-p6-grid-actions"/);
  assert.doesNotMatch(html, /class="cp-window-tabs"/);
  assert.match(html, /class="cp-context-add-menu"/);
  assert.doesNotMatch(html, /class="cp-window-tab\b/);
  assert.match(html, /Calendars/);
  assert.match(html, /Roles/);
  assert.match(html, /Tracking/);
  assert.match(html, /Thresholds/);
});

test("the right rail leads with one Add command menu and never repeats left navigation", () => {
  const html = render("en", "schedule");
  const railStart = html.indexOf('<aside class="cp-comments-dock-rail cp-context-command-rail cp-tool-rail"');
  assert.ok(railStart > -1, "the context command rail must be rendered");
  const railEnd = html.indexOf("</aside>", railStart);
  const rail = html.slice(railStart, railEnd);

  // The Add menu is the fixed first control in the rail in both directions.
  assert.match(rail, /^<aside[^>]*>\s*<details class="cp-context-add-menu"/);
  assert.match(rail, /<summary role="button" aria-haspopup="menu" aria-expanded="false"[^>]*>\+<\/summary>/);
  assert.match(rail, /data-context-add-popup role="menu"/);
  // Contextual create commands dispatch through stable desktop command ids.
  assert.match(rail, /data-desktop-command="project.add-activity"/);
  assert.match(rail, /data-desktop-command="edit.link"/);
  // The rail adds record-level commands; the left rail keeps destinations only.
  assert.doesNotMatch(rail, /data-menu=/);
  assert.match(rail, /data-rail-action="assistant"/);
  assert.match(rail, /data-rail-action="details"/);
  assert.match(rail, /data-rail-action="notebook"/);
  assert.match(rail, /data-rail-action="comments"/);
  // All eighteen Version 26 families are registered on the right rail.
  assert.equal((rail.match(/data-tool-family="/g) ?? []).length, 18);
  assert.match(rail, /data-tool-family="project-tools"/);
  assert.match(rail, /data-tool-family="schedule"/);
  // No write capability means every command stays visible but disabled with a
  // reason the user can read; nothing pretends the action succeeded.
  assert.match(rail, /data-desktop-command="project.add-activity" disabled aria-disabled="true"/);
  assert.match(rail, /Requires the project planner or administrator role\./);
});

test("contextual Add commands follow the active window, selection and stored data", () => {
  const state = createWorkspaceState({ tenant_id: "tenant-1", project_id: "project-1", revision: 3 }, "en");
  const renderWith = (menu: WorkspaceMenuKey, options: Parameters<typeof renderMainWorkspace>[2]): string => {
    const container = { innerHTML: "", querySelectorAll: () => [] };
    renderMainWorkspace(container as unknown as HTMLElement, { ...state, activeMenu: menu }, options);
    return container.innerHTML;
  };

  const schedule = renderWith("schedule", { canWrite: true });
  assert.match(schedule, /data-desktop-command="project.add-activity"/);
  assert.match(schedule, /data-desktop-command="edit.link"/);
  // Without a selected activity the relationship command explains why it is off.
  assert.match(schedule, /data-desktop-command="edit.link" disabled aria-disabled="true"[^>]*>/);
  assert.match(schedule, /Select an activity in the register first\./);

  const wbs = renderWith("wbs", { canWrite: true });
  assert.match(wbs, /data-desktop-command="project.add-wbs"/);
  assert.match(wbs, /data-desktop-command="project.add-activity" disabled aria-disabled="true"/);
  assert.match(wbs, /Add a WBS element before creating activities\./);

  const resources = renderWith("resources", { canWrite: true });
  assert.match(resources, /data-desktop-command="resource.create"/);

  const calendars = renderWith("calendars", { canWrite: true });
  assert.match(calendars, /data-desktop-command="calendar.create" disabled aria-disabled="true"/);
  assert.match(calendars, /A base calendar must exist before a calendar can be created\./);

  const reports = renderWith("reports", { canWrite: true });
  assert.match(reports, /This window has no create action\./);
  const reportsAdd = reports.match(/<div class="cp-context-add-popup"[\s\S]*?<\/div>/);
  assert.ok(reportsAdd, "the contextual Add popup must be rendered");
  assert.doesNotMatch(reportsAdd[0], /data-desktop-command=/);

  // A viewer sees the same commands disabled instead of write controls vanishing
  // behind an ambiguous empty rail.
  const viewer = renderWith("documents", { canWrite: false });
  assert.match(viewer, /data-desktop-command="document.create" disabled aria-disabled="true"/);
});

test("desktop workbench exposes real keyboard-operable resize separators and reset commands instead of disabled placeholders", () => {
  const html = render("en", "schedule");
  assert.match(html, /data-panel-splitter role="separator" aria-orientation="vertical" tabindex="0"[^>]*aria-valuemin="25"[^>]*aria-valuemax="75"[^>]*aria-valuenow="50"/);
  assert.match(html, /data-details-splitter[^>]*role="separator" aria-orientation="horizontal" tabindex="0"[^>]*aria-valuemin="40"[^>]*aria-valuemax="80"[^>]*aria-valuenow="70"/);
  assert.match(html, /data-column-resize="[^"]+" role="separator" aria-orientation="vertical"[^>]*aria-valuemin="48"[^>]*aria-valuemax="640"[^>]*aria-valuenow="\d+"/);
  assert.match(html, /data-layout-options-open/);
  assert.match(html, /data-reset-table-split/);
  assert.match(html, /data-reset-details-split/);
  assert.match(html, /data-reset-column-widths/);
  assert.doesNotMatch(html, /role="menuitem" disabled/);
  assert.doesNotMatch(html, /create workflow is not connected yet/);
});

test("Settings layout administration states honestly when no layout is loaded", () => {
  const html = render("en", "settings");
  assert.match(html, /data-settings-layout/);
  assert.match(html, /Layout Administration/);
  assert.match(html, /No saved activity-grid layout is loaded for this project revision/);
  assert.match(html, /id="cp-project-settings-open"/);
  assert.doesNotMatch(html, /data-p6-layout-undo/);
  assert.doesNotMatch(html, /data-p6-field-add/);
});

test("Settings layout administration reads the persisted layout and dispatches history actions", () => {
  const state = {
    ...createWorkspaceState({ tenant_id: "tenant-1", project_id: "project-1", revision: 3 }, "en"),
    activeMenu: "settings" as const,
    p6FieldRegistry: {
      registry_version: "p6-field-registry.v1",
      reference_product: "Oracle Primavera P6 Professional",
      reference_version: "26",
      status: "active",
      fields: [
        {
          field_id: "activity.activity_id",
          subject_area: "activity",
          p6_field: "Activity ID",
          display_name: "Activity ID",
          data_type: "string",
          writable: false,
          computed: false,
          disposition: "supported",
        },
        {
          field_id: "activity.name",
          subject_area: "activity",
          p6_field: "Activity Name",
          display_name: "Activity Name",
          data_type: "string",
          writable: false,
          computed: false,
          disposition: "supported",
        },
      ],
    } as const,
    p6Layout: {
      schema_version: "p6-layout.v1",
      scope: "project",
      view_id: "activity-grid",
      revision: 4,
      columns: [
        {
          field_id: "activity.activity_id",
          visible: true,
          order: 0,
          width: 120,
          alignment: "start",
          pinned: false,
          frozen: false,
        },
        {
          field_id: "activity.name",
          visible: false,
          order: 1,
          width: 240,
          alignment: "start",
          pinned: false,
          frozen: false,
        },
      ],
    } as const,
  };
  const events: string[] = [];
  let clickListener: ((event: Event) => void) | undefined;
  const undoButton = { dataset: { p6LayoutUndo: "" }, closest: () => undoButton };
  const redoButton = { dataset: { p6LayoutRedo: "" }, closest: () => redoButton };
  const restoreButton = { dataset: { p6LayoutRestore: "" }, closest: () => restoreButton };
  const revisionSelect = { value: "2" };
  const container: RenderContainer & {
    addEventListener: (event: string, listener: (event: Event) => void) => void;
    querySelector: (selector: string) => unknown;
  } = {
    innerHTML: "",
    querySelectorAll: () => [],
    addEventListener: (event, listener) => { if (event === "click") clickListener = listener; },
    querySelector: (selector) => selector === "[data-p6-layout-revision-select]" ? revisionSelect : null,
  };

  renderMainWorkspace(container as unknown as HTMLElement, state, {
    layoutHistory: {
      canUndo: true,
      canRedo: false,
      revisions: [
        { revision: 4, columnCount: 2 },
        { revision: 2, columnCount: 1 },
      ],
    },
    onP6LayoutUndo: () => events.push("undo"),
    onP6LayoutRedo: () => events.push("redo"),
    onP6LayoutRestore: (revision) => events.push(`restore:${revision}`),
  });

  assert.match(container.innerHTML, /data-settings-layout/);
  assert.match(container.innerHTML, /aria-label="Layout administration"/);
  assert.match(container.innerHTML, /<dt>Scope<\/dt><dd>project<\/dd>/);
  assert.match(container.innerHTML, /<dt>View<\/dt><dd>activity-grid<\/dd>/);
  assert.match(container.innerHTML, /<dt>Revision<\/dt><dd>R4<\/dd>/);
  assert.match(container.innerHTML, /<dt>Columns<\/dt><dd>1 \/ 2<\/dd>/);
  assert.match(container.innerHTML, /Field Registry · project · R4/);
  const undoMarkup = container.innerHTML.match(/<button[^>]*data-p6-layout-undo[^>]*>/)?.[0] ?? "";
  const redoMarkup = container.innerHTML.match(/<button[^>]*data-p6-layout-redo[^>]*>/)?.[0] ?? "";
  const restoreMarkup = container.innerHTML.match(/<button[^>]*data-p6-layout-restore[^>]*>/)?.[0] ?? "";
  assert.ok(!undoMarkup.includes("disabled"), "undo must be enabled when canUndo is true");
  assert.ok(redoMarkup.includes("disabled"), "redo must be disabled when canRedo is false");
  assert.ok(!restoreMarkup.includes("disabled"), "restore must be enabled when older revisions exist");
  assert.match(container.innerHTML, /<option value="2">R2 · 1 column\(s\)<\/option>/);
  assert.match(container.innerHTML, /Only the activity-grid layout is exposed/);

  clickListener?.({ target: undoButton } as unknown as Event);
  clickListener?.({ target: redoButton } as unknown as Event);
  clickListener?.({ target: restoreButton } as unknown as Event);
  assert.deepEqual(events, ["undo", "redo", "restore:2"]);
});

function wbsActivityState() {
  let state = createWorkspaceState(
    { tenant_id: "tenant-1", project_id: "project-1", revision: 3 },
    "en",
  );
  state = withWbsNodes(state, [
    { id: "W-ROOT", parentKind: "project", parentWbsId: null, localCode: "1", name: "Project", sequenceNumber: 0, recordRevision: 1 },
    { id: "W-A", parentKind: "wbs", parentWbsId: "W-ROOT", localCode: "1.1", name: "Civil", sequenceNumber: 10, recordRevision: 1 },
    { id: "W-A1", parentKind: "wbs", parentWbsId: "W-A", localCode: "1.1.1", name: "Earthwork", sequenceNumber: 10, recordRevision: 1 },
    { id: "W-B", parentKind: "wbs", parentWbsId: "W-ROOT", localCode: "1.2", name: "Structure", sequenceNumber: 20, recordRevision: 1 },
  ]);
  return withActivities(state, [
    {
      id: "A-1", wbsId: "W-A1", code: "A1", name: "Excavate",
      cells: { duration: 2 },
      gantt: { start: "2026-09-01T00:00:00Z", finish: "2026-09-03T00:00:00Z", progressPercent: 50, critical: true },
    },
    {
      id: "A-2", wbsId: "W-A1", code: "A2", name: "Haul",
      cells: { duration: 2 },
      gantt: { start: "2026-09-03T00:00:00Z", finish: "2026-09-05T00:00:00Z", progressPercent: 100, critical: false },
    },
    {
      id: "B-1", wbsId: "W-B", code: "B1", name: "Rebar",
      cells: { duration: 2 },
      gantt: { start: "2026-09-02T00:00:00Z", finish: "2026-09-04T00:00:00Z", progressPercent: 0, critical: false },
    },
  ]);
}

test("activity grid renders colored WBS bands with expand controls and matching Gantt summary rows", () => {
  const container: RenderContainer = { innerHTML: "", querySelectorAll: () => [] };
  renderMainWorkspace(container as unknown as HTMLElement, wbsActivityState());
  const html = container.innerHTML;

  assert.match(html, /<tr role="row" data-wbs-row="W-ROOT" data-band-key="W-ROOT" data-wbs-level="1" data-wbs-depth="0" data-wbs-collapsed="false" tabindex="0" aria-label="1 Project" aria-expanded="true" class="cp-p6-wbs-band cp-p6-tree-band" style="--cp-wbs-level:#0000ff;--cp-wbs-ink:#ffff00;--cp-wbs-font-family:Tahoma, &quot;Segoe UI&quot;, sans-serif;--cp-wbs-font-size:11px;--cp-wbs-row-height:22px"/);
  assert.match(html, /data-wbs-row="W-A" data-band-key="W-A" data-wbs-level="2" data-wbs-depth="1"[^>]*style="--cp-wbs-level:#80ff80;--cp-wbs-ink:#000000;--cp-wbs-font-family:Tahoma/);
  assert.match(html, /data-wbs-row="W-A1" data-band-key="W-A1" data-wbs-level="3" data-wbs-depth="2"[^>]*style="--cp-wbs-level:#ffff00;--cp-wbs-ink:#0000ff;--cp-wbs-font-family:Tahoma/);
  // The band carries its own label composition: code and name by default, and
  // the "WBS" title only when Show Title is enabled.
  assert.match(html, /class="cp-p6-wbs-code">1\.1\.1</);
  assert.doesNotMatch(html, /class="cp-p6-wbs-title"/);
  assert.match(html, /data-wbs-toggle="W-ROOT" aria-expanded="true"[^>]*>−</);
  assert.match(html, /data-wbs-toggle="W-A1" aria-expanded="true"[^>]*>−</);
  assert.match(html, /data-rollup="display" title="Derived for display from 2 persisted child activities"[^>]*>4<\/td>/);
  assert.match(html, /data-activity-id="A-1"[^>]*data-wbs-depth="3"/);
  // Each level draws a solid vertical spine inside the tree cell, so the
  // parent/child extent is visible even on leaf rows.
  assert.match(html, /class="cp-p6-tree-guides" data-tree-depth="3" style="--cp-wbs-level:#ffff00"><span class="cp-p6-wbs-spine" data-spine-level="1" style="--cp-spine:#0000ff" aria-hidden="true"><\/span><span class="cp-p6-wbs-spine" data-spine-level="2" style="--cp-spine:#80ff80" aria-hidden="true"><\/span><span class="cp-p6-wbs-spine" data-spine-level="3" style="--cp-spine:#ffff00" aria-hidden="true"><\/span>/);
  // The reference chart has no frozen label pane: rows are bars only, and the
  // table already carries the hierarchy.
  assert.doesNotMatch(html, /cp-gantt-label/);
  assert.match(html, /class="cp-gantt-row cp-gantt-group-row" data-gantt-wbs-id="W-ROOT"[^>]*><div class="cp-gantt-track">/);
  // A dashed rule closes each WBS branch instead of ruling every row.
  assert.match(html, /class="cp-gantt-row is-group-end" role="button" data-gantt-activity-id="A-2"/);
  assert.equal((html.match(/is-group-end/g) ?? []).length, 2);
  // Summary bars use the classic black bar with downward triangle caps and the
  // reference "Finish, Activity ID  Activity Name" label.
  assert.match(html, /class="cp-gantt-summary-bar[^"]*"[^>]*--cp-bar-body:#000000[^>]*><span class="cp-gantt-endpoint is-start is-triangle-down"/);
  assert.match(html, />05-Sep-26, 1  Project</);
  assert.match(html, />03-Sep-26, A-1  Excavate</);
  assert.match(html, /data-wbs-expand-all/);
  assert.match(html, /data-wbs-collapse-all/);
  assert.match(html, /data-wbs-collapse-to/);
  assert.match(html, /class="cp-gantt-row cp-gantt-group-row" data-gantt-wbs-id="W-ROOT" data-gantt-depth="0"/);
  assert.match(html, /class="cp-gantt-row cp-gantt-group-row" data-gantt-wbs-id="W-A1" data-gantt-depth="2"/);
  assert.match(html, /data-gantt-summary="derived" data-gantt-wbs-id="W-ROOT"/);
  assert.equal((html.match(/data-gantt-summary="derived"/g) ?? []).length, 4);
});

test("WBS band format applies its own font, ink, height and label selection", () => {
  const container: RenderContainer = { innerHTML: "", querySelectorAll: () => [] };
  renderMainWorkspace(container as unknown as HTMLElement, wbsActivityState(), {
    presentation: {
      ...DEFAULT_PRESENTATION,
      wbs: {
        ...DEFAULT_PRESENTATION.wbs,
        fontFamily: "cairo",
        fontSize: 14,
        inkMode: "custom",
        textColor: "#102030",
        rowHeight: 30,
        labels: { title: true, code: false, name: false },
      },
    },
  });
  const html = container.innerHTML;
  // Band typography and height are published per row, independent of the
  // activity table's font and row-height variables.
  assert.match(html, /--cp-wbs-level:#0000ff;--cp-wbs-ink:#102030;--cp-wbs-font-family:&quot;Cairo&quot;, &quot;Vazirmatn&quot;, &quot;Segoe UI&quot;, sans-serif;--cp-wbs-font-size:14px;--cp-wbs-row-height:30px/);
  assert.match(html, /class="cp-p6-wbs-title">WBS</);
  assert.doesNotMatch(html, /class="cp-p6-wbs-code">/);
  assert.doesNotMatch(html, /class="cp-p6-wbs-name"/);
});

test("collapsing a WBS branch removes its table rows and Gantt bars together", () => {
  let state = wbsActivityState();
  setCollapsedWbsIds(state.context.project_id, ["W-A"]);
  const container: RenderContainer = { innerHTML: "", querySelectorAll: () => [] };
  renderMainWorkspace(container as unknown as HTMLElement, state);
  const html = container.innerHTML;
  assert.match(html, /data-wbs-row="W-A" data-band-key="W-A" data-wbs-level="2" data-wbs-depth="1" data-wbs-collapsed="true"/);
  assert.match(html, /data-wbs-toggle="W-A" aria-expanded="false"[^>]*>\+</);
  assert.doesNotMatch(html, /data-activity-id="A-1"/);
  assert.doesNotMatch(html, /data-activity-id="A-2"/);
  assert.doesNotMatch(html, /data-gantt-wbs-id="W-A1"/);
  assert.doesNotMatch(html, /data-gantt-activity-id="A-1"/);
  assert.match(html, /data-gantt-wbs-id="W-B"/);
  assert.match(html, /data-activity-id="B-1"/);
  setCollapsedWbsIds(state.context.project_id, []);
});

test("activity context menu exposes the reference commands, real ones enabled and unsupported ones disabled with a reason", () => {
  const state = { ...wbsActivityState(), selectedActivityId: "A-1" };
  const items = workspaceMenuItems(
    { state, options: {} },
    { kind: "table-activity", activityId: "A-1", anchor: {} as HTMLElement },
  );
  const commands = items.map((item) => item.command);
  for (const command of [
    "details", "cut", "copy", "paste", "fill-down", "add", "delete", "dissolve", "renumber",
    "export-excel", "assign", "link", "columns", "line-numbers", "font-row", "filters",
    "group-sort", "expand-all", "collapse-all", "collapse-to",
  ]) {
    assert.ok(commands.includes(command), `missing context command ${command}`);
  }
  const byCommand = new Map(items.map((item) => [item.command, item]));
  assert.equal(byCommand.get("cut")?.disabled, true);
  assert.match(byCommand.get("cut")?.reason ?? "", /activity delete route/);
  assert.equal(byCommand.get("delete")?.disabled, true);
  assert.match(byCommand.get("export-excel")?.reason ?? "", /no XLSX export route exists/);
  assert.match(byCommand.get("assign")?.reason ?? "", /Resource assignment write is not available/);
  assert.notEqual(byCommand.get("details")?.disabled, true);
  assert.notEqual(byCommand.get("link")?.disabled, true);

  const headerItems = workspaceMenuItems(
    { state, options: {} },
    { kind: "table-header", columnId: state.columns[0]?.id ?? "", anchor: {} as HTMLElement },
  );
  const headerCommands = headerItems.map((item) => item.command);
  assert.ok(headerCommands.includes("columns"), "column header menu must open the real Columns dialog");
  assert.ok(headerCommands.includes("sort-asc"));
  assert.ok(headerCommands.includes("sort-desc"));
  assert.ok(headerCommands.includes("hide-column"));

  const ganttLinkItems = workspaceMenuItems(
    { state, options: {} },
    { kind: "gantt-link", relationshipId: state.relationships[0]?.id, anchor: {} as HTMLElement },
  );
  const linkCommands = ganttLinkItems.map((item) => item.command);
  assert.ok(linkCommands.includes("relationship-edit"));
  assert.ok(linkCommands.includes("relationship-delete"));
  assert.ok(!linkCommands.includes("cut"), "relationship menus must not carry activity-only commands");
});

test("right-click on an activity row selects it, prevents the browser menu and opens the pointer portal", () => {
  const listeners = new Map<string, (event: Event) => void>();
  const container = {
    innerHTML: "",
    querySelectorAll: () => [],
    querySelector: () => null,
    addEventListener: (type: string, listener: (event: Event) => void) => listeners.set(type, listener),
  };
  const selected: string[] = [];
  renderMainWorkspace(container as unknown as HTMLElement, wbsActivityState(), {
    onActivitySelect: (activityId) => selected.push(activityId),
  });
  const row = {
    dataset: { activityId: "A-1" },
    closest: (selector: string) => (selector.includes("[data-activity-id]") ? row : null),
  };
  let prevented = 0;
  listeners.get("contextmenu")?.({
    target: row,
    preventDefault: () => { prevented += 1; },
    clientX: 40,
    clientY: 30,
  } as unknown as Event);
  assert.equal(prevented, 1);
  assert.deepEqual(selected, ["A-1"]);
});

function layoutStorage(seed: Record<string, string> = {}): Storage {
  const rows = new Map(Object.entries(seed));
  return {
    get length() { return rows.size; },
    clear: () => rows.clear(),
    getItem: (key: string) => rows.get(key) ?? null,
    key: (index: number) => Array.from(rows.keys())[index] ?? null,
    removeItem: (key: string) => { rows.delete(key); },
    setItem: (key: string, value: string) => { rows.set(key, String(value)); },
  };
}

test("Activities layout helpers only offer views backed by persisted data", () => {
  const base = createWorkspaceState({ tenant_id: "tenant-1", project_id: "project-1", revision: 3 }, "en");
  assert.equal(isWorkspaceTopLayoutAvailable("table-only", base), true);
  assert.equal(isWorkspaceTopLayoutAvailable("table-gantt", base), true);
  assert.equal(isWorkspaceTopLayoutAvailable("activity-network", base), false);
  assert.equal(isWorkspaceTraceLogicAvailable(base), false);
  const rows = withActivities(base, [
    { id: "A", wbsId: "W1", code: "A", name: "A" },
    { id: "B", wbsId: "W1", code: "B", name: "B" },
  ]);
  assert.equal(isWorkspaceTopLayoutAvailable("activity-network", rows), false);
  const linked = withRelationships(rows, [
    { id: "r1", predecessorId: "A", successorId: "B", type: "FS", lagValue: "0", lagUnit: "working-day", recordRevision: 1 },
  ]);
  assert.equal(isWorkspaceTopLayoutAvailable("activity-network", linked), true);
  assert.equal(isWorkspaceTraceLogicAvailable(linked), false);
  assert.equal(isWorkspaceTraceLogicAvailable({ ...linked, selectedActivityId: "A" }), true);
});

test("Activities renders the table-only top layout and the Trace Logic bottom surface", () => {
  const state = {
    ...withRelationships(
      withActivities(createWorkspaceState({ tenant_id: "tenant-1", project_id: "project-1", revision: 3 }, "en"), [
        { id: "A", wbsId: "W1", code: "A", name: "Kickoff" },
        { id: "B", wbsId: "W1", code: "B", name: "Design" },
      ]),
      [{ id: "r1", predecessorId: "A", successorId: "B", type: "FS", lagValue: "2", lagUnit: "working-day", recordRevision: 1 }],
    ),
    selectedActivityId: "B",
  };
  const storage = layoutStorage({
    "cubi:workspace:top-layout:tenant-1:project-1:schedule": "table-only",
    "cubi:workspace:bottom-layout:tenant-1:project-1:schedule": "trace-logic",
  });
  const previous = Object.getOwnPropertyDescriptor(globalThis, "window");
  Object.defineProperty(globalThis, "window", { value: { localStorage: storage }, configurable: true });
  try {
    assert.equal(readWorkspaceBottomLayout(state), "trace-logic");
    const enhanced: HTMLElement[] = [];
    const details = { id: "cp-details", innerHTML: "" };
    const container: RenderContainer & { querySelector: (selector: string) => unknown } = {
      innerHTML: "",
      querySelectorAll: () => [],
      querySelector: (selector: string) => (selector === "#cp-details" ? details : null),
    };
    renderMainWorkspace(container as unknown as HTMLElement, state, {
      enhanceActivityDetails: (host: HTMLElement) => { enhanced.push(host); },
    });
    const html = container.innerHTML;
    assert.match(html, /data-top-layout="table-only"/);
    assert.doesNotMatch(html, /id="cp-gantt"/);
    assert.doesNotMatch(html, /data-panel-splitter/);
    assert.match(html, /data-bottom-surface="trace-logic"/);
    assert.match(html, /data-trace-logic/);
    assert.match(html, /data-trace-goto="A"/);
    assert.match(html, /aria-labelledby="cp-trace-heading"/);
    // The interactive Activity Details must never replace Trace Logic.
    assert.equal(enhanced.length, 0);

    storage.setItem("cubi:workspace:bottom-layout:tenant-1:project-1:schedule", "details");
    const detailsContainer: RenderContainer & { querySelector: (selector: string) => unknown } = {
      innerHTML: "",
      querySelectorAll: () => [],
      querySelector: (selector: string) => (selector === "#cp-details" ? details : null),
    };
    renderMainWorkspace(detailsContainer as unknown as HTMLElement, state, {
      enhanceActivityDetails: (host: HTMLElement) => { enhanced.push(host); },
    });
    assert.equal(readWorkspaceBottomLayout(state), "details");
    assert.equal(enhanced.length, 1);
    assert.equal(enhanced[0], details as unknown as HTMLElement);
  } finally {
    if (previous) Object.defineProperty(globalThis, "window", previous);
    else Reflect.deleteProperty(globalThis, "window");
  }
});

test("Projects window lists exactly the session projects and marks the open one", () => {
  const state = { ...createWorkspaceState({ tenant_id: "tenant-1", project_id: "p-1", revision: 3 }, "en"), activeMenu: "project" as const };
  const summary: ProjectSummary = {
    project_id: "p-1",
    tenant_id: "tenant-1",
    name: "Metro Line",
    revision: 3,
    start_date: "2026-01-05",
    date_system: "jalali",
    primary_calendar_id: "CAL-7",
    settings_revision: 4,
  };
  const listed: ProjectSummary[] = [
    { project_id: "p-1", tenant_id: "tenant-1", name: "Stale name", revision: 1 },
    { project_id: "p-2", tenant_id: "tenant-1", name: "Depot", revision: 2, date_system: "gregorian" },
  ];
  const container = { innerHTML: "", querySelectorAll: () => [], addEventListener: () => {} };
  renderMainWorkspace(container as unknown as HTMLElement, state, { projectSummary: summary, projects: listed });
  const html = container.innerHTML;
  assert.match(html, /data-project-row="p-1" aria-current="true"/);
  assert.match(html, /data-project-row="p-2"/);
  assert.match(html, /Metro Line/);
  assert.doesNotMatch(html, /Stale name/);
  assert.match(html, /data-project-open="p-2"/);
  assert.doesNotMatch(html, /data-project-open="p-1"/);
  assert.match(html, /cp-project-current/);
  assert.match(html, /CAL-7/);
  assert.doesNotMatch(html, /data-project-metadata-pending/);
});

test("Projects window states when the authoritative project record is still unread", () => {
  const state = { ...createWorkspaceState({ tenant_id: "tenant-1", project_id: "p-1", revision: 3 }, "en"), activeMenu: "project" as const };
  const container = { innerHTML: "", querySelectorAll: () => [], addEventListener: () => {} };
  renderMainWorkspace(container as unknown as HTMLElement, state, {
    projects: [{ project_id: "p-1", tenant_id: "tenant-1", name: "Metro Line", revision: 3 }],
  });
  assert.match(container.innerHTML, /data-project-metadata-pending="true"/);
  assert.match(container.innerHTML, /The authoritative project record has not been read yet/);
  assert.match(
    container.innerHTML,
    /<div class="cp-project" data-project-id="p-1" title="p-1">Metro Line<\/div>/,
  );
  assert.match(container.innerHTML, /data-project-row="p-1" aria-current="true"/);
  assert.match(container.innerHTML, /cp-project-current/);
  assert.doesNotMatch(container.innerHTML, /data-project-open="p-1"/);
});

test("Project Details tabs read the authoritative project summary instead of placeholders", () => {
  const state = { ...createWorkspaceState({ tenant_id: "tenant-1", project_id: "p-1", revision: 3 }, "en"), activeMenu: "project" as const };
  const summary: ProjectSummary = {
    project_id: "p-1",
    tenant_id: "tenant-1",
    name: "Metro Line",
    revision: 3,
    description: "Phase 2 civil works",
    start_date: "2026-01-05",
    date_system: "jalali",
    primary_calendar_id: "CAL-7",
    settings_revision: 4,
  };
  const withSummary = { innerHTML: "", querySelectorAll: () => [], addEventListener: () => {} };
  renderMainWorkspace(withSummary as unknown as HTMLElement, state, { projectSummary: summary });
  const html = withSummary.innerHTML;
  assert.match(html, /Project Details/);
  assert.match(
    html,
    /<div class="cp-project" data-project-id="p-1" title="p-1">Metro Line<\/div>/,
  );
  assert.match(html, /Edit Project/);
  assert.match(html, /Phase 2 civil works/);
  assert.match(html, /2026-01-05/);
  assert.match(html, /Jalali/);
  assert.match(html, /CAL-7/);
  assert.match(html, /R4/);
  assert.match(html, /data-project-detail-tab="general" aria-selected="true"/);
  assert.doesNotMatch(html, /The authoritative project record has not been read yet/);

  const unread = { innerHTML: "", querySelectorAll: () => [], addEventListener: () => {} };
  renderMainWorkspace(unread as unknown as HTMLElement, state);
  assert.match(unread.innerHTML, /The authoritative project record has not been read yet/);
  assert.doesNotMatch(unread.innerHTML, />R0</);
});

test("opening another project from the table dispatches exactly one switch request", () => {
  const listeners = new Map<string, (event: Event) => void>();
  const container = {
    innerHTML: "",
    querySelectorAll: () => [],
    addEventListener: (type: string, listener: (event: Event) => void) => listeners.set(type, listener),
  };
  const state = { ...createWorkspaceState({ tenant_id: "tenant-1", project_id: "p-1", revision: 3 }, "en"), activeMenu: "project" as const };
  const opened: string[] = [];
  renderMainWorkspace(container as unknown as HTMLElement, state, { onProjectOpen: (projectId) => opened.push(projectId) });
  const other = { dataset: { projectOpen: "p-2" }, closest: () => other };
  listeners.get("click")?.({ target: other } as unknown as Event);
  const current = { dataset: { projectOpen: "p-1" }, closest: () => current };
  listeners.get("click")?.({ target: current } as unknown as Event);
  assert.deepEqual(opened, ["p-2"]);
});

test("Projects register groups real records by persisted Business Domain and shows selection controls", () => {
  const state = { ...createWorkspaceState({ tenant_id: "tenant-1", project_id: "p-1", revision: 3 }, "en"), activeMenu: "project" as const };
  const listed: ProjectSummary[] = [
    { project_id: "p-1", tenant_id: "tenant-1", name: "Metro Line", revision: 3, business_domain: "infrastructure", status: "active" },
    { project_id: "p-2", tenant_id: "tenant-1", name: "Refinery", revision: 1, business_domain: "oil_gas", status: "planned" },
    { project_id: "p-3", tenant_id: "tenant-1", name: "Unassigned", revision: 0 },
  ];
  const container = { innerHTML: "", querySelectorAll: () => [], addEventListener: () => {} };
  renderMainWorkspace(container as unknown as HTMLElement, state, { projects: listed });
  const html = container.innerHTML;
  assert.match(html, /data-project-register/);
  assert.match(html, /data-project-search/);
  assert.match(html, /data-project-domain-filter/);
  assert.match(html, /data-project-sort/);
  assert.match(html, /3 of 3 projects/);
  assert.match(html, /data-project-domain-group="infrastructure"/);
  assert.match(html, /data-project-domain-group="oil_gas"/);
  assert.match(html, /data-project-domain-group="__unclassified__"/);
  assert.match(html, /Infrastructure/);
  assert.match(html, /Oil &amp; Gas/);
  assert.match(html, /Not classified/);
  assert.match(html, /data-project-select="p-1"/);
  assert.match(html, /data-project-select="p-2"/);
  assert.match(html, /data-project-selection/);
  assert.match(html, /Business Domain<\/th>/);
  assert.match(html, /Planned/);
});

test("Projects register renders empty and loading states without inventing rows", () => {
  const state = { ...createWorkspaceState({ tenant_id: "tenant-1", project_id: "p-1", revision: 3 }, "en"), activeMenu: "project" as const };
  const empty = { innerHTML: "", querySelectorAll: () => [], addEventListener: () => {} };
  renderMainWorkspace(empty as unknown as HTMLElement, state, { projects: [] });
  assert.match(empty.innerHTML, /The session service returned no projects\./);
  assert.doesNotMatch(empty.innerHTML, /data-project-row=/);

  const loading = { innerHTML: "", querySelectorAll: () => [], addEventListener: () => {} };
  renderMainWorkspace(loading as unknown as HTMLElement, state, {});
  assert.match(loading.innerHTML, /Loading the session-authorized project list/);
  assert.match(loading.innerHTML, /data-project-register aria-busy="true"/);
});

test("Projects register localizes the Business Domain tree for Persian", () => {
  const state = { ...createWorkspaceState({ tenant_id: "tenant-1", project_id: "p-1", revision: 3 }, "fa"), activeMenu: "project" as const };
  const container = { innerHTML: "", querySelectorAll: () => [], addEventListener: () => {} };
  renderMainWorkspace(container as unknown as HTMLElement, state, {
    projects: [{ project_id: "p-1", tenant_id: "tenant-1", name: "خط مترو", revision: 3, business_domain: "infrastructure" }],
  });
  const html = container.innerHTML;
  assert.match(html, /حوزه‌های کاری/);
  assert.match(html, /زیرساخت/);
  assert.match(html, /جست‌وجوی پروژه‌ها/);
  assert.match(html, /پروژهٔ انتخاب‌شده/);
  assert.doesNotMatch(html, /Infrastructure/);
});

test("WBS window renders persisted status and the weighted milestone editor", () => {
  const base = withWbsNodes(createWorkspaceState({ tenant_id: "tenant-1", project_id: "project-1", revision: 3 }, "en"), [{
    id: "W-1", parentKind: "project", parentWbsId: null, localCode: "1", name: "Project",
    sequenceNumber: 0, recordRevision: 4, status: "active", percentCompleteTechnique: "milestones",
    percentComplete: 75, milestones: [
      { id: "M-1", name: "Mobilize", weight: 9, completed: true, sequenceNumber: 0 },
      { id: "M-2", name: "Handover", weight: 3, completed: false, sequenceNumber: 1 },
    ],
  }]);
  const state = { ...base, activeMenu: "wbs" as const, selectedWbsId: "W-1" };
  const container: RenderContainer = { innerHTML: "", querySelectorAll: () => [] };
  renderMainWorkspace(container as unknown as HTMLElement, state);
  const html = container.innerHTML;
  assert.match(html, /Percent complete technique/);
  assert.match(html, />Active</);
  assert.match(html, />75\.00%</);
  assert.match(html, /data-wbs-milestones-form="W-1"/);
  assert.match(html, /data-wbs-revision="4"/);
  assert.equal((html.match(/<tr data-wbs-milestone-row>/g) ?? []).length, 4);
  assert.match(html, /value="Mobilize"/);
  assert.match(html, /name="milestone_weight" type="number" min="0\.01" step="0\.01" value="9"/);
});

test("WBS toolbar copies the selected element and pastes beneath the selected target", () => {
  const base = withWbsNodes(
    createWorkspaceState({ tenant_id: "tenant-1", project_id: "project-1", revision: 3 }, "en"),
    [
      { id: "W-ROOT", parentKind: "project", parentWbsId: null, localCode: "1", name: "Project", sequenceNumber: 0, recordRevision: 1 },
      { id: "W-CIVIL", parentKind: "wbs", parentWbsId: "W-ROOT", localCode: "1.1", name: "Civil", sequenceNumber: 0, recordRevision: 1 },
      { id: "W-CIVIL-SITE", parentKind: "wbs", parentWbsId: "W-CIVIL", localCode: "1.1.1", name: "Site works", sequenceNumber: 0, recordRevision: 1 },
      { id: "W-PM", parentKind: "wbs", parentWbsId: "W-ROOT", localCode: "1.2", name: "Project management", sequenceNumber: 1, recordRevision: 1 },
    ],
  );
  let clickListener: ((event: Event) => void) | undefined;
  const clipboard = { textContent: "" };
  const pasteButton = { disabled: true };
  const clipboardError = { hidden: true, textContent: "" };
  const container = {
    innerHTML: "",
    querySelectorAll: () => [],
    addEventListener: (event: string, listener: (event: Event) => void) => {
      if (event === "click") clickListener = listener;
    },
    querySelector: (selector: string) => {
      if (selector === "[data-wbs-clipboard]") return clipboard;
      if (selector === "[data-wbs-paste]") return pasteButton;
      if (selector === "[data-wbs-clipboard-error]") return clipboardError;
      return null;
    },
  };
  const events: string[] = [];
  const options = {
    onWbsUpdate: (wbsId: string, input: { parentWbsId?: string | null }) => {
      events.push(`update:${wbsId}:${input.parentWbsId ?? ""}`);
    },
    onWbsCopy: (wbsId: string, targetParentWbsId: string, rootCode: string) => {
      events.push(`copy:${wbsId}:${targetParentWbsId}:${rootCode}`);
    },
  };
  // A fresh presentation identity forces the full render path; a real browser
  // keeps its DOM, while this stub only exposes the rendered string.
  const paint = (selectedWbsId: string): void => {
    renderMainWorkspace(
      container as unknown as HTMLElement,
      { ...base, activeMenu: "wbs" as const, selectedWbsId },
      { ...options, presentation: { ...DEFAULT_PRESENTATION } },
    );
  };
  paint("W-CIVIL");
  assert.match(container.innerHTML, /data-wbs-cut/);
  assert.match(container.innerHTML, /data-wbs-copy/);
  assert.match(container.innerHTML, /<button type="button" data-wbs-paste disabled>/);
  assert.match(container.innerHTML, /Clipboard empty/);

  const copyButton = { dataset: { wbsCopy: "" }, closest: () => copyButton };
  clickListener?.({ target: copyButton } as unknown as Event);
  assert.equal(clipboard.textContent, "Clipboard: copy — Civil (1.1)");
  assert.equal(pasteButton.disabled, false);

  // Selecting a different element keeps the page-local clipboard entry.
  paint("W-PM");
  assert.match(container.innerHTML, /Clipboard: copy — Civil \(1\.1\)/);
  const paste = { dataset: { wbsPaste: "" }, closest: () => paste };
  clickListener?.({ target: paste } as unknown as Event);
  assert.deepEqual(events, ["copy:W-CIVIL:W-PM:1.1"]);

  // Cut pastes by moving the existing record to the selected parent.
  paint("W-CIVIL-SITE");
  const cutButton = { dataset: { wbsCut: "" }, closest: () => cutButton };
  clickListener?.({ target: cutButton } as unknown as Event);
  assert.equal(clipboard.textContent, "Clipboard: cut — Site works (1.1.1)");
  paint("W-PM");
  clickListener?.({ target: paste } as unknown as Event);
  assert.deepEqual(events, ["copy:W-CIVIL:W-PM:1.1", "update:W-CIVIL-SITE:W-PM"]);
});

test("Layout Options persists progress line, baseline and Data Date toggles through the presentation callback", () => {
  const listeners = new Map<string, (event: Event) => void>();
  const container = {
    innerHTML: "",
    querySelectorAll: () => [],
    addEventListener: (type: string, listener: (event: Event) => void) => listeners.set(type, listener),
  };
  const state = withActivities(createWorkspaceState({ tenant_id: "tenant-1", project_id: "project-1", revision: 3 }, "en"), [
    {
      id: "A-1", wbsId: "W-1", code: "A-1", name: "Foundation",
      cells: { "activity.baseline_start": "2026-09-01", "activity.baseline_finish": "2026-09-05" },
    },
  ]);
  const chosen: [string, boolean][] = [];
  renderMainWorkspace(container as unknown as HTMLElement, state, {
    presentation: normalizePresentation({
      bars: { baseline: { visible: true } },
      gantt: { progressLine: { visible: false }, dataDateLine: { visible: true } },
    }),
    onGanttDisplayToggle: (kind, visible) => chosen.push([kind, visible]),
  });
  assert.match(container.innerHTML, /data-layout-baseline checked/);
  assert.match(container.innerHTML, /data-layout-progress-line>/);
  assert.match(container.innerHTML, /data-layout-data-date-line checked/);
  const fire = (dataset: Record<string, string>, checked: boolean) => {
    const target = { dataset, checked, closest: () => null };
    listeners.get("change")?.({ target } as unknown as Event);
  };
  fire({ layoutProgressLine: "" }, true);
  fire({ layoutBaseline: "" }, false);
  fire({ layoutDataDateLine: "" }, false);
  assert.deepEqual(chosen, [
    ["progress-line", true],
    ["baseline", false],
    ["data-date-line", false],
  ]);
});

test("baseline bars stay disabled with an explicit reason when no stored window is loaded", () => {
  const empty = render("en", "schedule");
  assert.match(empty, /data-layout-baseline checked disabled/);
  assert.match(empty, /No stored baseline window is loaded for this project/);
});
