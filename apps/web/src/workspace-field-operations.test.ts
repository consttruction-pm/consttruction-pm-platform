import assert from "node:assert/strict";
import test from "node:test";

import {
  EQUIPMENT_STATUS_VERSION,
  FIELD_ISSUE_VERSION,
  FIELD_TIMECARD_VERSION,
  projectEquipmentStatus,
  projectFieldIssue,
  projectFieldTimecard,
} from "./workspace-field-operations.js";

const context = { tenant_id: "tenant-1", project_id: "project-1", revision: 7 };
const scope = { tenant_id: "tenant-1", project_id: "project-1", project_revision: 7 };

const evidence = [{ source_id: "photo-1", source_type: "photo", locator: "/photos/1", revision: 7 }];

test("field issue projection preserves scope, evidence and activity links", () => {
  const issue = projectFieldIssue(
    {
      contract_version: FIELD_ISSUE_VERSION,
      issue_id: "issue-1",
      scope,
      category: "quality",
      severity: "high",
      status: "open",
      title_key: "issue.concrete.honeycombing",
      detail_key: "issue.detail",
      reported_by: "inspector-1",
      location_key: "tower-a",
      activity_ids: ["A-101"],
      evidence_refs: evidence,
    },
    context,
  );

  assert.equal(issue.issueId, "issue-1");
  assert.equal(issue.evidenceCount, 1);
  assert.deepEqual(issue.activityIds, ["A-101"]);
});

test("field issue rejects missing evidence", () => {
  assert.throws(
    () =>
      projectFieldIssue(
        {
          contract_version: FIELD_ISSUE_VERSION,
          issue_id: "issue-1",
          scope,
          category: "quality",
          severity: "high",
          status: "open",
          title_key: "issue.title",
          reported_by: "user-1",
          evidence_refs: [],
        },
        context,
      ),
    /INVALID_FIELD_ISSUE/,
  );
});

test("field timecard projection preserves string quantities", () => {
  const card = projectFieldTimecard(
    {
      contract_version: FIELD_TIMECARD_VERSION,
      timecard_id: "tc-1",
      scope,
      person_id: "person-1",
      log_date: "2026-09-27",
      workplace_key: "tower-a",
      attendance_status: "on_site",
      start_at: "2026-09-27T07:30:00+04:00",
      end_at: "2026-09-27T17:00:00+04:00",
      activity_allocations: [{ activity_id: "A-101", quantity: "8.50", unit: "hr" }],
    },
    context,
  );

  assert.equal(card.attendanceStatus, "on_site");
  assert.equal(card.activityAllocations[0]?.quantity, "8.50");
});

test("field timecard rejects invalid calendar dates and reversed ranges", () => {
  const base = {
    contract_version: FIELD_TIMECARD_VERSION,
    timecard_id: "tc-1",
    scope,
    person_id: "person-1",
    workplace_key: "tower-a",
    attendance_status: "present" as const,
  };

  assert.throws(
    () => projectFieldTimecard({ ...base, log_date: "2026-02-30" }, context),
    /INVALID_FIELD_TIMECARD/,
  );

  assert.throws(
    () =>
      projectFieldTimecard(
        {
          ...base,
          log_date: "2026-09-27",
          start_at: "2026-09-27T18:00:00+04:00",
          end_at: "2026-09-27T07:00:00+04:00",
        },
        context,
      ),
    /INVALID_FIELD_TIMECARD_RANGE/,
  );
});

test("equipment projection preserves breakdown and meter values without calculation", () => {
  const equipment = projectEquipmentStatus(
    {
      contract_version: EQUIPMENT_STATUS_VERSION,
      report_id: "equipment-report-1",
      scope,
      equipment_id: "excavator-01",
      report_date: "2026-09-27",
      workplace_key: "north-zone",
      status: "broken",
      breakdown_cause_key: "hydraulic.failure",
      reported_by: "equipment-supervisor",
      activity_allocations: [{ activity_id: "A-201", quantity: "2.5", unit: "hr" }],
      meter_hours: "1280.75",
    },
    context,
  );

  assert.equal(equipment.status, "broken");
  assert.equal(equipment.breakdownCauseKey, "hydraulic.failure");
  assert.equal(equipment.meterHours, "1280.75");
  assert.equal(equipment.activityAllocations[0]?.quantity, "2.5");
});

test("field operation projections reject stale or unsupported snapshots", () => {
  const issue = {
    contract_version: FIELD_ISSUE_VERSION as typeof FIELD_ISSUE_VERSION,
    issue_id: "issue-1",
    scope,
    category: "safety",
    severity: "critical" as const,
    status: "open" as const,
    title_key: "issue.title",
    reported_by: "user-1",
    evidence_refs: evidence,
  };

  assert.throws(
    () => projectFieldIssue({ ...issue, scope: { ...scope, project_revision: 6 } }, context),
    /STALE_FIELD_OPERATION_SCOPE/,
  );

  assert.throws(
    () =>
      projectFieldIssue(
        { ...issue, contract_version: "field-issue.v99" as never },
        context,
      ),
    /UNSUPPORTED_FIELD_OPERATION_CONTRACT/,
  );
});
