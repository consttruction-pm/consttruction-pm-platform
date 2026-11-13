import test from "node:test";
import assert from "node:assert/strict";
import {
  addAllAvailableColumns,
  addAvailableColumn,
  availableColumns,
  columnHasCustomTitle,
  copyColumnsFrom,
  createP6ColumnsDraft,
  draftToLayout,
  moveSelectedColumn,
  removeAllColumns,
  removeSelectedColumn,
  resetDraftColumns,
  restoreDefaultTitle,
  selectAvailableColumn,
  selectSelectedColumn,
  setColumnSearch,
  setColumnSubjectArea,
  updateColumnDraft,
} from "./p6-columns-dialog.js";
import type { FieldRegistry, LayoutDefinition } from "./p6-field-layout-foundation.js";

const registry: FieldRegistry = {
  registry_version: "p6-field-registry.v1",
  reference_product: "Oracle Primavera P6 Professional",
  reference_version: "P6-compatible",
  status: "active",
  fields: [
    {
      field_id: "activity.id",
      subject_area: "Activity",
      p6_field: "Id",
      display_name: "Activity ID",
      data_type: "string",
      writable: true,
      computed: false,
      disposition: "standard",
    },
    {
      field_id: "activity.name",
      subject_area: "Activity",
      p6_field: "Name",
      display_name: "Activity Name",
      data_type: "string",
      writable: true,
      computed: false,
      disposition: "standard",
    },
    {
      field_id: "activity.planned_duration",
      subject_area: "Activity",
      p6_field: "PlannedDuration",
      display_name: "Original Duration",
      data_type: "duration",
      writable: true,
      computed: false,
      disposition: "standard",
    },
    {
      field_id: "wbs.code",
      subject_area: "WBS",
      p6_field: "Code",
      display_name: "WBS Code",
      data_type: "string",
      writable: true,
      computed: false,
      disposition: "standard",
    },
  ],
};

function layout(): LayoutDefinition {
  return {
    schema_version: "p6-layout.v1",
    scope: "project",
    view_id: "activity",
    revision: 4,
    columns: [
      { field_id: "activity.id", visible: true, order: 0, label: "ID", width: 120, alignment: "start", pinned: false, frozen: false },
      { field_id: "activity.name", visible: true, order: 1, width: 260, alignment: "start", pinned: false, frozen: false },
    ],
  };
}

test("available columns filter by search and subject area", () => {
  let draft = createP6ColumnsDraft(registry, layout());

  assert.deepEqual(availableColumns(draft).map((field) => field.field_id), [
    "activity.planned_duration",
    "wbs.code",
  ]);

  draft = setColumnSearch(draft, "duration");
  assert.deepEqual(availableColumns(draft).map((field) => field.field_id), ["activity.planned_duration"]);

  draft = setColumnSearch(draft, "");
  draft = setColumnSubjectArea(draft, "WBS");
  assert.deepEqual(availableColumns(draft).map((field) => field.field_id), ["wbs.code"]);
});

test("adds one or all columns and keeps an explicit selection", () => {
  let draft = createP6ColumnsDraft(registry, layout());
  draft = selectAvailableColumn(draft, "wbs.code");
  draft = addAvailableColumn(draft, "wbs.code");

  assert.deepEqual(draft.columns.map((column) => column.field_id), [
    "activity.id",
    "activity.name",
    "wbs.code",
  ]);
  assert.equal(draft.selected_selection, "wbs.code");
  assert.equal(draft.available_selection, null);
  assert.equal(draft.columns[2]?.visible, true);

  draft = selectSelectedColumn(draft, "activity.id");
  draft = addAllAvailableColumns(draft);
  assert.deepEqual(draft.columns.map((column) => column.field_id), [
    "activity.id",
    "activity.name",
    "wbs.code",
    "activity.planned_duration",
  ]);
  assert.deepEqual(draft.columns.map((column) => column.order), [0, 1, 2, 3]);
});

test("never removes the last selected column", () => {
  let draft = createP6ColumnsDraft(registry, layout());

  draft = removeSelectedColumn(draft, "activity.name");
  assert.deepEqual(draft.columns.map((column) => column.field_id), ["activity.id"]);
  assert.throws(() => removeSelectedColumn(draft, "activity.id"), /LAST_COLUMN_REQUIRED/);
  assert.throws(() => removeAllColumns(draft), /LAST_COLUMN_REQUIRED/);
});

test("remove all keeps one display column and reports that column as selected", () => {
  let draft = createP6ColumnsDraft(registry, layout());
  draft = addAllAvailableColumns(draft);
  draft = removeAllColumns(draft);

  assert.deepEqual(draft.columns.map((column) => column.field_id), ["activity.id"]);
  assert.equal(draft.selected_selection, "activity.id");
  assert.equal(draft.columns[0]?.order, 0);
});

test("moves a selected column within the display order", () => {
  let draft = createP6ColumnsDraft(registry, layout());
  draft = selectSelectedColumn(draft, "activity.name");
  draft = moveSelectedColumn(draft, "activity.name", -1);

  assert.deepEqual(draft.columns.map((column) => column.field_id), ["activity.name", "activity.id"]);
  assert.deepEqual(draft.columns.map((column) => column.order), [0, 1]);

  assert.deepEqual(
    moveSelectedColumn(draft, "activity.name", -1).columns.map((column) => column.field_id),
    ["activity.name", "activity.id"],
  );
});

test("edit column keeps the default title visible and restores it on Default", () => {
  let draft = createP6ColumnsDraft(registry, layout());

  draft = updateColumnDraft(draft, "activity.name", {
    label: "Name",
    width: 300,
    alignment: "center",
  });
  const column = draft.columns[1];
  assert.ok(column);
  assert.equal(column.label, "Name");
  assert.equal(column.width, 300);
  assert.equal(column.alignment, "center");
  assert.equal(columnHasCustomTitle(draft, column), true);

  draft = restoreDefaultTitle(draft, "activity.name");
  const restored = draft.columns[1];
  assert.ok(restored);
  assert.equal(restored.label, undefined);
  assert.equal(columnHasCustomTitle(draft, restored), false);
  // Width and alignment are separate Edit Column fields and survive Default.
  assert.equal(restored.width, 300);
});

test("reset replaces the draft with server defaults that exist in the registry", () => {
  const draft = createP6ColumnsDraft(registry, layout());

  const reset = resetDraftColumns(draft, [
    { field_id: "activity.name", visible: true, order: 0, width: 280, alignment: "start", pinned: false, frozen: false },
    { field_id: "missing.field", visible: true, order: 1, width: 100, alignment: "start", pinned: false, frozen: false },
    { field_id: "activity.id", visible: true, order: 2, width: 90, alignment: "start", pinned: false, frozen: false },
  ]);

  assert.deepEqual(reset.columns.map((column) => column.field_id), ["activity.name", "activity.id"]);
  assert.deepEqual(reset.columns.map((column) => column.order), [0, 1]);
  assert.equal(reset.selected_selection, "activity.name");
});

test("add all only adds the currently listed available columns", () => {
  let draft = createP6ColumnsDraft(registry, layout());
  draft = setColumnSubjectArea(draft, "WBS");
  draft = addAllAvailableColumns(draft);

  assert.deepEqual(draft.columns.map((column) => column.field_id), [
    "activity.id",
    "activity.name",
    "wbs.code",
  ]);
  assert.equal(draft.available_selection, null);
});

test("copy from replaces the draft with a saved layout's known columns", () => {
  const draft = createP6ColumnsDraft(registry, layout());
  const copied = copyColumnsFrom(draft, [
    { field_id: "wbs.code", visible: true, order: 3, label: "WBS", width: 150, alignment: "center", pinned: true, frozen: false },
    { field_id: "missing.field", visible: true, order: 0, width: 90, alignment: "start", pinned: false, frozen: false },
    { field_id: "activity.planned_duration", visible: false, order: 1, width: 120, alignment: "end", pinned: false, frozen: false },
  ]);

  assert.deepEqual(copied.columns.map((column) => column.field_id), [
    "activity.planned_duration",
    "wbs.code",
  ]);
  assert.deepEqual(copied.columns.map((column) => column.order), [0, 1]);
  assert.equal(copied.columns[1]?.label, "WBS");
  assert.equal(copied.columns[1]?.pinned, true);
  assert.equal(copied.columns[0]?.visible, false);
  assert.equal(copied.selected_selection, "activity.planned_duration");
  assert.throws(
    () => copyColumnsFrom(draft, [{ field_id: "missing.field", visible: true, order: 0, width: 90, alignment: "start", pinned: false, frozen: false }]),
    /NO_SOURCE_COLUMNS/,
  );
});

test("draft to layout normalizes order without inventing a revision", () => {
  let draft = createP6ColumnsDraft(registry, layout());
  draft = updateColumnDraft(draft, "activity.name", { width: 320 });
  draft = moveSelectedColumn(draft, "activity.name", -1);

  const result = draftToLayout(draft, layout());
  assert.equal(result.revision, 4);
  assert.equal(result.scope, "project");
  assert.deepEqual(result.columns.map((column) => column.field_id), ["activity.name", "activity.id"]);
  assert.deepEqual(result.columns.map((column) => column.order), [0, 1]);
  assert.equal(result.columns[0]?.width, 320);
});
