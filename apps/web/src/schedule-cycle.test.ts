import assert from "node:assert/strict";
import test from "node:test";

import {
  buildSettingsRestoreRequest,
  filterScheduleReferences,
  type ScheduleCodeReferenceCatalog,
  type ScheduleSettingsDTO,
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

test("settings restore posts the selected values at the current revision", () => {
  const revision: ScheduleSettingsDTO = {
    contract_version: "p6-project-schedule-settings-api.v1",
    kind: "project_schedule_settings",
    scope: { tenant_id: "T-1", project_id: "P-1", project_revision: 7 },
    record_revision: 2,
    mode: "DATE_BASED",
    project_calendar: {
      calendar_id: "CAL-1", calendar_version: "1",
      kind: "working-day", system: "gregorian",
    },
    project_start: "2026-09-21",
    project_finish: null,
    schedule_options: { mode: "ALAP" },
    project_leveling_priority: 10,
  };

  assert.deepEqual(buildSettingsRestoreRequest(revision, 5), {
    contract_version: "p6-project-schedule-settings-api.v1",
    expected_record_revision: 5,
    mode: "DATE_BASED",
    project_calendar_id: "CAL-1",
    project_calendar_version: "1",
    project_calendar_system: "gregorian",
    project_start: "2026-09-21",
    project_finish: null,
    schedule_options: { mode: "ALAP" },
    project_leveling_priority: 10,
  });
});
