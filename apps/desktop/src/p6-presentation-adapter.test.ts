import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { createP6PresentationAdapter } from "./p6-presentation-adapter.ts";

const fixture = JSON.parse(readFileSync(new URL("../../../shared/contracts/p6-presentation-parity.fixture.json", import.meta.url), "utf8"));

test("desktop consumes the same canonical P6 presentation fixture", () => {
  const result = createP6PresentationAdapter().validate(fixture);
  assert.deepEqual(result, fixture);
  assert.equal(result.registry.status, "seeded_not_certified");
});

test("desktop preserves authoritative formula result shape", () => {
  const result = createP6PresentationAdapter().validate(fixture);
  assert.deepEqual(result.formula_authoritative.dependencies.field_ids, ["activity.duration"]);
  assert.equal(result.formula_authoritative.result_type.data_type, "duration");
});
