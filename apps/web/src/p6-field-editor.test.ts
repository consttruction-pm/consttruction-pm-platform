import test from "node:test";
import assert from "node:assert/strict";
import { getP6FieldEditorDescriptor } from "./p6-field-editor.js";
import type { P6Field } from "./p6-field-layout-foundation.js";

function field(overrides: Partial<P6Field> = {}): P6Field {
  return {
    field_id: "activity-name",
    subject_area: "activity",
    p6_field: "Activity Name",
    display_name: "Activity Name",
    data_type: "string",
    writable: true,
    computed: false,
    disposition: "standard",
    nullable: true,
    allowed_values: null,
    ...overrides,
  };
}

test("maps writable nullable standard fields to an editable typed descriptor", () => {
  assert.deepEqual(getP6FieldEditorDescriptor(field()), {
    fieldId: "activity-name",
    label: "Activity Name",
    dataType: "string",
    control: "text",
    editable: true,
    nullable: true,
    computed: false,
    writable: true,
    allowedValues: null,
  });
});

test("computed fields remain read-only even when metadata marks them writable", () => {
  const descriptor = getP6FieldEditorDescriptor(
    field({ field_id: "remaining-duration", data_type: "duration", computed: true }),
  );
  assert.equal(descriptor.control, "duration");
  assert.equal(descriptor.editable, false);
  assert.equal(descriptor.computed, true);
  assert.equal(descriptor.writable, true);
});

test("read-only numeric fields keep authoritative type metadata", () => {
  const descriptor = getP6FieldEditorDescriptor(
    field({ field_id: "total-cost", data_type: "cost", writable: false, nullable: false }),
  );
  assert.equal(descriptor.control, "number");
  assert.equal(descriptor.dataType, "cost");
  assert.equal(descriptor.editable, false);
  assert.equal(descriptor.nullable, false);
});

test("boolean and date fields select typed presentation controls", () => {
  assert.equal(getP6FieldEditorDescriptor(field({ data_type: "boolean" })).control, "boolean");
  assert.equal(getP6FieldEditorDescriptor(field({ data_type: "datetime" })).control, "date");
});

test("enum fields do not invent option values before authoritative allowed-values metadata exists", () => {
  const descriptor = getP6FieldEditorDescriptor(field({ data_type: "enum", nullable: false }));
  assert.equal(descriptor.control, "text");
  assert.equal(descriptor.editable, true);
  assert.equal(descriptor.nullable, false);
});


test("enum fields preserve authoritative allowed values and select control", () => {
  const source = field({ data_type: "enum", allowed_values: ["A", "B"] });
  const descriptor = getP6FieldEditorDescriptor(source);
  assert.equal(descriptor.control, "select");
  assert.deepEqual(descriptor.allowedValues, ["A", "B"]);
  (descriptor.allowedValues as string[]).push("C");
  assert.deepEqual(source.allowed_values, ["A", "B"]);
});
