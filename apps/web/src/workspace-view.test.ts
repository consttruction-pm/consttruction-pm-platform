import assert from "node:assert/strict";
import test from "node:test";

import { renderMainWorkspace } from "./workspace-view.js";
import type { WorkspaceMenuKey } from "./workspace-model.js";
import { createWorkspaceState, setP6Presentation } from "./workspace-model.js";

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
    addEventListener: (_event, listener) => { clickListener = listener; },
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


test("P6 chooser exposes hidden authoritative fields", () => {
  const state = { ...createWorkspaceState({ tenant_id: "tenant-1", project_id: "project-1", revision: 3 }, "en"), p6FieldRegistry: { registry_version: "p6-field-registry.v1", reference_product: "Oracle Primavera P6 Professional", reference_version: "26", status: "active", fields: [{ field_id: "activity.activity_id", subject_area: "activity", p6_field: "Activity ID", display_name: "Activity ID", data_type: "string", writable: false, computed: false, disposition: "supported" }] } as const, p6Layout: { schema_version: "p6-layout.v1", scope: "project", view_id: "activity-grid", revision: 1, columns: [{ field_id: "activity.activity_id", visible: false, order: 0, width: 120, alignment: "start", pinned: false, frozen: false }] } as const };
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
