import assert from "node:assert/strict";
import test from "node:test";

import {
  EQUIPMENT_STATUS_VERSION,
  FIELD_TIMECARD_VERSION,
  projectEquipmentStatus,
  projectTimecard,
} from "./workspace-field-ops.js";

const context = { tenant_id: "tenant-1", project_id: "project-1", project_revision: 7 };
const audit = {
  created_by: "user-1",
  created_at: "2026-09-27T06:00:00Z",
  updated_at: "2026-09-27T07:00:00Z",
};

test("timecard projection preserves attendance without recalculation", () => {
  const card = projectTimecard({
    contract_version: FIELD_TIMECARD_VERSION,
    timecard_id: "tc-1",
    scope: context,
    person_id: "person-1",
    log_date: "2026-09-27",
    workplace_key: "tower-a",
    attendance_status: "present",
    audit,
    start_at: "2026-09-27T07:30:00Z",
    end_at: "2026-09-27T16:30:00Z",
  }, context);

  assert.equal(card.attendanceStatus, "present");
  assert.equal(card.personId, "person-1");
  assert.equal(card.startAt, "2026-09-27T07:30:00Z");
});

test("stale timecards are rejected", () => {
  const stale = { ...context, project_revision: 6 };
  assert.throws(() => projectTimecard({
    contract_version: FIELD_TIMECARD_VERSION,
    timecard_id: "tc-1",
    scope: stale,
    person_id: "person-1",
    log_date: "2026-09-27",
    workplace_key: "tower-a",
    attendance_status: "late",
    audit,
  }, context), /STALE_FIELD_TIMECARD_SCOPE/);
});

test("equipment projection preserves meter hours as transport text", () => {
  const report = projectEquipmentStatus({
    contract_version: EQUIPMENT_STATUS_VERSION,
    report_id: "eqr-1",
    scope: context,
    equipment_id: "exc-01",
    report_date: "2026-09-27",
    workplace_key: "tower-a",
    status: "broken",
    breakdown_cause_key: "hydraulic",
    reported_by: "user-1",
    meter_hours: "1240.50",
    audit,
  }, context);

  assert.equal(report.status, "broken");
  assert.equal(report.breakdownCauseKey, "hydraulic");
  assert.equal(report.meterHours, "1240.50");
});

test("invalid equipment meter values are rejected", () => {
  assert.throws(() => projectEquipmentStatus({
    contract_version: EQUIPMENT_STATUS_VERSION,
    report_id: "eqr-1",
    scope: context,
    equipment_id: "exc-01",
    report_date: "2026-09-27",
    workplace_key: "tower-a",
    status: "active",
    reported_by: "user-1",
    meter_hours: "-1",
    audit,
  }, context), /INVALID_EQUIPMENT_METER_HOURS/);
});
