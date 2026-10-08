import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { createP6PresentationAdapter } from "./p6-presentation-adapter.ts";

const fixture = JSON.parse(readFileSync(new URL("../../../shared/contracts/p6-presentation-parity.fixture.json", import.meta.url), "utf8"));

test("web consumes the canonical P6 presentation contract", () => {
  const result = createP6PresentationAdapter().validate(fixture);
  assert.deepEqual(result, fixture);
  assert.equal(result.registry.status, "seeded_not_certified");
});

test("web normalizes layout order through the shared contract", () => {
  const layout = createP6PresentationAdapter().normalizeLayout({
    ...fixture.layout,
    columns: [...fixture.layout.columns].reverse(),
  });
  assert.deepEqual(layout.columns.map((column) => column.field_id), ["activity.total_float","activity.duration","activity.activity_id"]);
  assert.deepEqual(layout.columns.map((column) => column.order), [0,1,2]);
});
