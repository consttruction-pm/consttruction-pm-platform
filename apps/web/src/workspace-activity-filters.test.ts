import assert from "node:assert/strict";
import test from "node:test";

import {
  activityFilterChoiceValues,
  activityMatchesFilter,
  applyActivityFilterState,
  copyActivityFilterAsLayout,
  deleteActivityFilter,
  describeActivityFilter,
  duplicateActivityFilter,
  EMPTY_ACTIVITY_FILTERS,
  filterActivitiesByDefinition,
  findActivityFilter,
  getBuiltinActivityFilters,
  makeGlobalActivityFilter,
  normalizeActivityFilter,
  normalizeActivityFilterState,
  optimizeActivityFilterCriteria,
  pasteActivityFilter,
  previewActivityFilter,
  resolveFilterDateValue,
  selectActivityFilter,
  setActiveActivityFilter,
  setActivityFilterAllActivities,
  setActivityFilterApplyMode,
  setActivityFilterCombine,
  upsertActivityFilter,
  validateActivityFilterCriterion,
  type ActivityFilterDefinition,
  type ActivityFilterState,
} from "./workspace-activity-filters.js";
import { normalizePresentation, DEFAULT_PRESENTATION } from "./workspace-presentation.js";
import type { WorkspaceActivityRow } from "./workspace-model.js";

const rows: readonly WorkspaceActivityRow[] = [
  {
    id: "A100", code: "A100", wbsId: "1 Project management", name: "Project kickoff",
    cells: {
      "activity.status": "Completed",
      "activity.type": "Task Dependent",
      "progress": 100,
      "duration": "1",
      "activity.total_float": 0,
      "activity.is_critical": true,
    },
  },
  {
    id: "A130", code: "A130", wbsId: "2 Civil works", name: "Earthworks",
    cells: {
      "activity.status": "In Progress",
      "activity.type": "Task Dependent",
      "progress": 37.5,
      "duration": "8",
      "activity.total_float": -2,
      "activity.is_critical": true,
    },
  },
  {
    id: "A140", code: "A140", wbsId: "2 Civil works", name: "Piling and foundations",
    cells: {
      "activity.status": "Not Started",
      "activity.type": "Start Milestone",
      "duration": "10",
      "activity.is_critical": false,
    },
  },
  {
    id: "A150", code: "A150", wbsId: "3 Procurement", name: "Structural steel procurement",
    cells: { "activity.status": "Not Started" },
  },
];

function ids(rowsToMap: readonly WorkspaceActivityRow[]): string[] {
  return rowsToMap.map((row) => row.id);
}

test("predefined filters follow the documented P6 activity criteria", () => {
  const builtin = getBuiltinActivityFilters();
  const inProgress = findActivityFilter(EMPTY_ACTIVITY_FILTERS, "builtin:in-progress");
  const completed = findActivityFilter(EMPTY_ACTIVITY_FILTERS, "builtin:completed");
  const notStarted = findActivityFilter(EMPTY_ACTIVITY_FILTERS, "builtin:not-started");
  const critical = findActivityFilter(EMPTY_ACTIVITY_FILTERS, "builtin:critical");
  const negativeFloat = findActivityFilter(EMPTY_ACTIVITY_FILTERS, "builtin:negative-float");
  const milestones = findActivityFilter(EMPTY_ACTIVITY_FILTERS, "builtin:milestones");

  assert.deepEqual(ids(filterActivitiesByDefinition(rows, inProgress)), ["A130"]);
  assert.deepEqual(ids(filterActivitiesByDefinition(rows, completed)), ["A100"]);
  assert.deepEqual(ids(filterActivitiesByDefinition(rows, notStarted)), ["A140", "A150"]);
  assert.deepEqual(ids(filterActivitiesByDefinition(rows, critical)), ["A100", "A130"]);
  assert.deepEqual(ids(filterActivitiesByDefinition(rows, negativeFloat)), ["A130"]);
  assert.deepEqual(ids(filterActivitiesByDefinition(rows, milestones)), ["A140"]);
  assert.ok(builtin.length >= 7);
  assert.ok(builtin.every((filter) => filter.builtin === true));
  assert.equal(filterActivitiesByDefinition(rows, null), rows);
});

test("custom filters combine criteria with AND or OR and ignore blank rows", () => {
  const all: ActivityFilterDefinition = {
    id: "custom:civil-open",
    name: "Civil open",
    match: "all",
    criteria: [
      { fieldId: "wbs", operator: "contains", value: "civil" },
      { fieldId: "activity_status", operator: "not-equals", value: "completed" },
      { fieldId: "activity_name", operator: "contains", value: "" },
    ],
  };
  assert.deepEqual(ids(filterActivitiesByDefinition(rows, all)), ["A130", "A140"]);

  const any: ActivityFilterDefinition = {
    id: "custom:at-risk",
    name: "At risk",
    match: "any",
    criteria: [
      { fieldId: "total_float", operator: "less-than", value: "0" },
      { fieldId: "progress", operator: "greater-than", value: "50" },
    ],
  };
  assert.deepEqual(ids(filterActivitiesByDefinition(rows, any)), ["A100", "A130"]);

  assert.equal(activityMatchesFilter(rows[3], all), false);
  assert.equal(activityMatchesFilter(rows[1], {
    ...all,
    criteria: [{ fieldId: "duration", operator: "equals", value: "8" }],
  }), true);
});

test("empty and boolean filters are evaluated against the real cell aliases", () => {
  const emptyFloat = normalizeActivityFilter({
    name: "No float fact",
    match: "all",
    criteria: [{ fieldId: "total_float", operator: "is-empty", value: "" }],
  });
  assert.deepEqual(ids(filterActivitiesByDefinition(rows, emptyFloat)), ["A140", "A150"]);

  const notEmpty = normalizeActivityFilter({
    name: "Has status",
    match: "all",
    criteria: [{ fieldId: "activity_status", operator: "is-not-empty", value: "" }],
  });
  assert.deepEqual(ids(filterActivitiesByDefinition(rows, notEmpty)), ["A100", "A130", "A140", "A150"]);

  const nonCritical = normalizeActivityFilter({
    name: "Non critical",
    match: "all",
    criteria: [{ fieldId: "is_critical", operator: "equals", value: "false" }],
  });
  assert.deepEqual(ids(filterActivitiesByDefinition(rows, nonCritical)), ["A140"]);
  // A150 has no persisted critical fact, so it is not asserted as non-critical.
  assert.equal(activityMatchesFilter(rows[3], nonCritical), false);
});

test("saved filters normalize, deduplicate, edit and delete immutably", () => {
  const first = normalizeActivityFilter({
    name: "Civil open",
    match: "all",
    criteria: [{ fieldId: "wbs", operator: "contains", value: "Civil" }],
  });
  assert.ok(first);
  assert.equal(first.id, "custom:civil-open");

  let state = upsertActivityFilter(EMPTY_ACTIVITY_FILTERS, first);
  assert.equal(state.activeId, "custom:civil-open");
  assert.equal(state.saved.length, 1);

  const edited = normalizeActivityFilter({
    name: "Civil open",
    match: "any",
    criteria: [{ fieldId: "wbs", operator: "contains", value: "Procurement" }],
  });
  assert.ok(edited);
  state = upsertActivityFilter(state, edited);
  assert.equal(state.saved.length, 1);
  assert.equal(state.saved[0].match, "any");
  assert.equal(state.saved[0].criteria[0].value, "Procurement");

  const builtin = setActiveActivityFilter(state, "builtin:completed");
  assert.equal(builtin.activeId, "builtin:completed");
  assert.equal(findActivityFilter(state, "builtin:completed")?.name, "Completed");
  assert.equal(setActiveActivityFilter(state, "missing").activeId, null);

  const deleted = deleteActivityFilter(builtin, "custom:civil-open");
  assert.equal(deleted.saved.length, 0);
  assert.equal(deleted.activeId, "builtin:completed");

  const normalized = normalizeActivityFilterState({
    saved: [
      { name: "Civil open", match: "all", criteria: [{ fieldId: "wbs", operator: "contains", value: "Civil" }] },
      { name: "Civil open", match: "all", criteria: [{ fieldId: "wbs", operator: "contains", value: "Civil" }] },
      { name: "", match: "all", criteria: [] },
      { name: "Bad field", criteria: [{ fieldId: "secret", operator: "equals", value: "x" }] },
    ],
    activeId: "custom:civil-open",
  });
  assert.equal(normalized.saved.length, 1);
  assert.equal(normalized.activeId, "custom:civil-open");
  assert.equal(describeActivityFilter(normalized.saved[0], "en"), "WBS contains Civil");
});

test("presentation normalization keeps saved filters and defaults old layouts", () => {
  const normalized = normalizePresentation({
    table: DEFAULT_PRESENTATION.table,
    bars: DEFAULT_PRESENTATION.bars,
    filters: {
      saved: [{ name: "Civil", match: "all", criteria: [{ fieldId: "wbs", operator: "contains", value: "Civil" }] }],
      activeId: "custom:civil",
    },
  });
  assert.equal(normalized.filters.saved.length, 1);
  assert.equal(normalized.filters.activeId, "custom:civil");

  const legacy = normalizePresentation({ table: DEFAULT_PRESENTATION.table, bars: DEFAULT_PRESENTATION.bars });
  assert.equal(legacy.filters.activeId, null);
  assert.deepEqual(legacy.filters.saved, []);
});

test("WBS criteria match the displayed code and name, not the internal node id", () => {
  const internal: readonly WorkspaceActivityRow[] = [
    { id: "A120", code: "A120", wbsId: "WBS-RPS-CIVIL", name: "Site survey", cells: {} },
    { id: "A150", code: "A150", wbsId: "WBS-RPS-PROC", name: "Steel procurement", cells: {} },
  ];
  const nodes = [
    { id: "WBS-RPS-CIVIL", localCode: "2", name: "Civil works" },
    { id: "WBS-RPS-PROC", localCode: "3", name: "Procurement" },
  ];
  const procurement = normalizeActivityFilter({
    name: "Procurement",
    match: "all",
    criteria: [{ fieldId: "wbs", operator: "contains", value: "Procurement" }],
  });
  assert.ok(procurement);
  assert.deepEqual(ids(filterActivitiesByDefinition(internal, procurement, nodes)), ["A150"]);

  // The database key is not a user value and must not match.
  const internalId = normalizeActivityFilter({
    name: "Internal id",
    match: "all",
    criteria: [{ fieldId: "wbs", operator: "contains", value: "WBS-RPS" }],
  });
  assert.ok(internalId);
  assert.deepEqual(ids(filterActivitiesByDefinition(internal, internalId, nodes)), []);
});

test("applyActivityFilterState handles All Activities, All/Any and highlight mode", () => {
  const state: ActivityFilterState = {
    ...EMPTY_ACTIVITY_FILTERS,
    selectedIds: ["builtin:completed", "builtin:critical"],
  };
  const all = applyActivityFilterState(rows, state);
  assert.deepEqual(ids(all.activities), ["A100"]);
  assert.deepEqual([...all.matchedIds], ["A100"]);
  assert.equal(all.highlight, false);

  const any = applyActivityFilterState(rows, setActivityFilterCombine(state, "any"));
  assert.deepEqual(ids(any.activities), ["A100", "A130"]);

  const highlighted = applyActivityFilterState(rows, setActivityFilterApplyMode(setActivityFilterCombine(state, "any"), "highlight"));
  assert.equal(highlighted.activities.length, rows.length);
  assert.deepEqual([...highlighted.matchedIds], ["A100", "A130"]);
  assert.equal(highlighted.highlight, true);

  const bypass = applyActivityFilterState(rows, setActivityFilterAllActivities(state, true));
  assert.equal(bypass.activities.length, rows.length);
  assert.deepEqual([...bypass.matchedIds], ["A100", "A130", "A140", "A150"]);
  assert.deepEqual(bypass.filters, []);
});

test("filter categories gate editing and support Make Global, Copy as Layout and Paste", () => {
  const layout = normalizeActivityFilter({
    name: "Civil open",
    match: "all",
    scope: "layout",
    criteria: [{ fieldId: "wbs", operator: "contains", value: "Civil" }],
  });
  assert.ok(layout);
  assert.equal(layout.scope, "layout");
  assert.equal(layout.id, "custom:civil-open");

  let state = upsertActivityFilter(EMPTY_ACTIVITY_FILTERS, layout);
  assert.deepEqual(state.selectedIds, ["custom:civil-open"]);

  state = makeGlobalActivityFilter(state, "custom:civil-open");
  assert.equal(state.saved[0].scope, "global");

  state = copyActivityFilterAsLayout(state, "builtin:completed");
  assert.equal(state.saved.length, 2);
  assert.equal(state.saved[0].scope, "layout");
  assert.equal(state.saved[0].name, "Completed");

  state = pasteActivityFilter(state, findActivityFilter(state, "custom:civil-open")!, "global");
  assert.equal(state.saved.length, 3);
  assert.equal(state.saved[0].scope, "global");
  assert.notEqual(state.saved[0].id, "custom:civil-open");

  // Built-ins are read-only: they cannot be deleted from the layout.
  assert.equal(deleteActivityFilter(state, "builtin:critical"), state);
});

test("selectActivityFilter keeps the checked ids and repairs a legacy activeId", () => {
  const state = selectActivityFilter(EMPTY_ACTIVITY_FILTERS, "builtin:in-progress", true);
  assert.deepEqual(state.selectedIds, ["builtin:in-progress"]);
  const both = selectActivityFilter(state, "builtin:completed", true);
  assert.deepEqual(both.selectedIds, ["builtin:in-progress", "builtin:completed"]);
  const removed = selectActivityFilter(both, "builtin:in-progress", false);
  assert.deepEqual(removed.selectedIds, ["builtin:completed"]);
  assert.equal(removed.activeId, "builtin:completed");

  const legacy = normalizeActivityFilterState({
    saved: [{ name: "Civil", match: "all", criteria: [{ fieldId: "wbs", operator: "contains", value: "Civil" }] }],
    activeId: "custom:civil",
  });
  assert.deepEqual(legacy.selectedIds, ["custom:civil"]);
  assert.equal(legacy.combine, "all");
  assert.equal(legacy.applyMode, "replace");
  assert.equal(legacy.allActivities, false);
});

test("date criteria accept ISO dates and the relative CD/CS/CF tokens", () => {
  const dated: readonly WorkspaceActivityRow[] = [
    { id: "D1", code: "D1", wbsId: "1", name: "Startup", cells: { start: "2026-10-10T08:00:00Z", finish: "2026-10-12T17:00:00Z" } },
    { id: "D2", code: "D2", wbsId: "1", name: "Mid", cells: { start: "2026-10-15T08:00:00Z", finish: "2026-10-20T17:00:00Z" } },
    { id: "D3", code: "D3", wbsId: "1", name: "Late", cells: { start: "2026-11-30T08:00:00Z", finish: "2026-12-03T17:00:00Z" } },
  ];
  const context = { currentDate: "2026-10-15", projectStart: "2026-10-10", projectFinish: "2026-12-03" };
  const lookahead: ActivityFilterDefinition = {
    id: "custom:lookahead",
    name: "Lookahead",
    match: "all",
    criteria: [{ fieldId: "start", operator: "within-range", value: "CD", highValue: "CD+7d" }],
  };
  assert.deepEqual(ids(filterActivitiesByDefinition(dated, lookahead, [], context)), ["D2"]);

  const beforeFinish: ActivityFilterDefinition = {
    id: "custom:before-finish", name: "Before finish", match: "all",
    criteria: [{ fieldId: "finish", operator: "less-than", value: "CF" }],
  };
  assert.deepEqual(ids(filterActivitiesByDefinition(dated, beforeFinish, [], context)), ["D1", "D2"]);

  const onStart: ActivityFilterDefinition = {
    id: "custom:on-start", name: "On start", match: "all",
    criteria: [{ fieldId: "start", operator: "equals", value: "CS" }],
  };
  assert.deepEqual(ids(filterActivitiesByDefinition(dated, onStart, [], context)), ["D1"]);

  // Without a date context a relative token cannot resolve, so the criterion
  // never matches instead of falling back to a guessed date.
  assert.deepEqual(ids(filterActivitiesByDefinition(dated, lookahead)), []);
  assert.equal(resolveFilterDateValue("CD+6w", context), Date.parse("2026-10-15") + 42 * 24 * 60 * 60 * 1000);
  assert.equal(resolveFilterDateValue("2026-10-20", context), Date.parse("2026-10-20"));
});

test("criterion validation reports incomplete, invalid and inverted ranges", () => {
  const context = { currentDate: "2026-10-15", projectStart: "2026-10-01", projectFinish: "2026-12-01" };
  assert.deepEqual(
    validateActivityFilterCriterion({ fieldId: "start", operator: "greater-than", value: "" }, context),
    { ok: false, code: "FILTER_VALUE_REQUIRED" },
  );
  assert.deepEqual(
    validateActivityFilterCriterion({ fieldId: "start", operator: "within-range", value: "CD" }, context),
    { ok: false, code: "FILTER_RANGE_INCOMPLETE" },
  );
  assert.deepEqual(
    validateActivityFilterCriterion({ fieldId: "start", operator: "greater-than", value: "soon" }, context),
    { ok: false, code: "FILTER_VALUE_INVALID_DATE" },
  );
  assert.deepEqual(
    validateActivityFilterCriterion({ fieldId: "start", operator: "within-range", value: "CF", highValue: "CD" }, context),
    { ok: false, code: "FILTER_RANGE_INVALID" },
  );
  assert.deepEqual(
    validateActivityFilterCriterion({ fieldId: "progress", operator: "within-range", value: "10", highValue: "50" }, context),
    { ok: true, code: "OK" },
  );
});

test("numeric ranges and not-contains narrow rows, and the preview counts them", () => {
  const numeric: ActivityFilterDefinition = {
    id: "custom:float", name: "Float band", match: "all",
    criteria: [{ fieldId: "total_float", operator: "within-range", value: "-5", highValue: "0" }],
  };
  assert.deepEqual(ids(filterActivitiesByDefinition(rows, numeric)), ["A100", "A130"]);

  const notCivil: ActivityFilterDefinition = {
    id: "custom:not-civil", name: "Not civil", match: "all",
    criteria: [{ fieldId: "wbs", operator: "not-contains", value: "civil" }],
  };
  assert.deepEqual(ids(filterActivitiesByDefinition(rows, notCivil)), ["A100", "A150"]);

  const preview = previewActivityFilter(rows, numeric);
  assert.deepEqual(preview, { total: 4, matched: 2, valid: true, code: "OK" });

  const invalid = previewActivityFilter(rows, {
    id: "custom:bad", name: "Bad", match: "all",
    criteria: [{ fieldId: "start", operator: "within-range", value: "CD" }],
  }, [], { currentDate: "2026-10-15", projectStart: null, projectFinish: null });
  assert.equal(invalid.valid, false);
  assert.equal(invalid.code, "FILTER_RANGE_INCOMPLETE");
});

test("normalization keeps the high value only for ranges and describes it", () => {
  const range = normalizeActivityFilter({
    name: "Lookahead", match: "all",
    criteria: [{ fieldId: "start", operator: "within-range", value: "CD", highValue: "CD+6w" }],
  });
  assert.ok(range);
  assert.equal(range.criteria[0].highValue, "CD+6w");
  assert.equal(describeActivityFilter(range, "en"), "Start is within range of CD and CD+6w");
  assert.equal(describeActivityFilter(range, "fa"), "شروع در بازهٔ CD تا CD+6w");

  const equal = normalizeActivityFilter({
    name: "Named", match: "all",
    criteria: [{ fieldId: "activity_name", operator: "equals", value: "Kickoff", highValue: "ignored" }],
  });
  assert.ok(equal);
  assert.equal(equal.criteria[0].highValue, undefined);
});

test("list parameters expose their stored values for a picker", () => {
  assert.deepEqual(activityFilterChoiceValues("activity_status"), ["Not Started", "In Progress", "Completed"]);
  assert.equal(activityFilterChoiceValues("activity_type")?.length, 6);
  assert.deepEqual(activityFilterChoiceValues("is_critical"), ["true", "false"]);
  assert.equal(activityFilterChoiceValues("activity_name"), null);
});

test("Optimize collapses duplicates and implied rows without changing matches", () => {
  const duplicates = optimizeActivityFilterCriteria([
    { fieldId: "wbs", operator: "contains", value: "Civil" },
    { fieldId: "wbs", operator: "contains", value: "civil" },
    { fieldId: "activity_name", operator: "contains", value: "" },
  ], "all");
  assert.equal(duplicates.removed, 2);
  assert.deepEqual(duplicates.criteria, [{ fieldId: "wbs", operator: "contains", value: "Civil" }]);

  // All (AND): the longer contains is stricter, so the shorter is implied.
  const all = optimizeActivityFilterCriteria([
    { fieldId: "activity_name", operator: "contains", value: "Piling" },
    { fieldId: "activity_name", operator: "contains", value: "Piling and foundations" },
  ], "all");
  assert.equal(all.removed, 1);
  assert.deepEqual(all.criteria, [{ fieldId: "activity_name", operator: "contains", value: "Piling and foundations" }]);

  // Any (OR): the shorter contains covers more, so the longer is absorbed.
  const any = optimizeActivityFilterCriteria([
    { fieldId: "activity_name", operator: "contains", value: "Piling" },
    { fieldId: "activity_name", operator: "contains", value: "Piling and foundations" },
  ], "any");
  assert.equal(any.removed, 1);
  assert.deepEqual(any.criteria, [{ fieldId: "activity_name", operator: "contains", value: "Piling" }]);

  // equals implies contains; not-contains implies not-equals.
  const mixed = optimizeActivityFilterCriteria([
    { fieldId: "activity_status", operator: "equals", value: "In Progress" },
    { fieldId: "activity_status", operator: "contains", value: "Progress" },
    { fieldId: "wbs", operator: "not-contains", value: "Civil" },
    { fieldId: "wbs", operator: "not-equals", value: "Civil" },
  ], "all");
  assert.equal(mixed.removed, 2);
  assert.deepEqual(mixed.criteria, [
    { fieldId: "activity_status", operator: "equals", value: "In Progress" },
    { fieldId: "wbs", operator: "not-contains", value: "Civil" },
  ]);

  const original: ActivityFilterDefinition = {
    id: "custom:check", name: "Check", match: "all",
    criteria: [
      { fieldId: "activity_name", operator: "contains", value: "Piling" },
      { fieldId: "activity_name", operator: "contains", value: "Piling and foundations" },
    ],
  };
  const optimized: ActivityFilterDefinition = { ...original, criteria: all.criteria };
  assert.deepEqual(ids(filterActivitiesByDefinition(rows, optimized)), ids(filterActivitiesByDefinition(rows, original)));
});

test("Optimize leaves a clean filter and an all-blank editor alone", () => {
  const clean = [
    { fieldId: "activity_status" as const, operator: "equals" as const, value: "Completed" },
    { fieldId: "progress" as const, operator: "less-than" as const, value: "50" },
  ];
  const result = optimizeActivityFilterCriteria(clean, "all");
  assert.equal(result.removed, 0);
  assert.deepEqual(result.criteria, clean);

  const blank = [{ fieldId: "activity_name" as const, operator: "contains" as const, value: "" }];
  const untouched = optimizeActivityFilterCriteria(blank, "all");
  assert.equal(untouched.removed, 0);
  assert.deepEqual(untouched.criteria, blank);
});

test("Duplicate saves a second copy in the same category", () => {
  const source = normalizeActivityFilter({
    name: "Civil open",
    match: "all",
    criteria: [{ fieldId: "wbs", operator: "contains", value: "Civil" }],
  });
  assert.ok(source);
  const state = upsertActivityFilter(EMPTY_ACTIVITY_FILTERS, { ...source, scope: "global" });
  const duplicated = duplicateActivityFilter(state, source.id);
  assert.equal(duplicated.saved.length, 2);
  assert.equal(duplicated.saved[0].name, "Civil open (copy)");
  assert.equal(duplicated.saved[0].scope, "global");
  assert.notEqual(duplicated.saved[0].id, source.id);
  assert.deepEqual(duplicated.saved[0].criteria, source.criteria);
  // A predefined filter is read-only; Copy as Layout is its documented path.
  assert.equal(duplicateActivityFilter(state, "builtin:completed"), state);
});
