import test from "node:test";
import assert from "node:assert/strict";
import {
  P6_INTERCHANGE_CONTRACT_VERSION,
  assertP6InterchangeTypedValue,
  validateP6InterchangeEnvelope,
  validateP6InterchangeTypedValue,
} from "./p6-interchange-contract.js";

const context = { tenant_id: "tenant-1", project_id: "project-1", revision: 7 };

test("preserves Decimal as string and validates duration payload", () => {
  assert.equal(
    validateP6InterchangeTypedValue({
      data_type: "decimal",
      value: "1234.50",
      unit: "cost",
      currency: "USD",
    }),
    true,
  );
  assert.equal(
    validateP6InterchangeTypedValue({
      data_type: "duration",
      value: { value: "2.50", unit: "working-day" },
      unit: "working-day",
      currency: null,
    }),
    true,
  );
});

test("requires typed ISO date and timezone-aware datetime", () => {
  assert.equal(validateP6InterchangeTypedValue({
    data_type: "date",
    value: "2026-09-28",
    unit: null,
    currency: null,
  }), true);
  assert.equal(validateP6InterchangeTypedValue({
    data_type: "datetime",
    value: "2026-09-28T10:00:00Z",
    unit: null,
    currency: null,
  }), true);
  assert.equal(validateP6InterchangeTypedValue({
    data_type: "datetime",
    value: "2026-09-28T10:00:00",
    unit: null,
    currency: null,
  }), false);
});

test("rejects lossy or untyped numeric representations", () => {
  assert.equal(validateP6InterchangeTypedValue({
    data_type: "decimal",
    value: 12.5,
    unit: null,
    currency: null,
  }), false);
  assert.equal(validateP6InterchangeTypedValue({
    data_type: "integer",
    value: 1.5,
    unit: null,
    currency: null,
  }), false);
});

test("requires project context on the shared envelope", () => {
  const envelope = {
    contract_version: P6_INTERCHANGE_CONTRACT_VERSION,
    context,
    value: { data_type: "decimal", value: "10.00", unit: null, currency: null },
  };
  assert.equal(validateP6InterchangeEnvelope(envelope, validateP6InterchangeTypedValue), true);
  assert.deepEqual(assertP6InterchangeTypedValue(envelope.value).value, "10.00");
});
