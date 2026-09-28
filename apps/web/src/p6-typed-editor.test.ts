import test from "node:test";
import assert from "node:assert/strict";
import { parseTypedEditorValue, validateTypedEditorValue } from "./p6-typed-editor.js";
import type { P6FieldCatalogEntry } from "./p6-field-registry-client.js";

test("typed editor parses duration as a number without doing scheduling", () => {
  const field: P6FieldCatalogEntry = {
    id: "duration", source: "standard", subjectArea: "activity", label: "Duration",
    dataType: "duration", writable: true, computed: false, unit: "day", filterable: true, orderable: true,
  };
  const value = parseTypedEditorValue(field, "5");
  validateTypedEditorValue(field, value);
  assert.deepEqual(value, { kind: "duration", value: 5 });
});

test("percentage editor rejects values outside shared type range", () => {
  const field: P6FieldCatalogEntry = {
    id: "progress", source: "standard", subjectArea: "activity", label: "Progress",
    dataType: "percentage", writable: true, computed: false, unit: "%", filterable: true, orderable: true,
  };
  assert.throws(() => validateTypedEditorValue(field, { kind: "number", value: 101 }), /INVALID_PERCENTAGE/);
});

test("computed fields cannot be edited by the client", () => {
  const field: P6FieldCatalogEntry = {
    id: "finish", source: "standard", subjectArea: "activity", label: "Finish",
    dataType: "date", writable: true, computed: true, unit: null, filterable: true, orderable: true,
  };
  assert.throws(() => parseTypedEditorValue(field, "2026-09-28"), /FIELD_NOT_EDITABLE/);
});
