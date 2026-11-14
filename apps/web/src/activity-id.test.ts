import assert from "node:assert/strict";
import test from "node:test";

import { computeNextActivityId, stripActivityIdAffixes } from "./activity-id.js";

const baseDefaults = {
  prefix: "",
  suffix: "",
  increment: 10,
  incrementActivityId: false,
};

test("next activity ID increments the highest existing number with prefix and suffix", () => {
  assert.equal(
    computeNextActivityId(["A100", "A110", "A090"], {
      ...baseDefaults,
      prefix: "A",
      suffix: "-P1",
    }),
    "A120-P1",
  );
});

test("next activity ID applies the stored increment and pads the numeric tail", () => {
  assert.equal(
    computeNextActivityId(["T-0008"], { ...baseDefaults, prefix: "T-", increment: 5 }, null),
    "T-0013",
  );
  assert.equal(
    computeNextActivityId(["W-9"], { ...baseDefaults, prefix: "W-", increment: 3 }, null),
    "W-12",
  );
});

test("next activity ID uses the selected activity only when the option is enabled", () => {
  const ids = ["A10", "A20"];
  assert.equal(
    computeNextActivityId(ids, baseDefaults, "A10"),
    "A30",
    "disabled option ignores the selection and uses the highest ID",
  );
  assert.equal(
    computeNextActivityId(
      ids,
      { ...baseDefaults, incrementActivityId: true },
      "A10",
    ),
    "A20",
    "enabled option starts from the selected activity",
  );
  assert.equal(
    computeNextActivityId(
      ids,
      { ...baseDefaults, incrementActivityId: true },
      "A99",
    ),
    "A109",
    "the selected activity is authoritative even beyond the current maximum",
  );
});

test("a new project starts from the increment and an ID without digits appends it", () => {
  assert.equal(computeNextActivityId([], baseDefaults), "10");
  assert.equal(
    computeNextActivityId(["SITE"], { ...baseDefaults, increment: 10, incrementActivityId: true }, "SITE"),
    "SITE10",
  );
});

test("invalid increments fall back to the stored default of ten", () => {
  assert.equal(computeNextActivityId(["A1"], { ...baseDefaults, increment: 0 }), "A11");
  assert.equal(computeNextActivityId(["A1"], { ...baseDefaults, increment: 2.5 }), "A11");
  assert.equal(computeNextActivityId(["A1"], { ...baseDefaults, increment: 20000 }), "A11");
});

test("stripActivityIdAffixes removes only matching prefix and suffix", () => {
  assert.equal(stripActivityIdAffixes(" A100-X ", "A", "-X"), "100");
  assert.equal(stripActivityIdAffixes("B100-X", "A", "-X"), "B100");
  assert.equal(stripActivityIdAffixes("A100", "", ""), "A100");
});
