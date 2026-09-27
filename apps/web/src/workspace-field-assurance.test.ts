import assert from "node:assert/strict";
import test from "node:test";

import {
  FIELD_INSPECTION_VERSION,
  QUALITY_RECORD_VERSION,
  PUNCH_ITEM_VERSION,
  SAFETY_OBSERVATION_VERSION,
  projectInspection,
  projectQualityRecord,
  projectPunchItem,
  projectSafetyObservation,
} from "./workspace-field-assurance.js";

const context = { tenant_id: "tenant-1", project_id: "project-1", project_revision: 9 };

test("inspection projection preserves checklist results", () => {
  const inspection = projectInspection({
    contract_version: FIELD_INSPECTION_VERSION,
    inspection_id: "insp-1",
    scope: context,
    inspection_type_key: "rebar",
    subject_type: "activity",
    subject_id: "A-10",
    location_key: "tower-a",
    inspection_date: "2026-09-27",
    inspector_id: "inspector-1",
    status: "completed",
    result: "pass",
    checklist: [{
      item_id: "item-1",
      criterion_key: "cover",
      result: "pass",
      comment_key: null,
    }],
  }, context);

  assert.equal(inspection.result, "pass");
  assert.equal(inspection.checklist[0]?.criterionKey, "cover");
});

test("quality record projection preserves NCR evidence and corrective references", () => {
  const record = projectQualityRecord({
    contract_version: QUALITY_RECORD_VERSION,
    record_id: "qr-1",
    scope: context,
    category_key: "concrete",
    severity: "high",
    status: "pending_verification",
    title_key: "ncr.concrete",
    reported_by: "qc-1",
    detail_key: "ncr.detail",
    location_key: "tower-a",
    activity_ids: ["A-10"],
    inspection_id: "insp-1",
    specification_reference: "SPEC-09",
    corrective_action_key: "repair-and-retest",
    disposition_key: "conditional_acceptance",
    evidence_refs: [{
      source_id: "photo-2",
      source_type: "photo",
      locator: "/photos/2",
      revision: 9,
    }],
  }, context);

  assert.equal(record.status, "pending_verification");
  assert.equal(record.inspectionId, "insp-1");
  assert.equal(record.evidenceCount, 1);
  assert.deepEqual(record.activityIds, ["A-10"]);
});

test("safety observation projection preserves activity links", () => {
  const observation = projectSafetyObservation({
    contract_version: SAFETY_OBSERVATION_VERSION,
    observation_id: "obs-1",
    scope: context,
    category_key: "working_at_height",
    severity: "high",
    status: "open",
    title_key: "unguarded_edge",
    observed_by: "safety-1",
    location_key: "floor-12",
    activity_ids: ["A-12", "A-13"],
    immediate_action_key: "stop_work_and_guard",
  }, context);

  assert.equal(observation.severity, "high");
  assert.deepEqual(observation.activityIds, ["A-12", "A-13"]);
});

test("punch item projection preserves closeout fields", () => {
  const punch = projectPunchItem({
    contract_version: PUNCH_ITEM_VERSION,
    punch_id: "p-1",
    scope: context,
    category_key: "finish",
    priority: "medium",
    status: "ready_for_verification",
    title_key: "door_hardware",
    reported_by: "qc-1",
    responsible_party_id: "sub-7",
    due_date: "2026-10-05",
    verification_by: "inspector-3",
    closeout_code_key: "verified",
  }, context);

  assert.equal(punch.status, "ready_for_verification");
  assert.equal(punch.dueDate, "2026-10-05");
  assert.equal(punch.verificationBy, "inspector-3");
});

test("stale safety observations and invalid punch dates are rejected", () => {
  const stale = { ...context, project_revision: 8 };
  assert.throws(() => projectSafetyObservation({
    contract_version: SAFETY_OBSERVATION_VERSION,
    observation_id: "obs-2",
    scope: stale,
    category_key: "ppe",
    severity: "low",
    status: "open",
    title_key: "ppe_gap",
    observed_by: "safety-1",
  }, context), /STALE_SAFETY_OBSERVATION_SCOPE/);

  assert.throws(() => projectPunchItem({
    contract_version: PUNCH_ITEM_VERSION,
    punch_id: "p-2",
    scope: context,
    category_key: "finish",
    priority: "low",
    status: "open",
    title_key: "floor",
    reported_by: "qc-1",
    due_date: "05-10-2026",
  }, context), /INVALID_PUNCH_ITEM/);
});
