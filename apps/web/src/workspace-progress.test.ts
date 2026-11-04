import assert from "node:assert/strict";
import test from "node:test";

import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";
import {
  buildProgressPayload,
  loadProgressActivities,
  parseProgressActivity,
  saveProgress,
  type ProgressActivity,
} from "./workspace-progress.js";

const CONTEXT: ProjectContext = { tenant_id: "t1", project_id: "project-1", revision: 4 };

const ACTIVITY = {
  activity_id: "A140",
  name: "Piling and foundations",
  status: "Not Started",
  status_code: "Planned",
  percent_complete: null,
  actual_start: null,
  actual_finish: null,
  remaining_duration: null,
  record_revision: 3,
};

function envelope(activity: unknown = ACTIVITY) {
  return {
    contract_version: "p6-activity-master-api.v1",
    kind: "p6_activity_master",
    scope: { tenant_id: "t1", project_id: "project-1", project_revision: 4 },
    activity,
  };
}

const PARSED: ProgressActivity = {
  activityId: "A140",
  name: "Piling and foundations",
  status: "Not Started",
  statusCode: "Planned",
  percentComplete: null,
  actualStart: null,
  actualFinish: null,
  remainingDuration: null,
  recordRevision: 3,
};

type Calls = {
  gets: { path: string }[];
  patches: { path: string; request: unknown }[];
};

function transportWith(
  result: ApiResult<unknown>,
  calls: Calls = { gets: [], patches: [] },
  withPatch = true,
): ApiTransport {
  const transport: ApiTransport = {
    async get(path) {
      calls.gets.push({ path });
      return result as ApiResult<never>;
    },
    async post() {
      throw new Error("progress must not POST");
    },
  };
  if (withPatch) {
    transport.patch = async (path, request) => {
      calls.patches.push({ path, request });
      return result as ApiResult<never>;
    };
  }
  return transport;
}

test("progress list reads the activity master contract and preserves stored progress", async () => {
  const calls: Calls = { gets: [], patches: [] };
  const stored = {
    ...ACTIVITY,
    status: "In Progress",
    status_code: "Active",
    percent_complete: 37.5,
    actual_start: "2026-10-07",
    remaining_duration: 5,
    record_revision: 4,
  };
  const result = await loadProgressActivities(
    transportWith({ ok: true, data: { contract_version: "p6-activity-master-api.v1", activities: [envelope(stored)] } }, calls),
    CONTEXT,
  );
  assert.equal(result.ok, true);
  if (!result.ok) return;
  assert.deepEqual(result.data, [{
    activityId: "A140",
    name: "Piling and foundations",
    status: "In Progress",
    statusCode: "Active",
    percentComplete: 37.5,
    actualStart: "2026-10-07",
    actualFinish: null,
    remainingDuration: 5,
    recordRevision: 4,
  }]);
  assert.deepEqual(calls.gets, [{ path: "/api/projects/project-1/p6/activities" }]);
});

test("progress list fails closed on a foreign contract, a missing identity or a bad revision", async () => {
  for (const activities of [
    [{ ...envelope(), contract_version: "other-api.v1" }],
    [envelope({ ...ACTIVITY, activity_id: "" })],
    [envelope({ ...ACTIVITY, record_revision: 0 })],
    [envelope({ ...ACTIVITY, percent_complete: 120 })],
    [envelope({ ...ACTIVITY, remaining_duration: -1 })],
  ]) {
    const result = await loadProgressActivities(
      transportWith({ ok: true, data: { contract_version: "p6-activity-master-api.v1", activities } }),
      CONTEXT,
    );
    assert.equal(result.ok, false, JSON.stringify(activities));
  }
});

test("parseProgressActivity rejects a non-activity envelope", () => {
  assert.throws(() => parseProgressActivity(null), /INVALID_ACTIVITY_RECORD/);
  assert.throws(() => parseProgressActivity({}), /INVALID_ACTIVITY_RESPONSE/);
  assert.throws(() => parseProgressActivity({ ...envelope(), kind: "p6_resource" }), /INVALID_ACTIVITY_RESPONSE/);
});

test("progress payload carries the loaded revision and normalized progress values", () => {
  const payload = buildProgressPayload(PARSED, {
    status: "In Progress",
    percentComplete: " 20.5 ",
    actualStart: "2026-10-07",
    actualFinish: "",
    remainingDuration: "6",
  });
  assert.deepEqual(payload, {
    contract_version: "p6-activity-master-api.v1",
    expected_revision: 3,
    percent_complete: 20.5,
    actual_start: "2026-10-07",
    actual_finish: null,
    remaining_duration: 6,
    status: "In Progress",
  });
});

test("progress payload clears optional values only when the form is empty", () => {
  const started: ProgressActivity = {
    ...PARSED,
    status: "In Progress",
    statusCode: "Active",
    percentComplete: 37.5,
    actualStart: "2026-10-07",
    remainingDuration: 5,
    recordRevision: 9,
  };
  const payload = buildProgressPayload(started, {
    status: "In Progress",
    percentComplete: "",
    actualStart: "",
    actualFinish: "",
    remainingDuration: "",
  });
  assert.equal(payload.percent_complete, null);
  assert.equal(payload.actual_start, null);
  assert.equal(payload.remaining_duration, null);
  assert.equal(payload.expected_revision, 9);
});

test("progress payload preserves a stored timestamp when the edited day did not change", () => {
  const started: ProgressActivity = {
    ...PARSED,
    status: "In Progress",
    statusCode: "Active",
    actualStart: "2026-10-07T08:30:00",
    recordRevision: 5,
  };
  const payload = buildProgressPayload(started, {
    status: "In Progress",
    percentComplete: "40",
    actualStart: "2026-10-07",
    actualFinish: "",
    remainingDuration: "4",
  });
  assert.equal(payload.actual_start, "2026-10-07T08:30:00");
});

test("progress payload enforces the shared activity constraints before the write", () => {
  const base = {
    status: "In Progress",
    percentComplete: "40",
    actualStart: "2026-10-07",
    actualFinish: "",
    remainingDuration: "4",
  };
  const cases: { input: typeof base; code: RegExp }[] = [
    { input: { ...base, percentComplete: "101" }, code: /INVALID_PERCENT_COMPLETE/ },
    { input: { ...base, percentComplete: "-1" }, code: /INVALID_PERCENT_COMPLETE/ },
    { input: { ...base, percentComplete: "abc" }, code: /INVALID_PERCENT_COMPLETE/ },
    { input: { ...base, remainingDuration: "-2" }, code: /INVALID_REMAINING_DURATION/ },
    { input: { ...base, remainingDuration: "1.5" }, code: /INVALID_REMAINING_DURATION/ },
    { input: { ...base, actualStart: "07/10/2026" }, code: /INVALID_ACTUAL_START/ },
    {
      input: { ...base, actualFinish: "2026-10-06", remainingDuration: "0" },
      code: /FINISH_BEFORE_START/,
    },
    {
      input: { ...base, actualStart: "", actualFinish: "2026-10-08", remainingDuration: "0" },
      code: /FINISH_REQUIRES_START/,
    },
    {
      input: { ...base, actualFinish: "2026-10-08", remainingDuration: "4" },
      code: /COMPLETED_REMAINING_DURATION/,
    },
    {
      input: { ...base, actualFinish: "2026-10-08", remainingDuration: "0", percentComplete: "50" },
      code: /COMPLETED_PERCENT_REQUIRED/,
    },
    { input: { ...base, status: "Paused" }, code: /INVALID_ACTIVITY_STATUS/ },
  ];
  for (const item of cases) {
    assert.throws(() => buildProgressPayload(PARSED, item.input), item.code);
  }
});

test("saveProgress PATCHes the activity and returns the stored record", async () => {
  const calls: Calls = { gets: [], patches: [] };
  const updated = {
    ...ACTIVITY,
    status: "In Progress",
    status_code: "Active",
    percent_complete: 20.5,
    actual_start: "2026-10-07",
    remaining_duration: 6,
    record_revision: 4,
  };
  const result = await saveProgress(
    transportWith({ ok: true, data: envelope(updated) }, calls),
    CONTEXT,
    PARSED,
    {
      status: "In Progress",
      percentComplete: "20.5",
      actualStart: "2026-10-07",
      actualFinish: "",
      remainingDuration: "6",
    },
  );
  assert.equal(result.ok, true);
  if (!result.ok) return;
  assert.equal(result.data.recordRevision, 4);
  assert.equal(result.data.percentComplete, 20.5);
  assert.deepEqual(calls.patches, [{
    path: "/api/projects/project-1/p6/activities/A140",
    request: {
      contract_version: "p6-activity-master-api.v1",
      expected_revision: 3,
      percent_complete: 20.5,
      actual_start: "2026-10-07",
      actual_finish: null,
      remaining_duration: 6,
      status: "In Progress",
    },
  }]);
});

test("saveProgress keeps the transport receiver for the optional PATCH method", async () => {
  const calls: Calls = { gets: [], patches: [] };
  const updated = {
    ...ACTIVITY,
    status: "In Progress",
    status_code: "Active",
    actual_start: "2026-10-12",
    remaining_duration: 9,
    record_revision: 2,
  };
  class BoundTransport implements ApiTransport {
    readonly calls = calls;
    async get(): Promise<ApiResult<never>> {
      throw new Error("unused");
    }
    async post(): Promise<ApiResult<never>> {
      throw new Error("unused");
    }
    async patch(path: string, request: unknown): Promise<ApiResult<never>> {
      this.calls.patches.push({ path, request });
      return { ok: true, data: envelope(updated) } as ApiResult<never>;
    }
  }
  const result = await saveProgress(new BoundTransport(), CONTEXT, PARSED, {
    status: "In Progress",
    percentComplete: "15",
    actualStart: "2026-10-12",
    actualFinish: "",
    remainingDuration: "9",
  });
  assert.equal(result.ok, true);
  assert.equal(calls.patches.length, 1);
  assert.equal(calls.patches[0]?.path, "/api/projects/project-1/p6/activities/A140");
});

test("saveProgress refuses an invalid draft or a transport without PATCH and writes nothing", async () => {
  const calls: Calls = { gets: [], patches: [] };
  const invalid = await saveProgress(
    transportWith({ ok: true, data: envelope() }, calls),
    CONTEXT,
    PARSED,
    {
      status: "In Progress",
      percentComplete: "101",
      actualStart: "",
      actualFinish: "",
      remainingDuration: "",
    },
  );
  assert.equal(invalid.ok, false);
  if (!invalid.ok) assert.equal(invalid.error.code, "INVALID_PERCENT_COMPLETE");
  assert.deepEqual(calls.patches, []);

  const unsupported = await saveProgress(
    transportWith({ ok: true, data: envelope() }, calls, false),
    CONTEXT,
    PARSED,
    {
      status: "In Progress",
      percentComplete: "10",
      actualStart: "",
      actualFinish: "",
      remainingDuration: "2",
    },
  );
  assert.equal(unsupported.ok, false);
  if (!unsupported.ok) assert.equal(unsupported.error.code, "PROGRESS_TRANSPORT_UNAVAILABLE");
  assert.deepEqual(calls.patches, []);
});
