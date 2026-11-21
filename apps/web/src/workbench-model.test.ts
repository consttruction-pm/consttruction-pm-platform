import assert from "node:assert/strict";
import test from "node:test";
import {
  STUDIO_ORDER,
  analysisCounts,
  escapeHtml,
  metricRows,
  metricSourceSummary,
  planAction,
  proposalImpact,
  readQuery,
  riskMatrix,
  statusTone,
  studioLabel,
  t,
  verifiedHelpUrl,
  withProject,
  workspaceWbsNodes,
} from "./workbench/model.js";
import type {
  AIActionProposal,
  RiskRecord,
  WorkbenchCommandPlan,
  WorkspaceReadSnapshot,
} from "./workbench/api.js";

function risk(overrides: Partial<RiskRecord>): RiskRecord {
  return {
    contract_version: "risk.v1",
    risk_id: "R-1",
    title: "Risk",
    description: "",
    category: "schedule",
    status: "open",
    probability: 3,
    impact: 3,
    score: 9,
    exposure_level: "medium",
    response_strategy: "mitigate",
    response_owner: null,
    response_due_date: null,
    owner: "owner",
    responsible_manager: null,
    date_identified: "2026-01-01",
    closure_note: null,
    revision: 1,
    ...overrides,
  };
}

function plan(overrides: Partial<WorkbenchCommandPlan>): WorkbenchCommandPlan {
  return {
    contract_version: "cubi-ai-workbench-command.v1",
    correlation_id: "wb-1",
    command: "show risks",
    intent: "risk",
    studio: "risk-analysis",
    status: "ready",
    can_open: true,
    can_execute: true,
    refusal: null,
    reason: null,
    missing_inputs: [],
    questions: [],
    facts: [],
    calculated: [],
    assumptions: [],
    recommendations: [],
    objective: null,
    constraints: [],
    evidence: "",
    project: { project_id: "P-1", revision: 1 },
    resolved_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

test("studio labels are localized and the studio order is stable", () => {
  assert.equal(studioLabel("en", "risk-analysis"), "Risk Analysis Studio");
  assert.equal(studioLabel("fa", "risk-analysis"), "کارگاه تحلیل ریسک");
  assert.equal(studioLabel("en", "unknown-studio"), "unknown-studio");
  assert.deepEqual(STUDIO_ORDER, [
    "import-staging",
    "schedule-scenario",
    "risk-analysis",
    "project-analysis",
    "decision-approval",
  ]);
});

test("translation falls back to English and Persian keeps the Persian value", () => {
  assert.equal(t("en", "Revision", "نسخه"), "Revision");
  assert.equal(t("fa", "Revision", "نسخه"), "نسخه");
  // Unsupported locale keeps the identifiable English fallback.
  assert.equal(t("xx", "Revision", "نسخه"), "Revision");
});

test("every dynamic value is escaped", () => {
  assert.equal(
    escapeHtml('<img src=x onerror="alert(1)">'),
    "&lt;img src=x onerror=&quot;alert(1)&quot;&gt;",
  );
  assert.equal(escapeHtml("plain & simple"), "plain &amp; simple");
});

test("status tone maps to the documented vocabulary only", () => {
  assert.equal(statusTone("LIVE_VERIFIED"), "is-live");
  assert.equal(statusTone("WIRED_WRITE"), "is-live");
  assert.equal(statusTone("WIRED_READ"), "is-read");
  assert.equal(statusTone("PARTIAL"), "is-partial");
  assert.equal(statusTone("BLOCKED"), "is-blocked");
  assert.equal(statusTone("SHELL_ONLY"), "is-planned");
  assert.equal(statusTone("PLANNED"), "is-planned");
});

test("a plan opens a studio only when the server allows it", () => {
  const open = planAction(plan({}));
  assert.equal(open.openStudio, "risk-analysis");
  assert.equal(open.blocked, false);

  const blocked = planAction(
    plan({ studio: "schedule-scenario", can_open: false, can_execute: false, status: "blocked" }),
  );
  assert.equal(blocked.openStudio, null);
  assert.equal(blocked.blocked, true);

  const unknown = planAction(plan({ studio: null, intent: "unknown", can_open: false }));
  assert.equal(unknown.openStudio, null);
  assert.equal(unknown.blocked, false);
});

test("a plan surfaces the first clarifying question", () => {
  const action = planAction(
    plan({
      studio: null,
      can_open: false,
      questions: [
        {
          id: "studio",
          prompt: "Which studio?",
          options: [{ value: "risk-analysis", label: "Risk" }],
          allow_unknown: true,
        },
      ],
    }),
  );
  assert.equal(action.question?.id, "studio");
  assert.equal(action.question?.options[0].value, "risk-analysis");
});

test("risk matrix groups stored ratings without recalculating them", () => {
  const cells = riskMatrix([
    risk({ risk_id: "R-1", probability: 5, impact: 4 }),
    risk({ risk_id: "R-2", probability: 5, impact: 4 }),
    risk({ risk_id: "R-3", probability: 1, impact: 1 }),
  ]);
  assert.equal(cells.length, 25);
  const top = cells[0];
  assert.equal(top.probability, 5);
  assert.equal(top.impact, 1);
  const cell = cells.find((item) => item.probability === 5 && item.impact === 4);
  assert.deepEqual(cell?.risks.map((item) => item.risk_id), ["R-1", "R-2"]);
  const low = cells.find((item) => item.probability === 1 && item.impact === 1);
  assert.equal(low?.risks.length, 1);
});

test("analysis counts read server rows and never derive a forecast", () => {
  assert.equal(analysisCounts(null), null);
  const snapshot: WorkspaceReadSnapshot = {
    contract_version: "v2",
    context: { tenant_id: "t", project_id: "p", revision: 1 },
    workspace: {
      activities: [
        { id: "A1", gantt: { critical: true } },
        { id: "A2", gantt: { critical: false } },
        { id: "A3" },
      ],
      wbs: [{ wbs_id: "W1" }],
      relationships: [{ id: "L1" }, { id: "L2" }],
    },
    control_intelligence: null,
  };
  assert.deepEqual(analysisCounts(snapshot), {
    activities: 3,
    wbs: 1,
    relationships: 2,
    critical: 1,
  });
});

test("stored metrics are presented as-is in a stable order", () => {
  const snapshot: WorkspaceReadSnapshot = {
    contract_version: "v2",
    context: { tenant_id: "t", project_id: "p", revision: 1 },
    workspace: {},
    control_intelligence: {
      contract_version: "v1",
      result_id: "r-1",
      scope: { tenant_id: "t", project_id: "p", project_revision: 1 },
      generated_at: "2026-01-01T00:00:00Z",
      summary_key: "control",
      metrics: { schedule_variance_days: -4, activity_count: 12, ignored: "x" as unknown as number },
      source_refs: [
        { id: "s1", label: "P6 schedule" },
        { id: "s1", label: "P6 schedule" },
        { kind: "baseline" },
      ],
    },
  };
  const rows = metricRows(snapshot);
  assert.deepEqual(
    rows.map((row) => row.key),
    ["activity_count", "schedule_variance_days"],
  );
  assert.equal(rows[1].value, -4);
  assert.deepEqual(metricSourceSummary(snapshot), ["P6 schedule", "baseline"]);
});

test("query and project helpers preserve only what they are asked to", () => {
  assert.equal(readQuery("project=P-1&lang=fa", "lang"), "fa");
  assert.equal(readQuery("project=P-1", "lang"), null);
  assert.equal(withProject("/ai-workbench?lang=fa", "P-1"), "/ai-workbench?lang=fa&project=P-1");
});

function snapshot(overrides: Partial<WorkspaceReadSnapshot["workspace"]> = {}): WorkspaceReadSnapshot {
  return {
    contract_version: "workspace-control-room-read.v2",
    context: { tenant_id: "t", project_id: "p", revision: 4 },
    workspace: {
      activities: [
        {
          id: "A1",
          wbs_id: "WBS-1",
          name: "Existing activity",
          cells: { duration: "3" },
          gantt: { critical: true },
        },
        { id: "A2", wbs_id: "WBS-2", name: "Second", cells: { duration: "2" } },
      ],
      wbs_nodes: [
        { wbs_id: "WBS-1", local_code: "1", name: "Civil works" },
        { wbs_id: "WBS-2", local_code: "2", name: "Electrical" },
      ],
      relationships: [{ relationship_id: "L1" }],
      ...overrides,
    },
    control_intelligence: null,
  };
}

function proposal(overrides: Partial<AIActionProposal> = {}): AIActionProposal {
  return {
    proposal_id: "prop-1",
    tool_name: "activity.create",
    action: "create",
    status: "proposed",
    requires_human_approval: true,
    requested_by: "u-1",
    evidence_refs: [],
    project_revision_id: "4",
    resource_domain: "activities",
    payload: {
      activity_id: "A-NEW",
      name: "New activity",
      duration_value: "5",
      duration_unit: "working-day",
      wbs_id: "WBS-1",
    },
    result: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    decided_by: null,
    is_stale: false,
    ...overrides,
  };
}

test("canonical wbs_nodes drive the WBS count instead of the legacy field", () => {
  const canonical = snapshot();
  assert.equal(workspaceWbsNodes(canonical).length, 2);
  assert.deepEqual(analysisCounts(canonical), {
    activities: 2,
    wbs: 2,
    relationships: 1,
    critical: 1,
  });
  // The legacy shape stays readable; it is not silently dropped.
  const legacy = snapshot({ wbs_nodes: undefined, wbs: [{ wbs_id: "WBS-1" }] });
  assert.equal(analysisCounts(legacy)?.wbs, 1);
});

test("proposal impact compares the literal payload with the current read", () => {
  const impact = proposalImpact(snapshot(), proposal());
  assert.ok(impact);
  assert.equal(impact?.exists, false);
  assert.equal(impact?.current, null);
  assert.equal(impact?.proposed.wbsLabel, "1 Civil works");
  assert.deepEqual(impact?.warnings, []);
});

test("proposal impact names an existing activity and an unknown WBS without calculating", () => {
  const existing = proposalImpact(
    snapshot(),
    proposal({
      payload: {
        activity_id: "A1",
        name: "Changed name",
        duration_value: "9",
        duration_unit: "working-hour",
        wbs_id: "WBS-MISSING",
      },
    }),
  );
  assert.equal(existing?.exists, true);
  assert.equal(existing?.current?.name, "Existing activity");
  assert.equal(existing?.current?.wbsLabel, "1 Civil works");
  assert.equal(existing?.current?.duration, "3");
  assert.deepEqual(existing?.warnings, ["WBS_NOT_IN_CURRENT_READ", "ACTIVITY_ID_EXISTS"]);
});

test("proposal impact declares an unavailable current read and ignores other tools", () => {
  const unavailable = proposalImpact(null, proposal());
  assert.deepEqual(unavailable?.warnings, ["CURRENT_STATE_UNAVAILABLE"]);
  assert.equal(unavailable?.proposed.name, "New activity");
  assert.equal(
    proposalImpact(snapshot(), proposal({ tool_name: "project.plan.create" })),
    null,
  );
});


test("only a recorded Oracle reference becomes a help link", () => {
  assert.equal(
    verifiedHelpUrl("https://docs.oracle.com/cd/G48902_01/client_help/en_US/risks.htm"),
    "https://docs.oracle.com/cd/G48902_01/client_help/en_US/risks.htm",
  );
  assert.equal(verifiedHelpUrl("https://example.test/risks.htm"), null);
  assert.equal(verifiedHelpUrl("http://docs.oracle.com/risks.htm"), null);
  assert.equal(verifiedHelpUrl("javascript:alert(1)"), null);
  assert.equal(verifiedHelpUrl(null), null);
  assert.equal(verifiedHelpUrl(""), null);
});
