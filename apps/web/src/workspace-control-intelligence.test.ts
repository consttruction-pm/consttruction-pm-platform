import assert from "node:assert/strict";
import test from "node:test";

import {
  CONTROL_INTELLIGENCE_RESULT_VERSION,
  projectControlIntelligence,
} from "./workspace-control-intelligence.js";

const context = { tenant_id: "tenant-1", project_id: "project-1", revision: 12 };

const source = {
  source_id: "schedule-1",
  source_type: "schedule",
  locator: "/schedule/A-1",
  revision: 12,
};

const snapshot = () => ({
  contract_version: CONTROL_INTELLIGENCE_RESULT_VERSION,
  result_id: "result-1",
  scope: {
    tenant_id: "tenant-1",
    project_id: "project-1",
    project_revision: 12,
  },
  generated_at: "2026-09-27T08:00:00Z",
  summary_key: "control.summary",
  findings: [{
    finding_id: "finding-1",
    domain: "schedule" as const,
    severity: "warning" as const,
    title_key: "finding.title",
    detail_key: "finding.detail",
    source_refs: [source],
  }],
  metrics: {
    schedule_variance: -2.5,
    progress_percent: 63,
  },
  source_refs: [source],
  proposed_actions: [],
});

test("control intelligence projection preserves authoritative revision and evidence", () => {
  const projected = projectControlIntelligence(snapshot(), context);
  assert.equal(projected.resultId, "result-1");
  assert.equal(projected.metrics.progress_percent, 63);
  assert.equal(projected.findings[0]?.source_refs[0]?.revision, 12);
});

test("stale control intelligence is rejected rather than silently displayed", () => {
  const broken = {
    ...snapshot(),
    scope: { ...snapshot().scope, project_revision: 11 },
  };
  assert.throws(
    () => projectControlIntelligence(broken, context),
    /STALE_CONTROL_INTELLIGENCE_SCOPE/,
  );
});

test("unsupported control intelligence version is rejected", () => {
  const broken = { ...snapshot(), contract_version: "control-intelligence-result.v99" };
  assert.throws(
    () => projectControlIntelligence(broken as never, context),
    /UNSUPPORTED_CONTROL_INTELLIGENCE_CONTRACT/,
  );
});

test("non-finite metrics are rejected", () => {
  const broken = { ...snapshot(), metrics: { progress_percent: Number.NaN } };
  assert.throws(
    () => projectControlIntelligence(broken, context),
    /INVALID_CONTROL_INTELLIGENCE_METRIC/,
  );
});

test("stale top-level control intelligence source revision is rejected", () => {
  const broken = {
    ...snapshot(),
    source_refs: [{ ...source, revision: 11 }],
  };
  assert.throws(
    () => projectControlIntelligence(broken, context),
    /STALE_CONTROL_INTELLIGENCE_SOURCE/,
  );
});

test("stale finding evidence revision is rejected", () => {
  const broken = {
    ...snapshot(),
    findings: [{
      ...snapshot().findings[0],
      source_refs: [{ ...source, revision: 11 }],
    }],
  };
  assert.throws(
    () => projectControlIntelligence(broken, context),
    /STALE_CONTROL_INTELLIGENCE_SOURCE/,
  );
});

test("stale proposed action evidence revision is rejected", () => {
  const broken = {
    ...snapshot(),
    proposed_actions: [{
      action_id: "action-1",
      action_type: "review",
      title_key: "action.review",
      source_refs: [{ ...source, revision: 11 }],
      requires_approval: true,
    }],
  };
  assert.throws(
    () => projectControlIntelligence(broken, context),
    /STALE_CONTROL_INTELLIGENCE_SOURCE/,
  );
});
