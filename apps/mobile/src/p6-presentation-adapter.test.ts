import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { createP6PresentationAdapter } from "./p6-presentation-adapter.ts";

const fixture = JSON.parse(readFileSync(new URL("../../../shared/contracts/p6-presentation-parity.fixture.json", import.meta.url), "utf8"));

test("mobile consumes the same canonical P6 presentation fixture", () => {
  const result = createP6PresentationAdapter().validate(fixture);
  assert.deepEqual(result, fixture);
  assert.equal(result.registry.status, "seeded_not_certified");
});

test("mobile rejects presentation contract version mismatches", () => {
  const invalid = structuredClone(fixture);
  invalid.contract_version = "2.0";
  assert.throws(() => createP6PresentationAdapter().validate(invalid), /INVALID_P6_PRESENTATION_CONTRACT_VERSION/);
});
