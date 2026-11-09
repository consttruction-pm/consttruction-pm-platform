import assert from "node:assert/strict";
import test from "node:test";

import {
  activityMatchesFilter,
  applyActivityFilterState,
  copyActivityFilterAsLayout,
  deleteActivityFilter,
  describeActivityFilter,
  EMPTY_ACTIVITY_FILTERS,
  filterActivitiesByDefinition,
  findActivityFilter,
  getBuiltinActivityFilters,
  makeGlobalActivityFilter,
  normalizeActivityFilter,
  normalizeActivityFilterState,
  pasteActivityFilter,
  selectActivityFilter,
  setActiveActivityFilter,
  setActivityFilterAllActivities,
  setActivityFilterApplyMode,
  setActivityFilterCombine,
  upsertActivityFilter,
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
