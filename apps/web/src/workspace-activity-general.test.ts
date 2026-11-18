import assert from "node:assert/strict";
import test from "node:test";

import {
  ACTIVITY_MASTER_API_VERSION,
  applyActivityGeneralToCells,
  buildActivityGeneralPatch,
  loadActivityGeneral,
  parseActivityGeneral,
  saveActivityGeneral,
  type ActivityGeneralInput,
  type ActivityGeneralRecord,
} from "./workspace-activity-general.js";
import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";

const CONTEXT: ProjectContext = {
  tenant_id: "tenant-1",
  project_id: "project-1",
  revision: 7,
};

function dto(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    activity_id: "A130",
    name: "Excavate foundations",
    activity_type: "Task Dependent",
    duration_type: "Fixed Duration & Units",
    percent_complete_type: "DURATION",
    leveling_priority: "Normal",
    cost_account_id: "CA-1",
    duration_value: "12",
    duration_unit: "working-day",
    status: "Not Started",
    record_revision: 3,
    ...overrides,
  };
}

function envelope(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    contract_version: ACTIVITY_MASTER_API_VERSION,
    activity: dto(overrides),
  };
}

const PARSED: ActivityGeneralRecord = {
  activityId: "A130",
  name: "Excavate foundations",
  activityType: "Task Dependent",
  durationType: "Fixed Duration & Units",
  percentCompleteType: "DURATION",
  levelingPriority: "Normal",
  costAccountId: "CA-1",
  durationValue: "12",
  durationUnit: "working-day",
  status: "Not Started",
  recordRevision: 3,
};

function input(overrides: Partial<ActivityGeneralInput> = {}): ActivityGeneralInput {
  return {
    name: "Excavate foundations",
    activityType: "Task Dependent",
    durationType: "Fixed Duration & Units",
    percentCompleteType: "DURATION",
    levelingPriority: "Normal",
    costAccountId: "CA-1",
    ...overrides,
  };
}

type Calls = {
  gets: string[];
  patches: Array<{ path: string; request: Record<string, unknown> }>;
};

function transportWith(
  getResult: ApiResult<unknown>,
  patchResult: ApiResult<unknown>,
  calls: Calls,
): ApiTransport {
  return {
    async get<T>(path: string): Promise<ApiResult<T>> {
      calls.gets.push(path);
      return getResult as ApiResult<T>;
    },
    async post<TRequest, TResponse>(): Promise<ApiResult<TResponse>> {
      throw new Error("unused");
    },
    async patch<T, R>(path: string, request: unknown): Promise<ApiResult<T>> {
      calls.patches.push({ path, request: request as Record<string, unknown> });
      return patchResult as ApiResult<T>;
    },
  };
}

test("activity master parsing accepts the nested DTO and keeps the revision", () => {
  const parsed = parseActivityGeneral(envelope());
  assert.equal(parsed.activityId, "A130");
  assert.equal(parsed.activityType, "Task Dependent");
  assert.equal(parsed.durationType, "Fixed Duration & Units");
  assert.equal(parsed.percentCompleteType, "DURATION");
  assert.equal(parsed.levelingPriority, "Normal");
  assert.equal(parsed.costAccountId, "CA-1");
  assert.equal(parsed.recordRevision, 3);
});

test("activity master parsing rejects unknown enums and missing revisions", () => {
  assert.throws(() => parseActivityGeneral({ contract_version: "wrong", activity: dto() }), /INVALID_ACTIVITY_MASTER_RESPONSE/);
  assert.throws(() => parseActivityGeneral(envelope({ activity_type: "Summary Task" })), /INVALID_ACTIVITY_MASTER_RESPONSE/);
  assert.throws(() => parseActivityGeneral(envelope({ duration_type: "Elapsed" })), /INVALID_ACTIVITY_MASTER_RESPONSE/);
  assert.throws(() => parseActivityGeneral(envelope({ percent_complete_type: "Duration" })), /INVALID_ACTIVITY_MASTER_RESPONSE/);
  assert.throws(() => parseActivityGeneral(envelope({ leveling_priority: "Urgent" })), /INVALID_ACTIVITY_MASTER_RESPONSE/);
  assert.throws(() => parseActivityGeneral(envelope({ record_revision: 0 })), /INVALID_ACTIVITY_MASTER_RESPONSE/);
  assert.throws(() => parseActivityGeneral(envelope({ name: "   " })), /INVALID_ACTIVITY_MASTER_RESPONSE/);
});

test("general patch contains only the fields that changed", () => {
  const patch = buildActivityGeneralPatch(PARSED, input({
    name: "Excavate and blind foundations",
    percentCompleteType: "UNITS",
    levelingPriority: "High",
  }));
  assert.deepEqual(patch, {
    name: "Excavate and blind foundations",
    percent_complete_type: "UNITS",
    leveling_priority: "High",
  });
});

test("general patch rejects invalid drafts instead of writing", () => {
  assert.equal(buildActivityGeneralPatch(PARSED, input({ name: " " })), "ACTIVITY_NAME_REQUIRED");
  assert.equal(buildActivityGeneralPatch(PARSED, input({ name: "x".repeat(181) })), "ACTIVITY_NAME_TOO_LONG");
  assert.equal(buildActivityGeneralPatch(PARSED, input({ activityType: "Summary Task" })), "INVALID_ACTIVITY_TYPE");
  assert.equal(buildActivityGeneralPatch(PARSED, input({ durationType: "Elapsed" })), "INVALID_DURATION_TYPE");
  assert.equal(buildActivityGeneralPatch(PARSED, input({ percentCompleteType: "Duration" })), "INVALID_PERCENT_COMPLETE_TYPE");
  assert.equal(buildActivityGeneralPatch(PARSED, input({ levelingPriority: "Urgent" })), "INVALID_LEVELING_PRIORITY");
});

test("loadActivityGeneral reads the activity master and reports service errors", async () => {
  const calls: Calls = { gets: [], patches: [] };
  const ok = await loadActivityGeneral(transportWith({ ok: true, data: envelope() }, { ok: true, data: envelope() }, calls), CONTEXT, "A 130/1");
  assert.equal(ok.ok, true);
  assert.deepEqual(calls.gets, ["/api/projects/project-1/p6/activities/A%20130%2F1"]);

  const denied = await loadActivityGeneral(transportWith({ ok: false, error: { code: "AUTHORIZATION_DENIED", retryable: false, message_key: "error.authorization.denied", available_actions: [] } }, { ok: true, data: envelope() }, calls), CONTEXT, "A130");
  assert.equal(denied.ok, false);
  if (!denied.ok) assert.equal(denied.error.code, "AUTHORIZATION_DENIED");
});

test("saveActivityGeneral patches with the loaded revision and no other fields", async () => {
  const calls: Calls = { gets: [], patches: [] };
  const result = await saveActivityGeneral(
    transportWith({ ok: true, data: envelope() }, {
      ok: true,
      data: envelope({
        name: "Excavate and blind foundations",
        activity_type: "Level of Effort",
        leveling_priority: "Top",
        record_revision: 4,
      }),
    }, calls),
    CONTEXT,
    PARSED,
    input({
      name: "Excavate and blind foundations",
      activityType: "Level of Effort",
      levelingPriority: "Top",
    }),
  );
  assert.equal(result.ok, true);
  if (!result.ok) return;
  assert.equal(result.data.changed, true);
  assert.equal(result.data.record.recordRevision, 4);
  assert.equal(result.data.record.levelingPriority, "Top");
  assert.deepEqual(calls.patches, [{
    path: "/api/projects/project-1/p6/activities/A130",
    request: {
      contract_version: ACTIVITY_MASTER_API_VERSION,
      expected_revision: 3,
      name: "Excavate and blind foundations",
      activity_type: "Level of Effort",
      leveling_priority: "Top",
    },
  }]);
});

test("saveActivityGeneral performs no write when the draft is unchanged", async () => {
  const calls: Calls = { gets: [], patches: [] };
  const result = await saveActivityGeneral(
    transportWith({ ok: true, data: envelope() }, { ok: true, data: envelope() }, calls),
    CONTEXT,
    PARSED,
    input({ name: "  Excavate foundations  ", costAccountId: " CA-1 " }),
  );
  assert.equal(result.ok, true);
  if (!result.ok) return;
  assert.equal(result.data.changed, false);
  assert.deepEqual(calls.patches, []);
});

test("saveActivityGeneral surfaces revision conflicts and refuses a transport without PATCH", async () => {
  const calls: Calls = { gets: [], patches: [] };
  const conflict = await saveActivityGeneral(
    transportWith({ ok: true, data: envelope() }, {
      ok: false,
      error: { code: "REVISION_CONFLICT", retryable: false, message_key: "error.revision.conflict", available_actions: [] },
    }, calls),
    CONTEXT,
    PARSED,
    input({ activityType: "Resource Dependent" }),
  );
  assert.equal(conflict.ok, false);
  if (!conflict.ok) assert.equal(conflict.error.code, "REVISION_CONFLICT");

  const readOnly: ApiTransport = {
    async get<T>(): Promise<ApiResult<T>> {
      return { ok: true, data: envelope() as T };
    },
    async post<TRequest, TResponse>(): Promise<ApiResult<TResponse>> {
      throw new Error("unused");
    },
  };
  const refused = await saveActivityGeneral(readOnly, CONTEXT, PARSED, input({ activityType: "Resource Dependent" }));
  assert.equal(refused.ok, false);
  if (!refused.ok) assert.equal(refused.error.code, "ACTIVITY_WRITE_TRANSPORT_UNAVAILABLE");
});

test("authoritative general fields are projected without touching schedule facts", () => {
  const cells = applyActivityGeneralToCells({
    "activity.name": "Old name",
    "activity.type": "Task Dependent",
    "activity.leveling_priority": "Normal",
    "activity.total_float": "4",
    "activity.early_start": "2026-11-01",
  }, {
    ...PARSED,
    name: "New name",
    activityType: "WBS Summary",
    percentCompleteType: "PHYSICAL",
    levelingPriority: "Lowest",
    costAccountId: null,
  });
  assert.equal(cells["activity.name"], "New name");
  assert.equal(cells["activity.activity_name"], "New name");
  assert.equal(cells["activity.type"], "WBS Summary");
  assert.equal(cells["activity.percent_complete_type"], "PHYSICAL");
  assert.equal(cells["activity.leveling_priority"], "Lowest");
  assert.equal(cells["activity.cost_account"], "");
  assert.equal(cells["activity.total_float"], "4");
  assert.equal(cells["activity.early_start"], "2026-11-01");
});
