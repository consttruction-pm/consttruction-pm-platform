import assert from "node:assert/strict";
import test from "node:test";
import type { BaselineRecord, EarnedValueSnapshot, RiskHistoryEvent, RiskRecord } from "./workbench/api.js";
import {
  renderAnalysisStudio,
  renderInspector,
  renderRiskEditForm,
  renderRiskHistory,
  type ShellState,
} from "./workbench/render.js";

function risk(overrides: Partial<RiskRecord> = {}): RiskRecord {
  return {
    contract_version: "p6-risk-api.v1",
    risk_id: "R-1",
    title: "Weather window",
    description: "",
    category: "schedule",
    status: "open",
    probability: 4,
    impact: 3,
    score: 12,
    exposure_level: "high",
    response_strategy: "mitigate",
    response_owner: null,
    response_due_date: null,
    owner: "owner",
    responsible_manager: null,
    date_identified: "2026-01-01",
    closure_note: null,
    revision: 3,
    ...overrides,
  };
}

function state(overrides: Partial<ShellState> = {}): ShellState {
  return {
    locale: "en",
    projectId: "p-1",
    context: {
      contract_version: "cubi-ai-workbench-context.v1",
      environment: "preview",
      project: {
        project_id: "p-1",
        name: "Project",
        revision: 7,
        settings_revision: 2,
        start_date: "2026-01-01",
        status: "active",
        date_system: "gregorian",
      },
      data_date: "2026-02-01",
      actor: { user_id: "u-1", roles: ["planner"] },
      permissions: { can_read: true, can_propose: true },
      studios: [],
    },
    plan: null,
    activeStudio: "risk-analysis",
    risks: [risk()],
    selectedRisk: "R-1",
    editingRisk: null,
    riskHistory: [],
    historyRisk: null,
    riskNotice: null,
    workspace: null,
    riskError: null,
    analysisError: null,
    baselines: [],
    baselineError: null,
    evm: null,
    evmError: null,
    evmBaselineId: "",
    evmCurrency: "",
    evmDataDate: "",
    loading: null,
    lastUpdated: null,
    connected: true,
    fallbackNotice: false,
    ...overrides,
  };
}

test("the edit form pre-fills stored values and the optimistic revision", () => {
  const html = renderRiskEditForm("en", risk());
  assert.match(html, /data-workbench="risk-edit-form"/);
  assert.match(html, /name="expected_revision" value="3"/);
  assert.match(html, /name="title" required maxlength="160" value="Weather window"/);
  assert.match(html, /<option value="mitigate" selected>/);
  assert.match(html, /<option value="open" selected>/);
});

test("the edit form escapes values from the stored record", () => {
  const html = renderRiskEditForm("en", risk({ title: `"><script>alert(1)</script>` }));
  assert.ok(!html.includes("<script>"));
  assert.match(html, /&quot;&gt;&lt;script&gt;alert\(1\)&lt;\/script&gt;/);
});

test("the history panel renders server events and an honest empty state", () => {
  const events: RiskHistoryEvent[] = [
    {
      contract_version: "p6-risk-api.v1",
      entity_type: "risk",
      entity_id: "R-1",
      revision: 3,
      event_type: "risk.updated",
      actor_id: "u-1",
      occurred_at: "2026-02-01T10:00:00+00:00",
      reason: "weekly review",
    },
  ];
  const html = renderRiskHistory("en", "R-1", events);
  assert.match(html, /data-risk-history/);
  assert.match(html, /risk\.updated/);
  assert.match(html, /weekly review/);
  assert.ok(!renderRiskHistory("en", "R-1", []).includes("data-risk-history"));
});

test("the inspector offers edit and history for a selected risk", () => {
  const html = renderInspector(state());
  assert.match(html, /data-workbench="edit-risk"/);
  assert.match(html, /data-workbench="show-history"/);
});

test("a read-only session sees history but no edit control", () => {
  const base = state();
  const readOnly = state({
    context: base.context ? { ...base.context, permissions: { can_read: true, can_propose: false } } : null,
  });
  const html = renderInspector(readOnly);
  assert.ok(!html.includes('data-workbench="edit-risk"'));
  assert.match(html, /data-workbench="show-history"/);
});

test("the inspector swaps to the edit form while editing", () => {
  const html = renderInspector(state({ editingRisk: "R-1" }));
  assert.match(html, /data-workbench="risk-edit-form"/);
  assert.ok(!html.includes('data-workbench="edit-risk"'));
});

function baseline(overrides: Partial<BaselineRecord> = {}): BaselineRecord {
  return {
    baseline_id: "BL-1",
    name: "Approved baseline",
    baseline_type: "PRIMARY",
    source_revision: 7,
    created_at: "2026-11-21T00:00:00+00:00",
    notes: null,
    ...overrides,
  };
}

function earnedValue(): EarnedValueSnapshot {
  return {
    contract_version: "p6-earned-value-read-model.v1",
    kind: "p6_earned_value_read_model",
    scope: { tenant_id: "t", project_id: "p-1", project_revision: 7 },
    baseline_id: "BL-1",
    data_date: "2026-10-01",
    currency: "USD",
    pv_method: "ACTIVITY_PERCENT_COMPLETE",
    earned_value: {
      planned_value: "125000.00",
      earned_value: "100000.00",
      actual_cost: "110000.00",
      cost_variance: "-10000.00",
      schedule_variance: "-25000.00",
      cost_performance_index: "0.9091",
      schedule_performance_index: "0.8000",
      etc_method: "REMAINING_COST",
      budget_at_completion: "200000.00",
      estimate_to_complete: "100000.00",
      estimate_at_completion: "210000.00",
      variance_at_completion: "-10000.00",
      performance_factor: null,
    },
  };
}

test("without a stored baseline the EVM section states INSUFFICIENT_DATA and offers no control", () => {
  const html = renderAnalysisStudio(state());
  assert.match(html, /data-evm-empty/);
  assert.match(html, /INSUFFICIENT_DATA/);
  assert.ok(!html.includes('data-workbench="evm-form"'));
});

test("a stored baseline exposes the explicit baseline, currency and data-date inputs", () => {
  const html = renderAnalysisStudio(
    state({ baselines: [baseline()], evmBaselineId: "BL-1", evmDataDate: "2026-10-01" }),
  );
  assert.match(html, /data-workbench="evm-form"/);
  assert.match(html, /name="currency" maxlength="3" value=""/);
  assert.match(html, /name="data_date" type="date" value="2026-10-01"/);
  assert.match(html, /<option value="BL-1" selected>Approved baseline \(BL-1\)<\/option>/);
});

test("EVM values are shown exactly as the server returned them", () => {
  const html = renderAnalysisStudio(
    state({ baselines: [baseline()], evmBaselineId: "BL-1", evm: earnedValue() }),
  );
  assert.match(html, /125000\.00/);
  assert.match(html, /0\.9091/);
  assert.match(html, /210000\.00/);
  assert.ok(!html.includes('data-evm-error'));
});

test("an authoritative EVM error is surfaced verbatim with no fabricated metrics", () => {
  const html = renderAnalysisStudio(
    state({ baselines: [baseline()], evmBaselineId: "BL-1", evmError: "EVM_BASELINE_ACTIVITIES_EMPTY:BL-1" }),
  );
  assert.match(html, /data-evm-error/);
  assert.match(html, /EVM_BASELINE_ACTIVITIES_EMPTY:BL-1/);
  assert.ok(!html.includes("Planned value"));
});
