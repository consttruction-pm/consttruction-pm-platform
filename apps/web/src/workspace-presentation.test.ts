import assert from "node:assert/strict";
import test from "node:test";

import {
  DEFAULT_PRESENTATION,
  DEFAULT_WBS_LEVEL_COLORS,
  activityBarFacts,
  barKindMatchesFilter,
  barLabelText,
  hasActualDates,
  hasBaselineDates,
  normalizeBarStyle,
  normalizePresentation,
  normalizeTimescale,
  presentationDataAvailability,
  presentationFontFamily,
  selectPrimaryBarKind,
  wbsBandInk,
  wbsLevelColor,
  type GanttBarFacts,
} from "./workspace-presentation.js";
import type { WorkspaceActivityRow } from "./workspace-model.js";

function facts(patch: Partial<GanttBarFacts> = {}): GanttBarFacts {
  return {
    critical: false,
    milestone: false,
    summary: false,
    status: "Not Started",
    progress: 0,
    hasActual: false,
    hasBaseline: false,
    ...patch,
  };
}

function activity(patch: Partial<WorkspaceActivityRow> = {}): WorkspaceActivityRow {
  return { id: "A1000", wbsId: "", code: "A1000", name: "Activity", ...patch };
}

test("normalisation keeps valid presentation values and clamps invalid ones", () => {
  const normalized = normalizePresentation({
    table: { fontFamily: "cairo", fontSize: 99, textColor: "#ABC", backgroundColor: "red", rowHeight: 2, rowHeightMode: "content", showIcons: true, lineNumbers: true },
    bars: { task: { bodyColor: "#123456", height: 99, row: 9, pattern: "hatched" } },
  });
  assert.equal(normalized.table.fontFamily, "cairo");
  assert.equal(normalized.table.fontSize, 16);
  assert.equal(normalized.table.textColor, "#aabbcc");
  assert.equal(normalized.table.backgroundColor, "#ffffff");
  assert.equal(normalized.table.rowHeight, 18);
  assert.equal(normalized.table.rowHeightMode, "content");
  assert.equal(normalized.bars.task.bodyColor, "#123456");
  assert.equal(normalized.bars.task.height, 24);
  assert.equal(normalized.bars.task.row, 3);
  assert.equal(normalized.bars.task.pattern, "hatched");
});

test("a fully invalid presentation falls back to the documented defaults", () => {
  assert.deepEqual(normalizePresentation(null), DEFAULT_PRESENTATION);
  assert.deepEqual(normalizePresentation({ table: 4, bars: "x" }), DEFAULT_PRESENTATION);
});

test("timescale and WBS level colours normalise and persist with the layout", () => {
  const normalized = normalizePresentation({
    timescale: {
      lines: 3,
      dateFormat: "ordinal",
      type: "week-of-year",
      interval: "week-day",
      ordinalStart: "2026-01-05",
      ordinalInterval: "day",
      fontSize: 99,
      textColor: "#ABC",
      backgroundColor: "not-a-colour",
    },
    wbs: { levelColors: ["#111111", "bad", "#333333"] },
  });
  assert.equal(normalized.timescale.lines, 3);
  // The dialog must be able to switch back from three header rows to two.
  assert.equal(normalizeTimescale({ lines: 2 }, normalized.timescale).lines, 2);
  assert.equal(normalized.timescale.dateFormat, "ordinal");
  assert.equal(normalized.timescale.type, "week-of-year");
  assert.equal(normalized.timescale.interval, "week-day");
  assert.equal(normalized.timescale.ordinalStart, "2026-01-05");
  assert.equal(normalized.timescale.ordinalInterval, "day");
  assert.equal(normalized.timescale.fontSize, 16);
  assert.equal(normalized.timescale.textColor, "#aabbcc");
  assert.equal(normalized.timescale.backgroundColor, DEFAULT_PRESENTATION.timescale.backgroundColor);
  assert.equal(normalized.wbs.levelColors.length, 6);
  assert.equal(normalized.wbs.levelColors[0], "#111111");
  assert.equal(normalized.wbs.levelColors[1], DEFAULT_WBS_LEVEL_COLORS[1]);
  assert.equal(normalized.wbs.levelColors[2], "#333333");
  assert.equal(wbsLevelColor(normalized.wbs, 99), DEFAULT_WBS_LEVEL_COLORS[5]);
  assert.equal(normalizePresentation({ timescale: { ordinalStart: "05/01/2026" } }).timescale.ordinalStart, null);
});

test("WBS band format keeps its own typeface, ink and label flags across reloads", () => {
  const normalized = normalizePresentation({
    wbs: {
      fontFamily: "cairo",
      fontSize: 44,
      inkMode: "custom",
      textColor: "#ABC",
      rowHeight: 99,
      labels: { title: true, code: false, name: "yes" },
    },
  });
  assert.equal(normalized.wbs.fontFamily, "cairo");
  assert.equal(normalized.wbs.fontSize, 16);
  assert.equal(normalized.wbs.inkMode, "custom");
  assert.equal(normalized.wbs.textColor, "#aabbcc");
  assert.equal(normalized.wbs.rowHeight, 40);
  assert.equal(normalized.wbs.labels.title, true);
  assert.equal(normalized.wbs.labels.code, false);
  // A non-boolean label flag falls back instead of being treated as false.
  assert.equal(normalized.wbs.labels.name, DEFAULT_PRESENTATION.wbs.labels.name);
  assert.equal(normalizePresentation({ wbs: { fontFamily: "comic", inkMode: "flashy" } }).wbs.fontFamily, DEFAULT_PRESENTATION.wbs.fontFamily);
  assert.equal(normalizePresentation({ wbs: { fontFamily: "comic", inkMode: "flashy" } }).wbs.inkMode, "auto");
});

test("WBS band ink uses the level contrast colour unless a custom ink is chosen", () => {
  const auto = normalizePresentation(undefined);
  // Level 1 is blue with yellow reference ink; a custom colour wins unchanged.
  assert.equal(wbsBandInk(auto.wbs, 0), "#ffff00");
  const custom = normalizePresentation({ wbs: { inkMode: "custom", textColor: "#102030" } });
  assert.equal(wbsBandInk(custom.wbs, 0), "#102030");
  assert.equal(wbsBandInk(custom.wbs, 2), "#102030");
});

test("each bar style is independent and does not share mutable defaults", () => {
  const normalized = normalizePresentation({ bars: { task: { bodyColor: "#010203" } } });
  assert.equal(normalized.bars.task.bodyColor, "#010203");
  assert.equal(normalized.bars.critical.bodyColor, DEFAULT_PRESENTATION.bars.critical.bodyColor);
  normalized.bars.task.height = 4;
  assert.notEqual(DEFAULT_PRESENTATION.bars.task.height, 4);
});

test("bar normalisation clamps every editable numeric field", () => {
  const style = normalizeBarStyle({ height: 0, row: 0, visible: "yes", bodyShape: "star" }, DEFAULT_PRESENTATION.bars.task);
  assert.equal(style.height, 3);
  assert.equal(style.row, 1);
  assert.equal(style.visible, DEFAULT_PRESENTATION.bars.task.visible);
  assert.equal(style.bodyShape, DEFAULT_PRESENTATION.bars.task.bodyShape);
});

test("filters read persisted activity facts only", () => {
  assert.equal(barKindMatchesFilter("all", facts()), true);
  assert.equal(barKindMatchesFilter("task", facts()), true);
  assert.equal(barKindMatchesFilter("task", facts({ summary: true })), false);
  assert.equal(barKindMatchesFilter("critical", facts({ critical: true })), true);
  assert.equal(barKindMatchesFilter("noncritical", facts({ critical: true })), false);
  assert.equal(barKindMatchesFilter("milestone", facts({ milestone: true })), true);
  assert.equal(barKindMatchesFilter("summary", facts({ summary: true })), true);
  assert.equal(barKindMatchesFilter("in-progress", facts({ progress: 40 })), true);
  assert.equal(barKindMatchesFilter("in-progress", facts({ progress: 100 })), false);
  assert.equal(barKindMatchesFilter("completed", facts({ progress: 100 })), true);
  assert.equal(barKindMatchesFilter("not-started", facts({ progress: 0 })), true);
  assert.equal(barKindMatchesFilter("not-started", facts({ progress: 0, status: "In Progress" })), false);
});

test("one primary bar is selected per activity by documented precedence", () => {
  const bars = DEFAULT_PRESENTATION.bars;
  assert.equal(selectPrimaryBarKind(bars, facts({ milestone: true })), "milestone");
  assert.equal(selectPrimaryBarKind(bars, facts({ summary: true, critical: true })), "summary");
  assert.equal(selectPrimaryBarKind(bars, facts({ critical: true })), "critical");
  assert.equal(selectPrimaryBarKind(bars, facts()), "task");
  const hiddenCritical = { ...bars, critical: { ...bars.critical, visible: false } };
  assert.equal(selectPrimaryBarKind(hiddenCritical, facts({ critical: true })), "task");
  const allHidden = { ...bars, task: { ...bars.task, visible: false }, critical: { ...bars.critical, visible: false } };
  assert.equal(selectPrimaryBarKind(allHidden, facts()), null);
});

test("missing dates disable actual and baseline bars instead of fabricating them", () => {
  const planned = activity();
  assert.equal(hasActualDates(planned), false);
  assert.equal(hasBaselineDates(planned), false);
  assert.deepEqual(presentationDataAvailability([planned]), { actual: false, baseline: false });

  const progressed = activity({ cells: { "activity.actual_start": "2026-01-02", "activity.actual_finish": "2026-01-05" } });
  assert.equal(hasActualDates(progressed), true);
  assert.equal(hasBaselineDates(progressed), false);

  const baselined = activity({ cells: { baseline_start: "2026-01-01", baseline_finish: "2026-01-04" } });
  assert.equal(hasBaselineDates(baselined), true);
  assert.deepEqual(presentationDataAvailability([planned, progressed, baselined]), { actual: true, baseline: true });
});

test("activity bar facts distinguish summary, milestone and progress", () => {
  const bars = { critical: true, milestone: true, progressPercent: 35 };
  const summaryRow = activity({ cells: { "activity.activity_type": "WBS Summary", "activity.activity_status": "In Progress" } });
  assert.deepEqual(activityBarFacts(summaryRow, bars), {
    critical: true,
    milestone: true,
    summary: true,
    status: "In Progress",
    progress: 35,
    hasActual: false,
    hasBaseline: false,
  });
});

test("labels read only the persisted display facts", () => {
  const row = activity({ name: "Excavate", cells: { duration: 5 } });
  assert.equal(barLabelText("activity-id", { activityId: "A1000", progressPercent: 20 }, row), "A1000");
  assert.equal(barLabelText("activity-name", { activityId: "A1000", progressPercent: 20 }, row), "Excavate");
  assert.equal(barLabelText("duration", { activityId: "A1000", progressPercent: 20 }, row), "5");
  assert.equal(barLabelText("progress", { activityId: "A1000", progressPercent: 20 }, row), "20%");
  assert.equal(barLabelText("none", { activityId: "A1000", progressPercent: 20 }, row), "");
  // The reference prints "Finish, Activity ID  Activity Name" beside the bar.
  const dated = activity({ name: "Excavate", gantt: { start: "2026-09-01T00:00:00Z", finish: "2026-09-05T00:00:00Z", progressPercent: 0, critical: false } });
  assert.equal(barLabelText("finish-id-name", { activityId: "A1000", progressPercent: 0 }, dated), "05-Sep-26, A1000  Excavate");
  // Without a persisted finish the label still carries the real identity only.
  assert.equal(barLabelText("finish-id-name", { activityId: "A1000", progressPercent: 0 }, row), "A1000  Excavate");
});

test("font families resolve to concrete stacks without third-party product names", () => {
  for (const family of ["system", "segoe", "cairo", "tahoma", "consolas"] as const) {
    const stack = presentationFontFamily(family);
    assert.ok(stack.length > 0);
    assert.doesNotMatch(stack, /oracle|primavera/i);
  }
});
