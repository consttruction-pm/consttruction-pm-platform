import assert from "node:assert/strict";
import test from "node:test";

import {
  buildPastedActivityPayload,
  makeActivityClipboard,
  nextPastedActivityId,
} from "./workspace-activity-clipboard.js";

test("the clipboard keeps unique authoritative source ids per project and mode", () => {
  const copied = makeActivityClipboard("p1", ["A130", "A130", "A140"], "copy");
  assert.deepEqual(copied, { projectId: "p1", ids: ["A130", "A140"], mode: "copy" });
  assert.equal(makeActivityClipboard("p1", [], "cut"), null);
  assert.equal(makeActivityClipboard("p1", ["A130"], "cut")?.mode, "cut");
});

test("pasted ids avoid every id that is already loaded", () => {
  const taken = new Set(["A130", "A130-C1", "A130-C2"]);
  assert.equal(nextPastedActivityId("A130", taken), "A130-C3");
});

test("the clone payload copies fields but starts a planned activity without progress", () => {
  const payload = buildPastedActivityPayload({
    contract_version: "p6-activity-master-api.v1",
    activity: {
      activity_id: "A130",
      name: "Structural steel",
      duration_value: "12",
      duration_unit: "working-day",
      activity_type: "Task Dependent",
      status: "In Progress",
      status_code: "Active",
      percent_complete_type: "DURATION",
      duration_type: "Fixed Duration & Units",
      cost_account_id: "CA-1",
      leveling_priority: "High",
    },
  }, "A130-C1", "WBS-RPS-CIVIL");
  assert.ok(payload);
  assert.equal(payload.activity_id, "A130-C1");
  assert.equal(payload.name, "Structural steel");
  assert.equal(payload.duration_value, "12");
  assert.equal(payload.wbs_id, "WBS-RPS-CIVIL");
  assert.equal(payload.status, "Not Started");
  assert.equal(payload.status_code, "Planned");
  assert.equal(payload.cost_account_id, "CA-1");
  assert.equal(payload.leveling_priority, "High");
  assert.equal(buildPastedActivityPayload(null, "X", null), null);
});
