import type { ProjectContext } from "./client.js";

export type WorkspaceLocale = "fa" | "en";
export type WorkspaceCalendarMode = "jalali" | "gregorian";
export type WorkspacePanel = "project_wbs" | "activity_grid" | "gantt" | "details";

export type WorkspaceMenuKey =
  | "project"
  | "schedule"
  | "progress"
  | "resources"
  | "cost"
  | "documents"
  | "reports"
  | "control"
  | "settings";

export type WorkspaceColumnDataType =
  | "text"
  | "integer"
  | "decimal"
  | "date"
  | "duration"
  | "boolean";

export type WorkspaceColumn = {
  id: string;
  label: string;
  dataType: WorkspaceColumnDataType;
  editable: boolean;
  formula: string | null;
  width: number;
};

export type WorkspaceActivityRow = {
  id: string;
  wbsId: string;
  code: string;
  name: string;
};

export type WorkspaceState = {
  context: ProjectContext;
  locale: WorkspaceLocale;
  direction: "rtl" | "ltr";
  calendarMode: WorkspaceCalendarMode;
  activeMenu: WorkspaceMenuKey;
  visiblePanels: Record<WorkspacePanel, boolean>;
  selectedWbsId: string | null;
  selectedActivityId: string | null;
  columns: readonly WorkspaceColumn[];
  activities: readonly WorkspaceActivityRow[];
};

export const DEFAULT_WORKSPACE_COLUMNS: readonly WorkspaceColumn[] = [
  { id: "activity_id", label: "Activity ID", dataType: "text", editable: false, formula: null, width: 120 },
  { id: "activity_name", label: "Activity Name", dataType: "text", editable: true, formula: null, width: 260 },
  { id: "start", label: "Start", dataType: "date", editable: false, formula: null, width: 120 },
  { id: "finish", label: "Finish", dataType: "date", editable: false, formula: null, width: 120 },
  { id: "duration", label: "Duration", dataType: "duration", editable: false, formula: null, width: 110 },
];

export function createWorkspaceState(
  context: ProjectContext,
  locale: WorkspaceLocale = "en",
  calendarMode: WorkspaceCalendarMode = "gregorian",
): WorkspaceState {
  validateContext(context);
  return {
    context: Object.freeze({ ...context }),
    locale,
    direction: locale === "fa" ? "rtl" : "ltr",
    calendarMode,
    activeMenu: "schedule",
    visiblePanels: {
      project_wbs: true,
      activity_grid: true,
      gantt: true,
      details: true,
    },
    selectedWbsId: null,
    selectedActivityId: null,
    columns: DEFAULT_WORKSPACE_COLUMNS,
    activities: [],
  };
}

export function selectWbs(state: WorkspaceState, wbsId: string | null): WorkspaceState {
  return {
    ...state,
    selectedWbsId: wbsId,
    selectedActivityId: null,
  };
}

export function selectActivity(state: WorkspaceState, activityId: string | null): WorkspaceState {
  const exists = activityId === null || state.activities.some((activity) => activity.id === activityId);
  if (!exists) {
    throw new Error("ACTIVITY_NOT_FOUND");
  }
  return {
    ...state,
    selectedActivityId: activityId,
  };
}

export function setLocale(state: WorkspaceState, locale: WorkspaceLocale): WorkspaceState {
  return {
    ...state,
    locale,
    direction: locale === "fa" ? "rtl" : "ltr",
  };
}

export function setCalendarMode(
  state: WorkspaceState,
  calendarMode: WorkspaceCalendarMode,
): WorkspaceState {
  return { ...state, calendarMode };
}

export function addFormulaColumn(state: WorkspaceState, column: WorkspaceColumn): WorkspaceState {
  if (column.formula === null || !column.formula.trim()) {
    throw new Error("FORMULA_REQUIRED");
  }
  if (column.dataType === "text" && column.formula.includes("=")) {
    // Formula expressions remain presentation metadata here; the authoritative
    // calculation engine owns evaluation. The client never computes formula values.
  }
  if (state.columns.some((existing) => existing.id === column.id)) {
    throw new Error("COLUMN_ALREADY_EXISTS");
  }
  return {
    ...state,
    columns: [...state.columns, Object.freeze({ ...column })],
  };
}

export function withActivities(
  state: WorkspaceState,
  activities: readonly WorkspaceActivityRow[],
): WorkspaceState {
  const ids = new Set<string>();
  for (const activity of activities) {
    if (ids.has(activity.id) || !activity.id || !activity.wbsId) {
      throw new Error("INVALID_ACTIVITY_ROWS");
    }
    ids.add(activity.id);
  }
  const selectedActivityId =
    state.selectedActivityId && ids.has(state.selectedActivityId)
      ? state.selectedActivityId
      : null;
  return {
    ...state,
    activities: activities.map((activity) => Object.freeze({ ...activity })),
    selectedActivityId,
  };
}

function validateContext(context: ProjectContext): void {
  if (
    !context.tenant_id ||
    !context.project_id ||
    !Number.isInteger(context.revision) ||
    context.revision < 0
  ) {
    throw new Error("INVALID_PROJECT_CONTEXT");
  }
}
