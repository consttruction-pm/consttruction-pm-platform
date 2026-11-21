import assert from "node:assert/strict";
import test from "node:test";
import type { AIActionProposal, BaselineRecord, EarnedValueSnapshot, RiskHistoryEvent, RiskRecord, WorkspaceReadSnapshot } from "./workbench/api.js";
import {
  renderAnalysisStudio,
  renderDecisionStudio,
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
    proposals: [],
    proposalError: null,
    proposalNotice: null,
    proposalBusy: null,
    impactError: null,
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

function proposal(overrides: Partial<AIActionProposal> = {}): AIActionProposal {
  return {
    proposal_id: "AIA-1",
    tool_name: "activity.create",
    action: "create",
    status: "proposed",
    requires_human_approval: true,
    requested_by: "u-planner",
    evidence_refs: ["workspace:7"],
    project_revision_id: "7",
    resource_domain: "schedule",
    payload: { activity_id: "AIW-1", wbs_id: "WBS-1", name: "<New>" },
    result: null,
    created_at: "2026-11-21T09:00:00+00:00",
    updated_at: "2026-11-21T09:00:00+00:00",
    decided_by: null,
    is_stale: false,
    ...overrides,
  };
}

test("a read-only session sees no proposal list at all", () => {
  const html = renderDecisionStudio(
    state({
      context: { ...state().context!, permissions: { can_read: true, can_propose: false } },
      proposals: [proposal()],
    }),
  );
  assert.match(html, /data-decision-readonly/);
  assert.ok(!html.includes("data-proposal="));
  assert.ok(!html.includes("data-workbench=\"decide-proposal\""));
});

test("an empty proposal store is stated honestly without inventing a row", () => {
  const html = renderDecisionStudio(state());
  assert.match(html, /data-decision-empty/);
  assert.match(html, /No proposal is stored/);
  assert.ok(!html.includes("data-proposal="));
});

test("a pending proposal exposes approve and reject with the escaped payload", () => {
  const html = renderDecisionStudio(state({ proposals: [proposal()] }));
  assert.match(html, /data-decision-list/);
  assert.match(html, /activity\.create/);
  assert.match(html, /data-proposal="AIA-1"/);
  assert.match(html, /data-approved="true"/);
  assert.match(html, /data-approved="false"/);
  assert.ok(!html.includes("data-workbench=\"execute-proposal\""));
  assert.ok(html.includes("&lt;New&gt;"));
});

test("an approved proposal offers execution and no further decision", () => {
  const html = renderDecisionStudio(state({ proposals: [proposal({ status: "approved" })] }));
  assert.match(html, /data-workbench="execute-proposal"/);
  assert.ok(!html.includes("data-workbench=\"decide-proposal\""));
});

test("a stale proposal cannot be approved or executed", () => {
  const html = renderDecisionStudio(
    state({ proposals: [proposal({ is_stale: true })] }),
  );
  assert.match(html, /data-proposal-stale/);
  assert.ok(!html.includes("data-workbench=\"decide-proposal\""));
  assert.ok(!html.includes("data-workbench=\"execute-proposal\""));
});

test("an executed proposal shows the canonical result and decision maker", () => {
  const html = renderDecisionStudio(
    state({
      proposals: [
        proposal({
          status: "executed",
          decided_by: "u-planner",
          result: { activity: { activity_id: "AIW-1" } },
        }),
      ],
    }),
  );
  assert.match(html, /u-planner/);
  assert.match(html, /AIW-1/);
  assert.ok(!html.includes("data-workbench=\"decide-proposal\""));
});

test("a proposal read error is surfaced with its stable code", () => {
  const html = renderDecisionStudio(state({ proposalError: "AUTHORIZATION_DENIED" }));
  assert.match(html, /data-decision-error/);
  assert.match(html, /AUTHORIZATION_DENIED/);
});

function workspace(): WorkspaceReadSnapshot {
  return {
    contract_version: "workspace-control-room-read.v2",
    context: { tenant_id: "t", project_id: "p-1", revision: 7 },
    workspace: {
      activities: [
        { id: "AIW-1", wbs_id: "WBS-1", name: "Existing activity", cells: { duration: "1" } },
      ],
      wbs_nodes: [{ wbs_id: "WBS-1", local_code: "1", name: "Civil works" }],
      relationships: [{ relationship_id: "L1" }],
    },
    control_intelligence: null,
  };
}

function activityProposal(activityId: string): AIActionProposal {
  return proposal({
    payload: {
      activity_id: activityId,
      name: "New activity",
      duration_value: "5",
      duration_unit: "working-day",
      wbs_id: "WBS-1",
    },
  });
}

test("analysis counts read the canonical wbs_nodes collection", () => {
  const html = renderAnalysisStudio(state({ workspace: workspace() }));
  assert.match(html, /<span>Activities<\/span><strong>1<\/strong>/);
  assert.match(html, /<span>WBS elements<\/span><strong>1<\/strong>/);
  assert.match(html, /<span>Relationships<\/span><strong>1<\/strong>/);
});

test("a pending activity proposal is compared with the canonical current read", () => {
  const html = renderDecisionStudio(
    state({ workspace: workspace(), proposals: [activityProposal("AIW-NEW")] }),
  );
  assert.match(html, /data-proposal-impact="activity.create"/);
  assert.match(html, /Civil works/);
  assert.match(html, /New activity/);
  assert.match(html, /Not present in the current read/);
  assert.match(html, /Literal comparison/);
  assert.ok(!html.includes('data-impact-warning="ACTIVITY_ID_EXISTS"'));
});

test("an existing activity and a missing WBS are review warnings, not calculations", () => {
  const html = renderDecisionStudio(
    state({
      workspace: workspace(),
      proposals: [
        proposal({
          payload: {
            activity_id: "AIW-1",
            name: "Changed name",
            duration_value: "2",
            duration_unit: "working-day",
            wbs_id: "WBS-MISSING",
          },
        }),
      ],
    }),
  );
  assert.match(html, /data-impact-warning="ACTIVITY_ID_EXISTS"/);
  assert.match(html, /data-impact-warning="WBS_NOT_IN_CURRENT_READ"/);
  assert.match(html, /Existing activity/);
});

test("an unavailable current read is declared instead of fabricated", () => {
  const html = renderDecisionStudio(
    state({
      workspace: null,
      impactError: "WORKSPACE_READ_FAILED",
      proposals: [activityProposal("AIW-NEW")],
    }),
  );
  assert.match(html, /data-impact-error="WORKSPACE_READ_FAILED"/);
  assert.match(html, /data-impact-warning="CURRENT_STATE_UNAVAILABLE"/);
});
