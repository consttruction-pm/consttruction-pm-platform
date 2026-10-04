import assert from "node:assert/strict";
import test from "node:test";

import { renderMainWorkspace } from "./workspace-view.js";
import type { WorkspaceMenuKey } from "./workspace-model.js";
import { createWorkspaceState } from "./workspace-model.js";

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
  const container: RenderContainer = { innerHTML: "", querySelectorAll: () => [] };
  const listeners = new Map<string, () => void>();
  const buttons = ["schedule", "reports"].map((menu) => ({
    dataset: { menu },
    addEventListener: (_event: string, listener: () => void) => listeners.set(menu, listener),
  }));
  container.querySelectorAll = ((selector: string) => selector === "[data-menu]" ? buttons as unknown as HTMLElement[] : []) as RenderContainer["querySelectorAll"];
  renderMainWorkspace(container as unknown as HTMLElement, state, {
    onMenuSelect: (menu) => selected.push(menu),
  });
  listeners.get("reports")?.();
  assert.deepEqual(selected, ["reports"]);
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
  assert.match(container.innerHTML, /aria-label="انتخاب‌گر فیلد P6"/);
  assert.match(container.innerHTML, /<strong>فیلدها<\/strong>/);
  assert.match(container.innerHTML, /title="حذف"/);
  assert.doesNotMatch(container.innerHTML, /aria-label="Main Menu"/);
  assert.doesNotMatch(container.innerHTML, /P6 Field Chooser/);
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
  const listeners = new Map<string, () => void>();
  const widthButton = {
    dataset: { p6FieldWidth: "activity.activity_id", p6FieldWidthDelta: "increase" },
    addEventListener: (_event: string, listener: () => void) => listeners.set("width", listener),
  };
  const container: RenderContainer = {
    innerHTML: "",
    querySelectorAll: ((selector: string) =>
      selector === "[data-p6-field-width]" ? [widthButton as unknown as HTMLElement] : []) as RenderContainer["querySelectorAll"],
  };

  renderMainWorkspace(container as unknown as HTMLElement, state, {
    onP6FieldWidthChange: (fieldId, width) => changes.push({ fieldId, width }),
  });
  listeners.get("width")?.();

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
  assert.match(container.innerHTML, /title="Show"/);
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
  const listeners = new Map<string, (event?: KeyboardEvent) => void>();
  const ganttRow = {
    dataset: { ganttActivityId: "A-1" },
    addEventListener: (event: string, listener: (event?: KeyboardEvent) => void) => listeners.set(event, listener),
  };
  const container: RenderContainer = {
    innerHTML: "",
    querySelectorAll: ((selector: string) =>
      selector === "[data-gantt-activity-id]" ? [ganttRow as unknown as HTMLElement] : []) as RenderContainer["querySelectorAll"],
  };
  renderMainWorkspace(container as unknown as HTMLElement, state, {
    onGanttActivitySelect: (activityId) => selected.push(activityId),
  });
  listeners.get("click")?.();
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
  assert.match(container.innerHTML, /<td role="gridcell">A-1<\/td>/);
});
