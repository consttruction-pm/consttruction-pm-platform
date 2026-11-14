import assert from "node:assert/strict";
import test from "node:test";

import {
  extractScheduleCheck,
  filterScheduleReferences,
  renderScheduleCheck,
  type ScheduleCodeReferenceCatalog,
} from "./schedule-cycle.js";

const catalog: ScheduleCodeReferenceCatalog = {
  contract_version: "schedule-code-reference.v1",
  reference_version: "0.8.7",
  as_of: "2026-10-23",
  summary: {
    requirement_count: 2,
    formula_count: 1,
    option_count: 1,
    option_status: { mapped_unverified: 1, known_gap: 0, not_inventoried: 0 },
    option_registry_valid: true,
    requirement_status: { mapped_unverified: 1, known_gap: 1, not_inventoried: 0 },
    documentation_review: {},
    parity_claimed_complete: false,
  },
  requirements: [
    {
      id: "SCH-001", area: "Scheduling / CPM", feature: "Early dates",
      description: "Calculate early start and finish from immutable inputs.",
      options: ["Data Date", "Schedule mode"], status: "mapped_unverified",
      known_gap: "", acceptance_evidence: [],
    },
    {
      id: "RES-001", area: "Resources", feature: "Resource leveling",
      description: "Respect resource calendars and effective capacity.",
      options: ["Capacity", "Priority"], status: "known_gap",
      known_gap: "Persistent capacity facts are not yet wired to the production query.",
      acceptance_evidence: [],
    },
  ],
  option_reference_version: "0.9.2",
  option_reference_as_of: "2026-10-23",
  formulas: [
    {
      id: "FRM-TF-001", feature: "Total Float",
      algorithm: "Selected late boundary minus early boundary.",
      inputs: ["early start", "late start"], options: ["Start Float", "Finish Float"],
      calendar_rules: "Use the project calculation calendar.", edge_cases: [],
      status: "unverified", known_gap: "",
    },
  ],
  options: [
    {
      id: "OPT-SCH-001", requirement_id: "SCH-001", area: "Scheduling / CPM",
      menu_path: "Schedule > Options", name: "Total Float calculation",
      values: ["Start Float", "Finish Float"], behavior: "Selects which early/late boundary drives float.",
      inputs: ["Early Start", "Late Start"], outputs: ["Total Float"],
      status: "mapped_unverified", known_gap: "",
      implementation_mapping_count: 2, regression_test_count: 1,
    },
  ],
  schedule_options_schema: [],
};

test("reference explorer searches feature, option and gap text", () => {
  const byOption = filterScheduleReferences(catalog, "data date", "all", "all");
  assert.deepEqual(byOption.requirements.map((item) => item.id), ["SCH-001"]);
  assert.deepEqual(byOption.formulas, []);

  const byGap = filterScheduleReferences(catalog, "persistent capacity", "all", "all");
  assert.deepEqual(byGap.requirements.map((item) => item.id), ["RES-001"]);
});

test("reference explorer filters evidence status and area separately", () => {
  const knownGaps = filterScheduleReferences(catalog, "", "known_gap", "all");
  assert.deepEqual(knownGaps.requirements.map((item) => item.id), ["RES-001"]);
  assert.deepEqual(knownGaps.formulas, []);
  assert.deepEqual(knownGaps.options, []);

  const resourceOnly = filterScheduleReferences(catalog, "", "all", "Resources");
  assert.deepEqual(resourceOnly.requirements.map((item) => item.id), ["RES-001"]);
  assert.deepEqual(resourceOnly.formulas, []);
  assert.deepEqual(resourceOnly.options.map((item) => item.id), []);
});

test("reference explorer can show formula-only results", () => {
  const result = filterScheduleReferences(catalog, "total float", "all", "all", "formulas");
  assert.deepEqual(result.requirements, []);
  assert.deepEqual(result.formulas.map((item) => item.id), ["FRM-TF-001"]);
  const optionResult = filterScheduleReferences(catalog, "total float", "all", "all", "options");
  assert.deepEqual(optionResult.options.map((item) => item.id), ["OPT-SCH-001"]);
  assert.deepEqual(optionResult.requirements, []);
  assert.deepEqual(optionResult.formulas, []);
});

const checkLabels = {
  checkTitle: "Schedule check",
  checkIntro: "Explicit checks.",
  checkRerunHint: "Re-run after fixes.",
  checkScope: "Scope",
  checkTotal: "Findings",
  checkErrors: "Errors",
  checkWarnings: "Warnings",
  checkInfo: "Info",
  checkRule: "Condition",
  checkSeverity: "Severity",
  checkCount: "Count",
  checkFindings: "Affected facts",
  checkNoFindings: "No findings.",
  checkOpenActivity: "Open activity",
  severityError: "Error",
  severityWarning: "Warning",
  severityInfo: "Info",
  ruleNegativeFloat: "Negative total float",
  ruleOpenStart: "No predecessor",
  ruleOpenFinish: "No successor",
  ruleActivityConstraint: "Activity constraint",
  ruleMandatoryConstraint: "Mandatory constraint",
  ruleNegativeLag: "Negative relationship lag",
};

const checkDocument = {
  schedule_check: {
    contract_version: "p6-schedule-check.v1",
    kind: "schedule_check",
    scope: { tenant_id: "T-1", project_id: "P-1", project_revision: 4 },
    snapshot_id: "SNAP-1",
    snapshot_hash: "a".repeat(64),
    calculation_run_identity: "b".repeat(64),
    counts: { total: 2, ERROR: 0, WARNING: 1, INFO: 1 },
    rules: [
      { rule_id: "NEGATIVE_FLOAT", severity: "WARNING", count: 0 },
      { rule_id: "OPEN_START", severity: "WARNING", count: 1 },
      { rule_id: "OPEN_FINISH", severity: "WARNING", count: 0 },
      { rule_id: "ACTIVITY_CONSTRAINT", severity: "INFO", count: 1 },
      { rule_id: "MANDATORY_CONSTRAINT", severity: "WARNING", count: 0 },
      { rule_id: "NEGATIVE_LAG", severity: "INFO", count: 0 },
    ],
    findings: [
      {
        rule_id: "OPEN_START",
        severity: "WARNING",
        message: "activity A100 has no predecessor",
        activity_id: "A100",
        relationship_id: null,
        constraint_id: null,
        details: { predecessor_count: 0 },
      },
      {
        rule_id: "ACTIVITY_CONSTRAINT",
        severity: "INFO",
        message: "activity A140 carries START_NO_EARLIER_THAN on 2026-10-20",
        activity_id: "A140",
        relationship_id: null,
        constraint_id: null,
        details: { constraint_type: "START_NO_EARLIER_THAN", constraint_date: "2026-10-20" },
      },
    ],
  },
};

test("schedule check document is parsed as returned by the server", () => {
  const check = extractScheduleCheck(checkDocument);
  assert.ok(check);
  assert.equal(check.total, 2);
  assert.deepEqual(check.counts, { error: 0, warning: 1, info: 1 });
  assert.equal(check.rules.length, 6);
  assert.equal(check.rules[0].count, 0);
  assert.equal(check.findings[1].activityId, "A140");
  assert.equal(check.findings[1].details.constraint_date, "2026-10-20");
  assert.equal(check.snapshotId, "SNAP-1");
  assert.deepEqual(check.scope, { projectId: "P-1", projectRevision: 4 });
});

test("missing schedule check blocks are ignored and malformed ones fail", () => {
  assert.equal(extractScheduleCheck({}), null);
  assert.equal(extractScheduleCheck({ schedule_check: { contract_version: "old" } }), null);
  const invalid = {
    schedule_check: {
      ...checkDocument.schedule_check,
      rules: [{ rule_id: "OPEN_START", severity: "SEVERE", count: 1 }],
    },
  };
  assert.throws(() => extractScheduleCheck(invalid), /INVALID_SCHEDULE_CHECK_SEVERITY/);
});

test("schedule check markup lists every rule and links a finding to its activity", () => {
  const check = extractScheduleCheck(checkDocument);
  assert.ok(check);
  const markup = renderScheduleCheck(check, checkLabels);
  assert.match(markup, /data-schedule-check/);
  assert.match(markup, /data-check-total="2"/);
  assert.match(markup, /data-check-scope="P-1@4"/);
  assert.match(markup, /data-check-rule="NEGATIVE_FLOAT"[^>]*data-check-count="0"/);
  assert.match(markup, /data-check-rule="OPEN_FINISH"/);
  assert.match(markup, /data-check-finding data-check-rule="OPEN_START"/);
  assert.match(markup, /data-check-focus="A100"/);
  assert.match(markup, /START_NO_EARLIER_THAN · 2026-10-20/);
  assert.match(markup, />No predecessor</);
});
