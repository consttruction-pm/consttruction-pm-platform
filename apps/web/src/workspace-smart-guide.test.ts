import assert from "node:assert/strict";
import test from "node:test";

import {
  CONTROL_INTELLIGENCE_RESULT_VERSION,
  type ControlRoomIntelligenceSnapshot,
} from "./workspace-control-intelligence.js";
import {
  SMART_GUIDE_VERSION,
  SCHEDULE_QUERY_VERSION,
  buildScheduleQueryRequest,
  projectSmartGuide,
} from "./workspace-smart-guide.js";

const context = { tenant_id: "tenant-1", project_id: "project-1", revision: 12 };
const source = {
  source_id: "schedule-1",
  source_type: "schedule",
  locator: "/schedule/A-1",
  revision: 12,
};

function snapshot(): ControlRoomIntelligenceSnapshot {
  return {
    contract_version: CONTROL_INTELLIGENCE_RESULT_VERSION,
    result_id: "result-1",
    scope: {
      tenant_id: context.tenant_id,
      project_id: context.project_id,
      project_revision: context.revision,
    },
    generated_at: "2026-09-27T08:00:00Z",
    summary_key: "control.summary",
    findings: [{
      finding_id: "f-1",
      domain: "schedule",
      severity: "warning",
      title_key: "finding.delay",
      detail_key: "finding.delay.detail",
      source_refs: [source],
    }],
    metrics: { schedule_variance: -2.5 },
    source_refs: [source],
    proposed_actions: [{
      action_id: "a-1",
      action_type: "schedule_review",
      title_key: "action.review",
      source_refs: [source],
      requires_approval: true,
    }],
  };
}

test("smart guide projects traceable findings and approval-safe actions", () => {
  const guide = projectSmartGuide(snapshot(), context, "schedule", "fa");

  assert.equal(guide.contractVersion, SMART_GUIDE_VERSION);
  assert.equal(guide.module, "schedule");
  assert.equal(guide.locale, "fa");
  assert.equal(guide.sourceCount, 1);
  assert.equal(guide.approvalRequiredCount, 1);
  assert.equal(guide.findings[0]?.finding_id, "f-1");
  assert.equal(guide.proposedActions[0]?.requiresApproval, true);
});

test("smart guide preserves control-intelligence scope semantics", () => {
  assert.throws(
    () => projectSmartGuide(
      { ...snapshot(), scope: { ...snapshot().scope, project_revision: 11 } },
      context,
      "control-room",
      "en",
    ),
    /STALE_CONTROL_INTELLIGENCE_SCOPE/,
  );
});

test("schedule query composer creates the exact versioned wire contract", () => {
  const request = buildScheduleQueryRequest(
    context,
    "planner-1",
    "query-1",
    "Which critical activities are delayed?",
    "fact",
    "fa-IR",
    { critical_only: true },
  );

  assert.equal(request.contract_version, SCHEDULE_QUERY_VERSION);
  assert.equal(request.scope.project_revision, 12);
  assert.equal(request.kind, "fact");
  assert.equal(request.language, "fa-IR");
  assert.deepEqual(request.constraints, { critical_only: true });
});

test("schedule query composer rejects invalid identity and kind", () => {
  assert.throws(
    () => buildScheduleQueryRequest(
      context,
      "",
      "query-1",
      "What is delayed?",
      "fact",
      "en-US",
    ),
    /INVALID_SCHEDULE_QUERY_REQUEST/,
  );

  assert.throws(
    () => buildScheduleQueryRequest(
      context,
      "planner-1",
      "query-1",
      "What is delayed?",
      "unknown" as never,
      "en-US",
    ),
    /INVALID_SCHEDULE_QUERY_KIND/,
  );
});
