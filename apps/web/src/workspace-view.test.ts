import assert from "node:assert/strict";
import test from "node:test";

import { renderMainWorkspace } from "./workspace-view.js";
import type { WorkspaceMenuKey } from "./workspace-model.js";
import { createWorkspaceState, setP6Presentation, withActivities, withRelationships, withWbsNodes } from "./workspace-model.js";

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
  for (const menu of ["project", "schedule", "progress", "resources", "cost", "documents", "reports", "control", "settings"] as const) {
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

  assert.deepEqual(registrations, ["input", "submit", "click", "keydown", "change"]);
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
  assert.match(container.innerHTML, /<table role="grid" aria-label="Activity Grid" aria-multiselectable="false">/);
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

test("empty and preview-only modules show an explicit truthful surface", () => {
  const reports = render("en", "reports");
  assert.match(reports, /data-workspace-menu="reports"/);
  assert.match(reports, /Reports &amp; print/);
  assert.match(reports, /not available in this preview yet/);

  const progress = render("fa", "progress");
  assert.match(progress, /data-workspace-menu="progress"/);
  assert.match(progress, /داشبورد و نمودارهای اختصاصی پیشرفت/);

  const documents = render("en", "documents");
  assert.match(documents, /No project documents have been added or linked yet/);

  const settings = render("en", "settings");
  assert.match(settings, /id="cp-settings-panel"[^>]*data-workspace-menu="settings"/);
});

test("schedule surface places the activity grid beside the Gantt in a shared classic split", () => {
  const html = render("en", "schedule");
  assert.match(html, /class="cp-schedule-split"[^>]*data-workspace-menu="schedule"/);
  const splitStart = html.indexOf('class="cp-schedule-split"');
  const gridStart = html.indexOf('id="cp-activity-grid"', splitStart);
  const ganttStart = html.indexOf('id="cp-gantt"', gridStart);
  const optionsStart = html.indexOf('id="cp-schedule-options"', ganttStart);
  assert.ok(splitStart >= 0 && gridStart > splitStart && ganttStart > gridStart && optionsStart > ganttStart);
  assert.match(html, /<details class="cp-editor-details cp-activity-entry-details">/);
  assert.match(html, /<summary>Add activity<\/summary>/);
  assert.match(html, /data-activity-create-form/);
  assert.match(html, /<details class="cp-editor-details cp-wbs-entry-details">/);
});

