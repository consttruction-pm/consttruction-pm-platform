import test from "node:test";
import assert from "node:assert/strict";
import {
  addColumn,
  createDefaultLayout,
  migrateWorkspaceLayout,
  reorderColumn,
  removeColumn,
  setColumnLabel,
  setColumnState,
  MemoryWorkspaceLayoutStore,
} from "./workspace-layout.js";
import type { P6FieldCatalogEntry } from "./p6-field-registry-client.js";

const catalog: readonly P6FieldCatalogEntry[] = [
  { id: "activity_id", source: "standard", subjectArea: "activity", label: "Activity ID", dataType: "string", writable: false, computed: false, unit: null, nullable: null, allowedValues: [], p6Field: "ActivityId", filterable: true, orderable: true },
  { id: "duration", source: "standard", subjectArea: "activity", label: "Duration", dataType: "duration", writable: false, computed: true, unit: "day", nullable: null, allowedValues: [], p6Field: "Duration", filterable: true, orderable: true },
  { id: "progress", source: "standard", subjectArea: "activity", label: "Progress", dataType: "percentage", writable: false, computed: true, unit: "%", nullable: null, allowedValues: [], p6Field: "Progress", filterable: true, orderable: true },
];

test("layout supports add/remove/reorder and column presentation state", () => {
  let layout = createDefaultLayout("activity-default", "activity", "project", 3, catalog);
  layout = removeColumn(layout, "duration");
  layout = addColumn(layout, catalog[1]);
  layout = reorderColumn(layout, "progress", 0);
  layout = setColumnLabel(layout, "progress", "Actual %");
  layout = setColumnState(layout, "progress", { visible: true, pinned: true, frozen: true, width: 150, alignment: "end" });

  assert.equal(layout.columns[0].fieldId, "progress");
  assert.equal(layout.columns[0].labelOverride, "Actual %");
  assert.equal(layout.columns[0].pinned, true);
  assert.equal(layout.columns[0].frozen, true);
  assert.equal(layout.columns[0].width, 150);
});

test("migration drops unknown fields and adds newly available catalog fields hidden", () => {
  const migrated = migrateWorkspaceLayout({
    contract_version: "workspace-layout.legacy",
    layout_id: "activity-user",
    subject_area: "activity",
    scope: "user",
    columns: [
      { field_id: "activity_id", visible: true, order: 4, width: 20 },
      { field_id: "removed_field", visible: true, order: 0, width: 500 },
    ],
  }, catalog, 4);

  assert.equal(migrated.revision, 4);
  assert.equal(migrated.columns.length, 3);
  assert.equal(migrated.columns.some((column) => column.fieldId === "removed_field"), false);
  assert.equal(migrated.columns.find((column) => column.fieldId === "progress")?.visible, false);
  assert.equal(migrated.columns.find((column) => column.fieldId === "activity_id")?.width, 48);
});

test("layout store round-trips a saved layout", () => {
  const store = new MemoryWorkspaceLayoutStore();
  const layout = createDefaultLayout("activity-default", "activity", "global", 0, catalog);
  store.save("global:activity", layout);
  assert.deepEqual(store.load("global:activity"), layout);
});

test("layout rejects fields from another subject area", () => {
  const layout = createDefaultLayout("activity-default", "activity", "project", 0, catalog);
  assert.throws(
    () => addColumn(layout, {
      ...catalog[0],
      id: "wbs.code",
      subjectArea: "WBS",
    }),
    /FIELD_SUBJECT_AREA_MISMATCH/,
  );
});

test("layout rejects unknown future contract versions", () => {
  assert.throws(
    () => migrateWorkspaceLayout({
      contract_version: "workspace-layout.v99",
      layout_id: "activity-user",
      subject_area: "activity",
      scope: "user",
      columns: [],
    }, catalog, 4),
    /UNSUPPORTED_WORKSPACE_LAYOUT_VERSION/,
  );
});
