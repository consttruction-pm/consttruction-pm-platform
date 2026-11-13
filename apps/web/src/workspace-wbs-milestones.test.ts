import assert from "node:assert/strict";
import test from "node:test";

import type { WorkspaceWbsMilestone } from "./workspace-model.js";
import { weightedPercentComplete, wbsStatusLabel, wbsTechniqueLabel } from "./workspace-wbs-milestones.js";

function milestone(weight: number, completed: boolean): WorkspaceWbsMilestone {
  return { id: `M-${weight}-${completed}`, name: "M", weight, completed, sequenceNumber: 0 };
}

test("weighted percent complete divides completed weight by total weight", () => {
  assert.equal(weightedPercentComplete([milestone(9, true), milestone(3, false)]), 75);
  assert.equal(
    weightedPercentComplete([milestone(9, true), milestone(1, true), milestone(2, false)]),
    83.33,
  );
});

test("weighted percent complete rounds to two decimals and handles empty weights", () => {
  assert.equal(weightedPercentComplete([]), 0);
  assert.equal(weightedPercentComplete([milestone(1, true), milestone(2, false)]), 33.33);
  assert.equal(weightedPercentComplete([milestone(1, false), milestone(1, true)]), 50);
});

test("WBS status and technique labels are localized without fabricating a missing status", () => {
  assert.equal(wbsStatusLabel("en", "active"), "Active");
  assert.equal(wbsStatusLabel("fa", "what_if"), "فرضی");
  assert.equal(wbsStatusLabel("en", undefined), "—");
  assert.equal(wbsTechniqueLabel("en", "milestones"), "WBS Milestones");
  assert.equal(wbsTechniqueLabel("fa", "activities"), "فعالیت‌ها");
  assert.equal(wbsTechniqueLabel("en", undefined), "—");
});
