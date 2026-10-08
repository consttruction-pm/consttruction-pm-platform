import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import {
  P6_PRESENTATION_CONTRACT_ID,
  P6_PRESENTATION_CONTRACT_VERSION,
  createP6PresentationAdapter,
  validateP6PresentationBundle,
  reorderFields,
} from "./p6-presentation-contract.ts";

const fixture = JSON.parse(
  readFileSync(
    new URL("../../../shared/contracts/p6-presentation-parity.fixture.json", import.meta.url),
    "utf8",
  ),
);

test("canonical P6 presentation contract validates one shared fixture", () => {
  const adapter = createP6PresentationAdapter();
  assert.equal(P6_PRESENTATION_CONTRACT_ID, "constructionpm://contracts/p6-presentation/v1");
  assert.equal(P6_PRESENTATION_CONTRACT_VERSION, "1.0");
  assert.deepEqual(adapter.validate(fixture), fixture);
  assert.equal(fixture.registry.status, "seeded_not_certified");
});

test("canonical P6 presentation contract rejects layout fields absent from registry", () => {
  const invalid = structuredClone(fixture);
  invalid.layout.columns[0].field_id = "activity.unknown";
  assert.throws(() => validateP6PresentationBundle(invalid), /P6_COLUMN_FIELD_NOT_IN_REGISTRY/);
});

test("canonical P6 presentation contract preserves formula dependency and result type", () => {
  const result = validateP6PresentationBundle(fixture).formula_authoritative;
  assert.deepEqual(result.dependencies.field_ids, ["activity.duration"]);
  assert.equal(result.result_type.data_type, "duration");
});

test("reorderFields rejects duplicate field IDs", () => {
  assert.throws(
    () => reorderFields(fixture.layout, ["activity.activity_id", "activity.activity_id", "activity.total_float"]),
    /INVALID_LAYOUT_ORDER/,
  );
});
