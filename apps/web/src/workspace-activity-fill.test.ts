import assert from "node:assert/strict";
import test from "node:test";

import {
  FILLABLE_COLUMNS,
  buildFillDownPayload,
  fillableColumnFor,
  sourceValueFor,
} from "./workspace-activity-fill.js";

function column(id: string) {
  const found = FILLABLE_COLUMNS.find((entry) => entry.columnId === id);
  assert.ok(found);
  return found;
}

test("only visible, editable columns qualify for Fill Down", () => {
  assert.equal(fillableColumnFor("duration", ["duration", "activity_name"])?.apiField, "duration_value");
  assert.equal(fillableColumnFor("duration", ["activity_name"]), null);
  assert.equal(fillableColumnFor("start", ["start"]), null);
  assert.equal(fillableColumnFor(null, ["duration"]), null);
});

test("text, decimal, percent and enum values are validated before any write", () => {
  assert.deepEqual(buildFillDownPayload(column("activity_name"), "  Piling  "), { name: "Piling" });
  assert.deepEqual(buildFillDownPayload(column("duration"), "12.5"), { duration_value: "12.5" });
  assert.deepEqual(buildFillDownPayload(column("progress"), 40), { percent_complete: 40 });
  assert.deepEqual(buildFillDownPayload(column("status"), "In Progress"), { status: "In Progress" });
  assert.throws(() => buildFillDownPayload(column("activity_name"), "   "), /FILL_DOWN_EMPTY_VALUE/);
  assert.throws(() => buildFillDownPayload(column("duration"), "2d"), /FILL_DOWN_INVALID_NUMBER/);
  assert.throws(() => buildFillDownPayload(column("progress"), 120), /FILL_DOWN_INVALID_PERCENT/);
  assert.throws(() => buildFillDownPayload(column("status"), "Paused"), /FILL_DOWN_INVALID_OPTION/);
});

test("the source value comes from the authoritative Activity Master DTO", () => {
  const dto = { activity: { name: "Piling", duration_value: "7", percent_complete: 25 } };
  assert.equal(sourceValueFor(column("activity_name"), dto), "Piling");
  assert.equal(sourceValueFor(column("duration"), dto), "7");
  assert.equal(sourceValueFor(column("progress"), dto), 25);
  assert.equal(sourceValueFor(column("status"), dto), undefined);
});
