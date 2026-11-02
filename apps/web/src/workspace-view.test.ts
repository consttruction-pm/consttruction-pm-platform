import assert from "node:assert/strict";
import test from "node:test";

import { renderMainWorkspace } from "./workspace-view.js";
import type { WorkspaceMenuKey } from "./workspace-model.js";
import { createWorkspaceState, setDocuments, setP6Presentation, withActivities, withRelationships, withWbsNodes } from "./workspace-model.js";

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
  for (const menu of ["project", "wbs", "schedule", "progress", "resources", "assignments", "roles", "calendars", "cost", "expenses", "documents", "reports", "tracking", "issues", "risks", "thresholds", "control", "settings"] as const) {
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

test("WBS register exposes the connected add workflow and never fabricates a chart action", () => {
  const html = render("en", "wbs");
  assert.match(html, /data-rail-action="wbs"/);
  assert.match(html, /data-rail-action="wbs">Add WBS/);
  assert.match(html, /data-wbs-delete disabled/);
  assert.match(html, /WBS chart view is not connected yet/);
});

test("Activity Group and Sort defaults to WBS in English and Persian", () => {
  const english = render("en", "schedule");
  assert.match(english, /<select data-activity-group aria-label="Group by">\s*<option value="wbs" selected>WBS<\/option>/);
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

test("rendered schedule surface exposes localized label and partial status", () => {
  const html = render("en", "schedule");

  assert.match(html, /<strong>Schedule<\/strong>/);
  assert.match(html, /data-surface-status="partial">Partial<\/span>/);
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
  for (const label of ["Timescale start", "Date format", "Date interval", "Shift calendar", "Show ordinal dates", "Ordinal start", "Ordinal date interval", "Font &amp; Color", "Default Font", "Apply", "Help"]) {
    assert.ok(english.includes(label), `missing Timescale dialog control: ${label}`);
  }
  assert.match(english, /name="timescale-format"/);
  assert.match(english, /data-layout-options-actions/);
  assert.match(english, /data-layout-links/);

  const persian = render("fa", "schedule");
  assert.match(persian, /گزینه‌های چیدمان/);
  assert.match(persian, /مقیاس زمانی/);
  assert.match(persian, /نمایش خطوط روابط/);
});

test("Activity Details exposes the Bottom Layout Options tab customization dialog", () => {
  const html = render("en", "schedule");
  assert.match(html, /data-activity-details-options-open/);
  assert.match(html, /data-activity-details-options-dialog/);
  assert.match(html, /data-activity-detail-available/);
  assert.match(html, /data-activity-detail-display/);
  assert.match(html, /value="general"/);
  assert.match(html, /Available Tabs/);
  assert.match(html, /Display Tabs/);
  assert.match(html, /data-activity-detail-add-all/);
  assert.match(html, /data-activity-detail-remove-all/);
  assert.match(html, /data-activity-detail-move-up/);
  assert.match(html, /data-activity-detail-move-down/);
  assert.match(html, /data-activity-detail-default/);
  assert.match(html, /data-activity-details-apply-close/);
  assert.match(html, /Customize Activity Details/);
  assert.match(html, /Choose the available tabs, move them into Display Tabs, and arrange their order/);
});

test("Activity Details tab editor transfers tabs, reorders them and applies the selected order", () => {
  type Option = { value: string; selected: boolean; owner?: FakeSelect };
  class FakeSelect {
    options: Option[];
    constructor(options: Option[]) { this.options = options; options.forEach((option) => { option.owner = this; }); }
    get selectedOptions(): Option[] { return this.options.filter((option) => option.selected); }
    set selectedIndex(value: number) { if (value === -1) this.options.forEach((option) => { option.selected = false; }); }
    add(option: Option): void {
      if (option.owner) {
        const index = option.owner.options.indexOf(option);
        if (index >= 0) option.owner.options.splice(index, 1);
      }
      option.owner = this;
      this.options.push(option);
    }
    insertBefore(option: Option, reference: Option): void {
      const current = this.options.indexOf(option);
      if (current >= 0) this.options.splice(current, 1);
      const index = this.options.indexOf(reference);
      this.options.splice(index < 0 ? this.options.length : index, 0, option);
      option.owner = this;
    }
  }
  const availableOption: Option = { value: "resources", selected: true };
  const available = new FakeSelect([availableOption]);
  const displayed = new FakeSelect([
    { value: "general", selected: false },
    { value: "status", selected: false },
  ]);
  const dialog = {
    querySelector: (selector: string) => selector === "[data-activity-detail-available]" ? available : selector === "[data-activity-detail-display]" ? displayed : null,
    close: () => {},
  };
  const details = { innerHTML: "" };
  const listeners = new Map<string, (event: Event) => void>();
  const container = {
    innerHTML: "",
    querySelectorAll: () => [],
    querySelector: (selector: string) => selector === "[data-activity-details-options-dialog]" ? dialog : selector === "#cp-details" ? details : null,
    addEventListener: (type: string, listener: (event: Event) => void) => listeners.set(type, listener),
  };
  renderMainWorkspace(container as unknown as HTMLElement, createWorkspaceState(
    { tenant_id: "tenant-1", project_id: "project-1", revision: 3 },
    "en",
  ));
  const dispatch = (dataset: Record<string, string>) => {
    const target = { dataset, closest: () => target };
    listeners.get("click")?.({ target } as unknown as Event);
  };
  dispatch({ activityDetailAdd: "" });
  assert.deepEqual(displayed.options.map((option) => option.value), ["general", "status", "resources"]);
  dispatch({ activityDetailMoveUp: "" });
  assert.deepEqual(displayed.options.map((option) => option.value), ["general", "resources", "status"]);
  dispatch({ activityDetailsApplyClose: "" });
  assert.ok(details.innerHTML.indexOf('data-activity-detail-tab="general"') < details.innerHTML.indexOf('data-activity-detail-tab="resources"'));
  assert.ok(details.innerHTML.indexOf('data-activity-detail-tab="resources"') < details.innerHTML.indexOf('data-activity-detail-tab="status"'));
  assert.ok(details.innerHTML.includes('data-activity-detail-tab="status"'));
});

test("Documents window renders real records and navigable detail tabs", () => {
  const document = {
    documentId: "DOC-101",
    resourceType: "drawing" as const,
    title: "Foundation Layout",
    status: "approved" as const,
    revision: 2,
    contentHash: `sha256:${"a".repeat(64)}`,
    linkedEntityRefs: ["activity:ACT-101", "wbs:WBS-01"],
    hasStorageRef: true,
  };
  const state = {
    ...setDocuments(createWorkspaceState({ tenant_id: "tenant-1", project_id: "project-1", revision: 3 }, "en"), [document]),
    activeMenu: "documents" as const,
  };
  const listeners = new Map<string, (event: Event) => void>();
  const container = {
    innerHTML: "",
    querySelectorAll: () => [],
    addEventListener: (type: string, listener: (event: Event) => void) => listeners.set(type, listener),
  };
  renderMainWorkspace(container as unknown as HTMLElement, state);
  assert.match(container.innerHTML, /class="cp-documents-window"/);
  assert.match(container.innerHTML, /DOC-101/);
  assert.match(container.innerHTML, /Foundation Layout/);
  assert.match(container.innerHTML, /data-document-select="DOC-101"/);
  const rowTarget = { dataset: { documentSelect: "DOC-101" }, closest: () => rowTarget };
  listeners.get("click")?.({ target: rowTarget } as unknown as Event);
  assert.match(container.innerHTML, /aria-pressed="true"/);
  assert.match(container.innerHTML, /Document Details/);
  assert.match(container.innerHTML, /data-document-detail-tab="links"/);
  const linksTarget = { dataset: { documentDetailTab: "links" }, closest: () => linksTarget };
  listeners.get("click")?.({ target: linksTarget } as unknown as Event);
  assert.match(container.innerHTML, /activity:ACT-101/);
  assert.match(container.innerHTML, /wbs:WBS-01/);
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
  for (const tab of ["general", "status", "resources", "predecessors", "successors", "codes", "tasks", "discussion", "notebook", "steps", "feedback", "documents", "expenses", "summary", "relationships", "risks", "udfs"]) {
    assert.ok(html.includes(`data-activity-detail-tab="${tab}"`), `missing Activity Details tab: ${tab}`);
  }
  assert.match(html, /Select an activity in the table or Gantt chart/);
});
test("workspace tabs reflect persisted open windows and dispatch close for the selected window", () => {
  const listeners = new Map<string, (event: Event) => void>();
  const closed: WorkspaceMenuKey[] = [];
  const container = {
    innerHTML: "",
    querySelectorAll: () => [],
    addEventListener: (type: string, listener: (event: Event) => void) => listeners.set(type, listener),
  };
  renderMainWorkspace(
    container as unknown as HTMLElement,
    createWorkspaceState({ tenant_id: "tenant-1", project_id: "project-1", revision: 3 }, "en"),
    {
      openWindows: ["project", "schedule"],
      onWindowClose: (menu) => closed.push(menu),
    },
  );
  assert.match(container.innerHTML, /data-window-tab="project"/);
  assert.match(container.innerHTML, /data-window-tab="schedule"/);
  assert.match(container.innerHTML, /data-window-close="project"/);
  const target = { dataset: { windowClose: "project" }, closest: () => target };
  listeners.get("click")?.({ target } as unknown as Event);
  assert.deepEqual(closed, ["project"]);
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

test("Project Details splitter follows pointer dragging and double-click restores its default height", () => {
  const listeners = new Map<string, (event: Event) => void>();
  const styles: Record<string, string> = {};
  const root = { style: { setProperty: (name: string, value: string) => { styles[name] = value; } } };
  const splitter = {
    dataset: { projectDetailsSplitter: "" },
    setAttribute: () => {},
    setPointerCapture: () => {},
    releasePointerCapture: () => {},
  };
  const details = { getBoundingClientRect: () => ({ height: 240 }) };
  const container = {
    innerHTML: "",
    querySelectorAll: () => [],
    querySelector: (selector: string) => selector === ".cp-workspace[data-active-menu=project]" ? root
      : selector === "[data-project-details-splitter]" ? splitter
        : selector === "#cp-details" ? details : null,
    addEventListener: (type: string, listener: (event: Event) => void) => listeners.set(type, listener),
  };
  const state = {
    ...createWorkspaceState({ tenant_id: "tenant-1", project_id: "project-1", revision: 3 }, "en"),
    activeMenu: "project" as const,
  };
  renderMainWorkspace(container as unknown as HTMLElement, state);
  const target = { closest: () => splitter };
  listeners.get("pointerdown")?.({ target, pointerId: 7, clientY: 300, preventDefault: () => {} } as unknown as Event);
  listeners.get("pointermove")?.({ pointerId: 7, clientY: 280 } as unknown as Event);
  assert.equal(styles["--cp-project-details-height"], "260px");
  listeners.get("pointerup")?.({ target, pointerId: 7 } as unknown as Event);
  listeners.get("dblclick")?.({ target, preventDefault: () => {} } as unknown as Event);
  assert.equal(styles["--cp-project-details-height"], "240px");
});

test("module navigation submenus route to real registers, detail tabs and tracking views", () => {
  const wbs = render("en", "wbs");
  assert.match(wbs, /href="#cp-p6-module-stage"/);
  assert.match(wbs, /data-navigation-action="wbs-detail-tab:general"/);
  assert.match(wbs, /WBS Chart/);
  assert.match(wbs, /data-submenu-status="preview"/);

  const calendars = render("en", "calendars");
  for (const action of ["calendar-tab:workweek", "calendar-tab:exceptions", "calendar-tab:assignments"]) {
    assert.match(calendars, new RegExp(`data-navigation-action="${action}"`));
  }

  const roles = render("en", "roles");
  assert.match(roles, /data-navigation-action="register-tab:roles:rates"/);
  assert.match(roles, /data-navigation-action="register-tab:roles:assignments"/);

  const resources = render("en", "resources");
  assert.match(resources, /class="cp-register-window"/);
  assert.match(resources, /Resource ID/);
  assert.match(resources, /Max Units \/ Time/);
  assert.match(resources, /data-navigation-action="register-tab:resources:assignments"/);
  assert.match(resources, /data-navigation-action="register-tab:resources:codes"/);
  assert.match(resources, /data-navigation-action="register-tab:resources:roles"/);
  assert.match(resources, /Resource records are not yet returned by the project API/);

  const assignments = render("en", "assignments");
  assert.match(assignments, /data-navigation-action="register-tab:assignments:general"/);

  const issues = render("en", "issues");
  assert.match(issues, /data-navigation-action="register-tab:issues:details"/);

  const risks = render("en", "risks");
  assert.match(risks, /data-navigation-action="register-tab:risks:general"/);

  const thresholds = render("en", "thresholds");
  assert.match(thresholds, /data-navigation-action="register-tab:thresholds:monitoring"/);
  assert.match(thresholds, /data-navigation-action="register-tab:thresholds:details"/);

  const tracking = render("en", "tracking");
  for (const layout of ["bar-chart", "gantt-profile", "resource-analysis"]) {
    assert.match(tracking, new RegExp(`data-navigation-action="tracking-layout:${layout}"`));
  }
});

test("module navigation action activates a namespaced register detail tab", () => {
  const listeners = new Map<string, (event: Event) => void>();
  let activated = 0;
  const tab = { dataset: { registerTab: "roles:rates" }, click: () => { activated += 1; } };
  const container = {
    innerHTML: "",
    querySelectorAll: (selector?: string) => selector === "[data-register-tab]" ? [tab] : [],
    addEventListener: (type: string, listener: (event: Event) => void) => listeners.set(type, listener),
  };
  const state = {
    ...createWorkspaceState({ tenant_id: "tenant-1", project_id: "project-1", revision: 3 }, "en"),
    activeMenu: "roles" as const,
  };
  renderMainWorkspace(container as unknown as HTMLElement, state);
  const target = { dataset: { navigationAction: "register-tab:roles:rates" }, closest: () => target };
  listeners.get("click")?.({ target } as unknown as Event);
  assert.equal(activated, 1);
});

test("Activities window docks Activity Details below the grid and Gantt with a resize splitter", () => {
  const html = render("en", "schedule");
  assert.match(html, /class="cp-activity-details-splitter"[^>]*role="separator" aria-orientation="horizontal"/);
  assert.match(html, /id="cp-details" class="cp-panel cp-details cp-activity-details-dock"/);
  assert.match(html, /data-activity-details-options-open/);
  for (const tab of ["general", "status", "resources", "predecessors", "successors", "codes", "steps", "relationships", "documents", "expenses", "summary", "risks", "udfs"]) {
    assert.match(html, new RegExp(`data-activity-detail-tab="${tab}"`));
  }
});

test("Show on Bottom Activity Details command scrolls to the docked details pane", () => {
  const listeners = new Map<string, (event: Event) => void>();
  let scrolled = false;
  const details = { scrollIntoView: () => { scrolled = true; } };
  const container = {
    innerHTML: "",
    querySelectorAll: () => [],
    querySelector: (selector: string) => selector === "#cp-details" ? details : null,
    addEventListener: (type: string, listener: (event: Event) => void) => listeners.set(type, listener),
  };
  renderMainWorkspace(container as unknown as HTMLElement, createWorkspaceState(
    { tenant_id: "tenant-1", project_id: "project-1", revision: 3 },
    "en",
  ));
  const target = { dataset: { shellCommand: "Activity Details" }, closest: () => target };
  listeners.get("click")?.({ target } as unknown as Event);
  assert.equal(scrolled, true);
});

test("Projects window docks Project Details below the register with the full detail-tab strip", () => {
  const html = render("en", "project");
  assert.match(html, /class="cp-project-details-splitter"[^>]*role="separator" aria-orientation="horizontal"/);
  assert.match(html, /data-project-structure-splitter role="separator" aria-orientation="vertical"/);
  assert.match(html, /id="cp-details" class="cp-panel cp-details cp-project-details-dock"/);
  assert.match(html, /aria-label="Project detail tabs"/);
  for (const tab of ["general", "dates", "notebook", "budget-log", "spending-plan", "budget-summary", "funding", "codes", "defaults", "resources", "settings", "calculations", "planning-resources", "contract-management", "udfs"]) {
    assert.match(html, new RegExp(`data-project-detail-tab="${tab}"`));
  }
});

test("Project Structure leading rail supports keyboard and pointer resizing", () => {
  const listeners = new Map<string, (event: Event) => void>();
  const styles: Record<string, string> = {};
  const attributes: Record<string, string> = {};
  let direction = "ltr";
  const root = { style: { setProperty: (name: string, value: string) => { styles[name] = value; } }, getAttribute: () => direction };
  const splitter = {
    dataset: { projectStructureSplitter: "" },
    setAttribute: (name: string, value: string) => { attributes[name] = value; },
    setPointerCapture: () => {},
    releasePointerCapture: () => {},
  };
  const structure = { getBoundingClientRect: () => ({ width: 240 }) };
  const container = {
    innerHTML: "",
    querySelectorAll: () => [],
    querySelector: (selector: string) => selector === ".cp-workspace[data-active-menu=project]" ? root
      : selector === "[data-project-structure-splitter]" ? splitter
        : selector === ".cp-project-structure-summary" ? structure : null,
    addEventListener: (type: string, listener: (event: Event) => void) => listeners.set(type, listener),
  };
  const state = {
    ...createWorkspaceState({ tenant_id: "tenant-1", project_id: "project-1", revision: 3 }, "en"),
    activeMenu: "project" as const,
  };
  renderMainWorkspace(container as unknown as HTMLElement, state);
  const target = { dataset: { projectStructureSplitter: "" }, closest: () => target };
  let prevented = false;
  listeners.get("keydown")?.({ target, key: "ArrowRight", preventDefault: () => { prevented = true; } } as unknown as Event);
  assert.equal(prevented, true);
  assert.equal(styles["--cp-project-structure-width"], "256px");
  listeners.get("pointerdown")?.({ target, pointerId: 9, clientX: 300, preventDefault: () => {} } as unknown as Event);
  listeners.get("pointermove")?.({ pointerId: 9, clientX: 320 } as unknown as Event);
  assert.equal(styles["--cp-project-structure-width"], "260px");
  assert.equal(attributes["aria-valuenow"], "260");
  listeners.get("pointerup")?.({ target, pointerId: 9 } as unknown as Event);
  direction = "rtl";
  listeners.get("keydown")?.({ target, key: "ArrowLeft", preventDefault: () => {} } as unknown as Event);
  assert.equal(styles["--cp-project-structure-width"], "256px");
  listeners.get("pointerdown")?.({ target, pointerId: 10, clientX: 300, preventDefault: () => {} } as unknown as Event);
  listeners.get("pointermove")?.({ pointerId: 10, clientX: 280 } as unknown as Event);
  assert.equal(styles["--cp-project-structure-width"], "260px");
  listeners.get("pointerup")?.({ target, pointerId: 10 } as unknown as Event);
});

test("Project Details horizontal splitter supports keyboard resizing and persists its pane height", () => {
  const listeners = new Map<string, (event: Event) => void>();
  const styles: Record<string, string> = {};
  const attributes: Record<string, string> = {};
  const root = { style: { setProperty: (name: string, value: string) => { styles[name] = value; } } };
  const splitter = { setAttribute: (name: string, value: string) => { attributes[name] = value; } };
  const container = {
    innerHTML: "",
    querySelectorAll: () => [],
    querySelector: (selector: string) => selector === ".cp-workspace[data-active-menu=project]" ? root : selector === "[data-project-details-splitter]" ? splitter : null,
    addEventListener: (type: string, listener: (event: Event) => void) => listeners.set(type, listener),
  };
  const state = {
    ...createWorkspaceState({ tenant_id: "tenant-1", project_id: "project-1", revision: 3 }, "en"),
    activeMenu: "project" as const,
  };
  renderMainWorkspace(container as unknown as HTMLElement, state);
  const target = { dataset: { projectDetailsSplitter: "" }, closest: () => target };
  let prevented = false;
  listeners.get("keydown")?.({ target, key: "ArrowUp", preventDefault: () => { prevented = true; } } as unknown as Event);
  assert.equal(prevented, true);
  assert.equal(styles["--cp-project-details-height"], "256px");
  assert.equal(attributes["aria-valuenow"], "256");
});

test("rendered navigation surface follows Persian locale and RTL direction", () => {
  const html = render("fa", "schedule");

  assert.match(html, /dir="rtl"/);
  assert.match(html, /<strong>زمان‌بندی<\/strong>/);
  assert.match(html, /جدول فعالیت‌ها/);
  assert.match(html, /گانت/);
  assert.match(html, /data-surface-status="partial">جزئی<\/span>/);
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

  assert.deepEqual(registrations, ["pointerdown", "input", "submit", "click", "keydown", "pointerdown", "pointermove", "pointerup", "pointercancel", "dblclick", "change"]);
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
  const menuButtons = [
    { dataset: { menu: "schedule" }, setAttribute: () => {} },
    { dataset: { menu: "reports" }, setAttribute: () => {} },
  ];
  const container = {
    innerHTML: "",
    querySelectorAll: (selector: string) => selector === "[data-menu]" ? menuButtons : [],
    querySelector: (selector: string) => selector === ".cp-navigation-surface" ? navigation : null,
    addEventListener: () => {},
  };

  renderMainWorkspace(container as unknown as HTMLElement, base);
  const initialHtml = container.innerHTML;
  renderMainWorkspace(container as unknown as HTMLElement, { ...base, activeMenu: "reports" });

  assert.equal(container.innerHTML, initialHtml);
  assert.ok(navigation.outerHTML.includes("<strong>Reports</strong>"));
  assert.ok(navigation.outerHTML.includes('data-surface-status="preview"'));
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
  assert.match(container.innerHTML, /class="cp-panel cp-details cp-activity-details-dock" hidden/);
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
  assert.match(container.innerHTML, /class="cp-panel cp-details cp-activity-details-dock"[^>]*aria-labelledby="cp-details-heading"/);
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
  assert.match(container.innerHTML, /class="cp-gantt-row is-selected" role="button" data-gantt-activity-id="A-1" tabindex="0" aria-pressed="true" aria-label="A-1"/);
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
  assert.match(container.innerHTML, /<table role="grid" aria-label="Activity Grid" aria-multiselectable="false"[^>]*>/);
  assert.match(container.innerHTML, /<thead><tr role="row">/);
  assert.match(container.innerHTML, /<th role="columnheader" scope="col"/);
  assert.match(container.innerHTML, /<tr role="row" data-activity-id="A-1" tabindex="0" aria-selected="true" aria-label="A-1"/);
  assert.match(container.innerHTML, /<td role="gridcell"[^>]*>A-1<\/td>/);
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
  assert.match(container.innerHTML, /style="text-align:center;width:140px;--cp-p6-sticky-offset:0px"/);
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
  assert.match(container.innerHTML, /class="cp-wbs-tree" role="tree"/);
  assert.match(container.innerHTML, /data-wbs-id="W-ROOT"/);
  assert.match(container.innerHTML, /data-wbs-id="W-FOUNDATION"/);
  assert.match(container.innerHTML, /data-wbs-id="W-EMPTY"/);
  assert.match(container.innerHTML, /aria-level="2"/);
  assert.match(container.innerHTML, /Project &lt;Root&gt;/);
  assert.ok(container.innerHTML.indexOf("Foundation") < container.innerHTML.indexOf("Package with no activities"));
  assert.doesNotMatch(container.innerHTML, /data-wbs-id="A-/);
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
  assert.match(container.innerHTML, /data-column-id="start"[^>]*>2026-10-07<\/td>/);

  renderMainWorkspace(
    container as unknown as HTMLElement,
    { ...base, calendarMode: "jalali", columns: [dateColumn], activities: [row] },
  );
  assert.match(container.innerHTML, /data-column-id="start"[^>]*>۱۴۰۵\/۰۷\/۱۵<\/td>/);
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
  assert.match(container.innerHTML, />2026-09-02</);
  assert.match(container.innerHTML, /data-gantt-scale-mode="day"/);
  assert.match(container.innerHTML, /data-gantt-scale="day" aria-pressed="true"/);
  assert.match(container.innerHTML, /data-gantt-scale="week" aria-pressed="false"/);
  assert.match(container.innerHTML, /class="cp-gantt-bar is-critical is-milestone"/);
});

test("Gantt axis shows the Jalali display date while keeping canonical tick dates", () => {
  const container: RenderContainer = { innerHTML: "", querySelectorAll: () => [] };
  renderMainWorkspace(container as unknown as HTMLElement, scheduledGanttState("fa", "jalali"));
  assert.match(container.innerHTML, /data-gantt-tick="2026-09-01"[^>]*>۱۴۰۵/);
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

test("WBS, assignments, expenses, issues, risks and thresholds have separate register windows", () => {
  const cases: Array<[WorkspaceMenuKey, string]> = [
    ["wbs", "Work Breakdown Structure"],
    ["assignments", "Resource Assignments"],
    ["expenses", "Project Expenses"],
    ["issues", "Project Issues"],
    ["risks", "Project Risks"],
    ["thresholds", "Project Thresholds"],
  ];
  for (const [menu, title] of cases) {
    const html = render("en", menu);
    assert.ok(html.includes(title), `missing register surface: ${title}`);
    assert.match(html, /No records are loaded for this project|WBS hierarchy/);
  }
});

test("Roles and Tracking are first-class windows with their documented visual surfaces", () => {
  const roles = render("en", "roles");
  assert.match(roles, /Role Register/);
  assert.match(roles, /Max Units \/ Time/);
  assert.match(roles, /data-register-tab="roles:rates"/);
  assert.match(roles, /Select a role to view its limits information/);
  const tracking = render("en", "tracking");
  assert.match(tracking, /Tracking Layout/);
  assert.match(tracking, /Project Table/);
  assert.match(tracking, /Project Bar Chart/);
  assert.match(tracking, /Project Gantt \/ Profile/);
  assert.match(tracking, /Resource Analysis/);
  assert.match(tracking, /data-tracking-layout/);
});

test("Calendar Register opens as a first-class window with documented editor controls", () => {
  const html = render("en", "calendars");
  assert.match(html, /data-active-menu="calendars"/);
  assert.match(html, /Calendar Register/);
  assert.match(html, /Calendar Scope/);
  assert.match(html, /Workweek/);
  assert.match(html, /Exceptions and Holidays/);
  assert.match(html, /Assignments/);
  for (const tab of ["general", "workweek", "exceptions", "assignments"]) {
    assert.ok(html.includes(`id="cp-calendar-tab-${tab}" aria-controls="cp-calendar-panel-${tab}"`));
    assert.ok(html.includes(`role="tabpanel" id="cp-calendar-panel-${tab}" aria-labelledby="cp-calendar-tab-${tab}"`));
  }
  assert.match(html, /tabindex="0" class="is-active" data-calendar-editor-tab="general"/);
  assert.match(html, /tabindex="-1" class=""/);
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
  const withActivity = withActivities(base, [{
    id: "ACT-101", wbsId: "WBS-1", code: "A-101", name: "Excavation",
    cells: { start: "2026-11-03", finish: "2026-11-06", progress: 25 },
    gantt: { start: "2026-11-03", finish: "2026-11-06", progressPercent: 25, critical: false },
  }]);
  const wbsState = { ...withActivity, selectedWbsId: "WBS-1" };
  const container = { innerHTML: "", querySelectorAll: () => [], addEventListener: () => {} };
  renderMainWorkspace(container as unknown as HTMLElement, wbsState);
  for (const tab of ["general", "activities", "notebook", "budget-log", "spending-plan", "budget-summary", "milestones", "documents", "earned-value", "planning-resources", "udfs"]) {
    assert.ok(container.innerHTML.includes(`data-wbs-detail-tab="${tab}"`), `missing WBS Details tab: ${tab}`);
  }
  assert.match(container.innerHTML, /WBS Details/);
  assert.match(container.innerHTML, /Structure/);
  assert.match(container.innerHTML, /data-wbs-linked-activity="ACT-101"/);
  assert.match(container.innerHTML, /Excavation/);
  assert.match(container.innerHTML, /2026-11-03/);
  assert.match(container.innerHTML, /25/);
});

test("empty and preview-only modules show an explicit truthful surface", () => {
  const reports = render("en", "reports");
  assert.match(reports, /data-workspace-menu="reports"/);
  assert.match(reports, /Reports &amp; print/);
  assert.match(reports, /not available in this preview yet/);

  const progress = render("fa", "progress");
  assert.match(progress, /data-workspace-menu="progress"/);
  assert.match(progress, /داشبورد و نمودارهای اختصاصی پیشرفت/);
  assert.match(progress, /href="#cp-site-logs"/, "empty progress registers remain reachable");
  assert.match(progress, /href="#cp-field-operations"/, "empty field-operation registers remain reachable");
  assert.doesNotMatch(progress, /data-submenu-status="preview"/, "existing empty-state destinations are not disabled");

  const documents = render("en", "documents");
  assert.match(documents, /No project documents have been added or linked yet/);

  const settings = render("en", "settings");
  assert.match(settings, /id="cp-settings-panel"[^>]*data-workspace-menu="settings"/);
});


test("desktop workbench renders a grouped navigation tree, window tabs and contextual command rail", () => {
  const html = render("en", "schedule");
  assert.match(html, /class="[^"]*cp-navigation-tree/);
  const navigationStart = html.indexOf('class="cp-menu cp-p6-rail cp-navigation-tree"');
  const navigationEnd = html.indexOf("</nav>", navigationStart);
  const navigationMarkup = html.slice(navigationStart, navigationEnd + 6);
  assert.equal((navigationMarkup.match(/data-menu=/g) ?? []).length, 18);
  assert.match(html, /Project workspace/);
  assert.match(html, /Planning &amp; execution/);
  assert.match(html, /Resources &amp; cost/);
  assert.match(html, /class="cp-window-tabs"/);
  assert.match(html, /role="tab" data-window-tab="schedule" data-menu="schedule" aria-selected="true"/);
  assert.match(html, /class="cp-context-command-bar"/);
  assert.match(html, /Current window commands/);
  assert.match(html, /class="[^"]*cp-context-command-rail/);
  assert.match(html, /class="cp-context-add-menu"/);
  assert.match(html, /Calendars/);
  assert.match(html, /Roles/);
  assert.match(html, /Tracking/);
  assert.match(html, /Thresholds/);
  assert.match(html, /Add to current window/);
});

test("desktop workbench keeps contextual Add actions visibly unavailable until workflows exist", () => {
  const html = render("en", "schedule");
  assert.match(html, /role="menuitem" disabled/);
  assert.match(html, /create workflow is not connected yet/);
});


test("schedule workspace renders localized command ribbon and three layout choices", () => {
  const english = render("en", "schedule");
  assert.match(english, /class="cp-command-ribbon" role="toolbar"/);
  assert.match(english, /data-workspace-layout="split" aria-pressed="true"/);
  assert.match(english, /data-workspace-layout="grid" aria-pressed="false"/);
  assert.match(english, /data-workspace-layout="gantt" aria-pressed="false"/);
  assert.match(english, /data-workspace-command="run-schedule"/);
  assert.match(english, /data-workspace-command="relationships"/);
  const persian = render("fa", "schedule");
  assert.match(persian, /ابزارهای زمان‌بندی/);
  assert.match(persian, /جدول \+ گانت/);
  assert.match(persian, /افزودن فعالیت/);
});

test("workspace layout toolbar dispatches selected mode to the application", () => {
  const listeners = new Map<string, (event: Event) => void>();
  const container = {
    innerHTML: "",
    querySelectorAll: () => [],
    addEventListener: (type: string, listener: (event: Event) => void) => listeners.set(type, listener),
  };
  const layouts: string[] = [];
  renderMainWorkspace(container as unknown as HTMLElement, createWorkspaceState(
    { tenant_id: "tenant-1", project_id: "project-1", revision: 3 },
    "en",
  ), { onWorkspaceLayoutChange: (layout) => layouts.push(layout) });
  const gridButton = { dataset: { workspaceLayout: "grid" }, closest: () => gridButton };
  listeners.get("click")?.({ target: gridButton } as unknown as Event);
  assert.deepEqual(layouts, ["grid"]);
});


test("Group and Sort opens a structured dialog and applies supported grouping and sort controls", () => {
  const html = render("en", "schedule");
  assert.match(html, /data-group-sort-dialog/);
  for (const label of ["Display Options", "Show Group Totals", "Show Grand Total", "Show Summaries", "Shrink vertical groups", "Group By", "Hide if empty", "Sort bands alphabetically", "Field Name", "Sort Order", "Ascending", "Descending"]) {
    assert.ok(html.includes(label), `missing Group and Sort control: ${label}`);
  }
  assert.match(html, /data-group-sort-group/);
  assert.match(html, /data-group-sort-field/);
  assert.match(html, /data-group-sort-direction/);
  assert.match(html, /data-group-sort-apply/);
});

test("Group and Sort apply dispatches grouping and sort together without stale-state overwrites", () => {
  const listeners = new Map<string, (event: Event) => void>();
  const calls: unknown[][] = [];
  const dialog = {
    close: () => {},
    querySelector: (selector: string) => {
      if (selector === "[data-group-sort-group]") return { value: "none" };
      if (selector === "[data-group-sort-field]") return { value: "activity_name" };
      if (selector === "[data-group-sort-direction]") return { value: "desc" };
      return null;
    },
  };
  const container = {
    innerHTML: "",
    querySelectorAll: () => [],
    querySelector: (selector: string) => selector === "[data-group-sort-dialog]" ? dialog : null,
    addEventListener: (type: string, listener: (event: Event) => void) => listeners.set(type, listener),
  };
  renderMainWorkspace(container as unknown as HTMLElement, createWorkspaceState({ tenant_id: "tenant-1", project_id: "project-1", revision: 3 }, "en"), {
    onActivityGroupSortChange: (...args) => calls.push(args),
  });
  const target = { dataset: { groupSortApply: "" }, closest: () => target };
  listeners.get("click")?.({ target } as unknown as Event);
  assert.deepEqual(calls, [["none", "activity_name", "desc"]]);
});

test("Bars dialog exposes bar definition columns, style/settings/labels tabs and command column", () => {
  const html = render("en", "schedule");
  for (const label of ["Bars", "Display", "Name", "Timescale", "User Start", "User Finish", "Filter", "Preview", "Bar Style", "Bar Settings", "Bar Labels", "Shape", "Color", "Pattern", "Row", "Position", "Label", "Copy From...", "Shift Up", "Shift Down", "Options..."]) {
    assert.ok(html.includes(label), `missing Bars dialog inventory item: ${label}`);
  }
  assert.match(html, /data-bars-dialog/);
  assert.match(html, /data-bars-tab="style"/);
  assert.match(html, /data-bars-tab="settings"/);
  assert.match(html, /data-bars-tab="labels"/);
  assert.match(html, /data-bar-chart-options-open/);
});

test("Bar Chart Options exposes all documented tabs without enabling unsupported settings", () => {
  const html = render("en", "schedule");
  for (const label of ["General", "Collapsed Bars", "Data Date", "Sight Lines", "Progress Line", "Show Relationships", "Show Legend", "Limit Text Label Characters To", "Collapse to grouping bands", "Show Data Date", "Vertical Lines", "Baseline to use"]) {
    assert.ok(html.includes(label), `missing Bar Chart Options item: ${label}`);
  }
  assert.match(html, /data-bar-chart-options-dialog/);
  assert.match(html, /data-bar-options-tab="progress-line"/);
  assert.match(html, /data-layout-links/);
});

test("Show on Top Table and Gantt Chart commands select the matching workspace layout", () => {
  const listeners = new Map<string, (event: Event) => void>();
  const layouts: string[] = [];
  const container = {
    innerHTML: "",
    querySelectorAll: () => [],
    addEventListener: (type: string, listener: (event: Event) => void) => listeners.set(type, listener),
  };
  renderMainWorkspace(container as unknown as HTMLElement, createWorkspaceState(
    { tenant_id: "tenant-1", project_id: "project-1", revision: 3 },
    "en",
  ), { onWorkspaceLayoutChange: (layout) => layouts.push(layout) });
  const table = { dataset: { shellCommand: "Table" }, closest: () => table };
  const gantt = { dataset: { shellCommand: "Gantt Chart" }, closest: () => gantt };
  listeners.get("click")?.({ target: table } as unknown as Event);
  listeners.get("click")?.({ target: gantt } as unknown as Event);
  assert.deepEqual(layouts, ["grid", "gantt"]);
});

test("Edit menu Add Activity, Add WBS, Add Relationship and Find commands reach their live controls", () => {
  const listeners = new Map<string, (event: Event) => void>();
  const activated: string[] = [];
  const focused: string[] = [];
  const trigger = (name: string) => ({ click: () => activated.push(name) });
  const focusable = (name: string) => ({ focus: () => focused.push(name) });
  const container = {
    innerHTML: "",
    querySelectorAll: () => [],
    querySelector: (selector: string) => {
      if (selector === '[data-workspace-command="new-activity"]') return trigger("new-activity");
      if (selector === '[data-workspace-command="new-wbs"]') return trigger("new-wbs");
      if (selector === '[data-workspace-command="relationships"]') return trigger("relationships");
      if (selector === '[data-relationship-create-form] [name="predecessor_id"]') return focusable("predecessor");
      if (selector === "[data-activity-filter]") return focusable("find");
      return null;
    },
    addEventListener: (type: string, listener: (event: Event) => void) => listeners.set(type, listener),
  };
  renderMainWorkspace(container as unknown as HTMLElement, createWorkspaceState(
    { tenant_id: "tenant-1", project_id: "project-1", revision: 3 },
    "en",
  ));
  const dispatch = (command: string) => {
    const target = { dataset: { shellCommand: command }, closest: () => target };
    listeners.get("click")?.({ target } as unknown as Event);
  };
  dispatch("Add Activity");
  dispatch("Add WBS");
  dispatch("Add Relationship");
  dispatch("Find");
  assert.deepEqual(activated, ["new-activity", "new-wbs", "relationships"]);
  assert.deepEqual(focused, ["predecessor", "find"]);
});

test("Columns menu command opens the dedicated field registry dialog", () => {
  const html = render("en", "schedule");
  assert.match(html, /data-columns-dialog/);
  assert.match(html, /class="cp-columns-dialog"/);
  assert.match(html, /cp-columns-unavailable|class="cp-p6-field-chooser"/);
  const listeners = new Map<string, (event: Event) => void>();
  let opened = false;
  const dialog = { showModal: () => { opened = true; } };
  const container = {
    innerHTML: "",
    querySelectorAll: () => [],
    querySelector: (selector: string) => selector === "[data-columns-dialog]" ? dialog : null,
    addEventListener: (type: string, listener: (event: Event) => void) => listeners.set(type, listener),
  };
  renderMainWorkspace(container as unknown as HTMLElement, createWorkspaceState(
    { tenant_id: "tenant-1", project_id: "project-1", revision: 3 },
    "en",
  ));
  const target = { dataset: { shellCommand: "Columns" }, closest: () => target };
  listeners.get("click")?.({ target } as unknown as Event);
  assert.equal(opened, true);
});

test("Bottom Layout Options menu command opens the Activity Details tab selector", () => {
  const listeners = new Map<string, (event: Event) => void>();
  let opened = false;
  const trigger = { click: () => { opened = true; } };
  const container = {
    innerHTML: "",
    querySelectorAll: () => [],
    querySelector: (selector: string) => selector === "[data-activity-details-options-open]" ? trigger : null,
    addEventListener: (type: string, listener: (event: Event) => void) => listeners.set(type, listener),
  };
  renderMainWorkspace(container as unknown as HTMLElement, createWorkspaceState(
    { tenant_id: "tenant-1", project_id: "project-1", revision: 3 },
    "en",
  ));
  const target = { dataset: { shellCommand: "Bottom Layout Options" }, closest: () => target };
  listeners.get("click")?.({ target } as unknown as Event);
  assert.equal(opened, true);
});

test("Bars and Bar Chart Options commands open their own dialogs", () => {
  const listeners = new Map<string, (event: Event) => void>();
  let barsOpened = false;
  let optionsOpened = false;
  const barsDialog = { showModal: () => { barsOpened = true; } };
  const optionsDialog = { showModal: () => { optionsOpened = true; } };
  const container = {
    innerHTML: "",
    querySelectorAll: () => [],
    querySelector: (selector: string) => selector === "[data-bars-dialog]" ? barsDialog : selector === "[data-bar-chart-options-dialog]" ? optionsDialog : null,
    addEventListener: (type: string, listener: (event: Event) => void) => listeners.set(type, listener),
  };
  renderMainWorkspace(container as unknown as HTMLElement, createWorkspaceState({ tenant_id: "tenant-1", project_id: "project-1", revision: 3 }, "en"));
  const barsTarget = { dataset: { shellCommand: "Bars" }, closest: () => barsTarget };
  listeners.get("click")?.({ target: barsTarget } as unknown as Event);
  assert.equal(barsOpened, true);
  const optionsTarget = { dataset: { shellCommand: "Bar Chart Options" }, closest: () => optionsTarget };
  listeners.get("click")?.({ target: optionsTarget } as unknown as Event);
  assert.equal(optionsOpened, true);
});

test("Bars dialog tabs switch the visible configuration panel", () => {
  const listeners = new Map<string, (event: Event) => void>();
  const buttons = ["style", "settings", "labels"].map((barsTab) => ({
    dataset: { barsTab },
    setAttribute: (_name: string, _value: string) => {},
    classList: { toggle: (_name: string, _active: boolean) => {} },
  }));
  const panels = ["style", "settings", "labels"].map((barsPanel) => ({ dataset: { barsPanel }, hidden: true }));
  const container = {
    innerHTML: "",
    querySelectorAll: (selector: string) => selector === "[data-bars-tab]" ? buttons : selector === "[data-bars-panel]" ? panels : [],
    querySelector: () => null,
    addEventListener: (type: string, listener: (event: Event) => void) => listeners.set(type, listener),
  };
  renderMainWorkspace(container as unknown as HTMLElement, createWorkspaceState({ tenant_id: "tenant-1", project_id: "project-1", revision: 3 }, "en"));
  const target = { dataset: { barsTab: "labels" }, closest: () => target };
  listeners.get("click")?.({ target } as unknown as Event);
  assert.equal(panels.find((panel) => panel.dataset.barsPanel === "labels")?.hidden, false);
  assert.equal(panels.find((panel) => panel.dataset.barsPanel === "style")?.hidden, true);
});



test("Filter By opens a filter dialog and applies the current activity search", () => {
  const listeners = new Map<string, (event: Event) => void>();
  const calls: string[] = [];
  let closed = false;
  const dialog = { showModal: () => {}, close: () => { closed = true; } };
  const search = { value: "concrete" };
  const container = {
    innerHTML: "",
    querySelectorAll: () => [],
    querySelector: (selector: string) => selector === "[data-filters-dialog]" ? dialog : selector === "[data-filters-search]" ? search : null,
    addEventListener: (type: string, listener: (event: Event) => void) => listeners.set(type, listener),
  };
  renderMainWorkspace(container as unknown as HTMLElement, createWorkspaceState({ tenant_id: "tenant-1", project_id: "project-1", revision: 3 }, "en"), {
    onActivityFilterChange: (value) => calls.push(value),
  });
  const target = { dataset: { filtersApply: "" }, closest: () => target };
  listeners.get("click")?.({ target } as unknown as Event);
  assert.deepEqual(calls, ["concrete"]);
  assert.equal(closed, true);
});
