import test from "node:test";
import assert from "node:assert/strict";
import { getP6FieldEditorDescriptor, getP6UdfEditorDescriptor } from "./p6-field-editor.js";
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

test("enum fields do not invent option values without authoritative metadata", () => {
  const descriptor = getP6FieldEditorDescriptor(field({ data_type: "enum", nullable: false }));
  assert.equal(descriptor.control, "text");
  assert.equal(descriptor.editable, true);
});

test("UDF enum fields use only authoritative allowed values", () => {
  const source = {
    udf_id: "activity.status",
    subject_area: "Activity",
    display_name: "Status",
    data_type: "enum" as const,
    writable: true,
    nullable: false,
    unit: null,
    allowed_values: ["Planned", "In Progress", "Complete"] as const,
  };
  const descriptor = getP6UdfEditorDescriptor(source);
  assert.equal(descriptor.control, "select");
  assert.deepEqual(descriptor.allowedValues, ["Planned", "In Progress", "Complete"]);
  (descriptor.allowedValues as string[]).push("Injected");
  assert.deepEqual(source.allowed_values, ["Planned", "In Progress", "Complete"]);
});
