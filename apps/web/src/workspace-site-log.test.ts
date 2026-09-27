import assert from "node:assert/strict";
import test from "node:test";

import { FIELD_DAILY_LOG_VERSION, projectSiteDailyLog } from "./workspace-site-log.js";

const context = { tenant_id: "tenant-1", project_id: "project-1", revision: 5 };

const sourceLog = () => ({
  contract_version: FIELD_DAILY_LOG_VERSION,
  log_id: "log-1",
  scope: { tenant_id: "tenant-1", project_id: "project-1", project_revision: 5 },
  log_date: "2026-09-27",
  location_key: "tower-a",
  status: "submitted" as const,
  entries: [{
    entry_id: "entry-1",
    category: "work",
    text_key: "concrete.completed",
    activity_ids: ["A-101"],
    resource_ids: ["crew-01"],
    quantity: "120.50",
    unit: "m3",
  }],
  audit: {
    created_by: "user-1",
    created_at: "2026-09-27T06:00:00Z",
    updated_at: "2026-09-27T10:00:00Z",
  },
});

test("site daily log projection preserves revision and typed quantities", () => {
  const log = projectSiteDailyLog(sourceLog(), context);
  assert.equal(log.logId, "log-1");
  assert.equal(log.status, "submitted");
  assert.equal(log.entries[0]?.quantity, "120.50");
  assert.equal(log.entries[0]?.activity_ids[0], "A-101");
});

test("stale daily logs are rejected", () => {
  const broken = { ...sourceLog(), scope: { ...sourceLog().scope, project_revision: 4 } };
  assert.throws(() => projectSiteDailyLog(broken, context), /STALE_FIELD_DAILY_LOG_SCOPE/);
});

test("unsupported daily log contracts are rejected", () => {
  const broken = { ...sourceLog(), contract_version: "field-daily-log.v99" };
  assert.throws(() => projectSiteDailyLog(broken as never, context), /UNSUPPORTED_FIELD_DAILY_LOG_CONTRACT/);
});

test("invalid dates are rejected", () => {
  const broken = { ...sourceLog(), log_date: "27-09-2026" };
  assert.throws(() => projectSiteDailyLog(broken, context), /INVALID_FIELD_DAILY_LOG/);
});
