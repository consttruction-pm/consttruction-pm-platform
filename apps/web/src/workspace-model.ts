import type { ProjectContext } from "./client.js";
import type { WorkspaceControlSummary } from "./workspace-control-intelligence.js";
import type { WorkspaceSiteDailyLog } from "./workspace-site-log.js";
import type { WorkspaceEquipmentStatus, WorkspaceTimecard } from "./workspace-field-ops.js";
import type { WorkspaceFieldIssue } from "./workspace-field-issues.js";
import type { WorkspaceChangeNotice, WorkspaceChangeCase, WorkspaceClaimRecord, WorkspaceChangeClaimImpact } from "./workspace-change-claim.js";
import type { WorkspaceDocument } from "./workspace-document.js";
import type { WorkspaceProcurementRecord } from "./workspace-procurement.js";
import type { WorkspaceInspection, WorkspaceQualityRecord, WorkspaceSafetyObservation, WorkspacePunchItem } from "./workspace-field-assurance.js";
import type { WorkspaceSmartGuide } from "./workspace-smart-guide.js";
import type { FieldRegistry, LayoutDefinition } from "./p6-field-layout-foundation.js";
import { addField, removeField, reorderFields, updateFieldPresentation } from "./p6-field-layout-foundation.js";
import { getWorkspaceLocaleDirection, translateWorkspaceText } from "./workspace-localization.js";

export type WorkspaceLocale = string;
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
  | "double"
  | "percentage"
  | "cost"
  | "unit"
  | "date"
  | "datetime"
  | "duration"
  | "boolean"
  | "enum"
  | "object-id"
  | "object-id-array"
  | "string-array"
  | "complex"
  | "spread";

export type WorkspaceCellValue = string | number | boolean | null;

export type WorkspaceColumn = {
  id: string;
  label: string;
  dataType: WorkspaceColumnDataType;
  editable: boolean;
  formula: string | null;
  width: number;
  alignment: "start" | "center" | "end";
  pinned: boolean;
  frozen: boolean;
};

export type WorkspaceGanttData = {
  /** ISO-8601 values already resolved by the authoritative schedule engine. */
  start: string;
  finish: string;
  progressPercent: number;
  critical: boolean;
};

export type WorkspaceActivityRow = {
  id: string;
  wbsId: string;
  code: string;
  name: string;
  /** Display-ready typed values; the Web client never evaluates formulas. */
  cells?: Readonly<Record<string, WorkspaceCellValue>>;
  /** Display-only schedule result projected from Shared Core. */
  gantt?: WorkspaceGanttData;
};

export type WorkspaceWbsNode = {
  id: string;
  parentKind: "project" | "wbs";
  parentWbsId: string | null;
  /** The node-local code; it is not the concatenated P6 WBS display path. */
  localCode: string;
  name: string;
  sequenceNumber: number;
  recordRevision: number;
};

export type WorkspaceRelationshipType = "FS" | "SS" | "FF" | "SF";

export type WorkspaceRelationshipRow = {
  id: string;
  predecessorId: string;
  successorId: string;
  type: WorkspaceRelationshipType;
  /** Canonical decimal text persisted for the lag; the client never recalculates it. */
  lagValue: string;
  lagUnit: string;
  recordRevision: number;
};

/** Read-only result facts returned by the authoritative shared scheduling service. */
export type AuthoritativeScheduledActivity = {
  start: string;
  finish: string;
  duration?: number;
  critical?: boolean;
  early_start?: string;
  early_finish?: string;
  late_start?: string;
  late_finish?: string;
  total_float?: number;
  free_float?: number;
};

export type AuthoritativeScheduleFacts = {
  calculation_run_identity?: string;
  project_finish?: string;
  activity_count?: number;
  activities: Readonly<Record<string, AuthoritativeScheduledActivity>>;
};

export type WorkspaceActivitySort = {
  readonly columnId: string;
  readonly direction: "asc" | "desc";
};

/** Presentation-only zoom of the Gantt time axis; schedule dates never change. */
export type WorkspaceGanttScale = "day" | "week" | "month";

export type WorkspaceState = {
  context: ProjectContext;
  locale: WorkspaceLocale;
  direction: "rtl" | "ltr";
  calendarMode: WorkspaceCalendarMode;
  ganttScale: WorkspaceGanttScale;
  activeMenu: WorkspaceMenuKey;
  visiblePanels: Record<WorkspacePanel, boolean>;
  selectedWbsId: string | null;
  selectedActivityId: string | null;
  columns: readonly WorkspaceColumn[];
  activities: readonly WorkspaceActivityRow[];
  wbsNodes: readonly WorkspaceWbsNode[];
  relationships: readonly WorkspaceRelationshipRow[];
  activityFilter: string;
  activitySort: WorkspaceActivitySort | null;
  controlSummary: WorkspaceControlSummary | null;
  smartGuide: WorkspaceSmartGuide | null;
  siteDailyLogs: readonly WorkspaceSiteDailyLog[];
  timecards: readonly WorkspaceTimecard[];
  equipmentReports: readonly WorkspaceEquipmentStatus[];
  fieldIssues: readonly WorkspaceFieldIssue[];
  changeNotices: readonly WorkspaceChangeNotice[];
  changeCases: readonly WorkspaceChangeCase[];
  claims: readonly WorkspaceClaimRecord[];
  changeClaimImpacts: readonly WorkspaceChangeClaimImpact[];
  documents: readonly WorkspaceDocument[];
  procurementRecords: readonly WorkspaceProcurementRecord[];
  inspections: readonly WorkspaceInspection[];
  qualityRecords: readonly WorkspaceQualityRecord[];
  safetyObservations: readonly WorkspaceSafetyObservation[];
  punchItems: readonly WorkspacePunchItem[];
  /** Authoritative P6 field metadata consumed by the Web presentation layer. */
  p6FieldRegistry: FieldRegistry | null;
  /** Authoritative/persisted layout projection for the current workspace view. */
  p6Layout: LayoutDefinition | null;
};

export const DEFAULT_WORKSPACE_COLUMNS: readonly WorkspaceColumn[] = [
  { id: "activity_id", label: "Activity ID", dataType: "text", editable: false, formula: null, width: 120, alignment: "start", pinned: false, frozen: false },
  { id: "activity_code", label: "Code", dataType: "text", editable: false, formula: null, width: 100, alignment: "start", pinned: false, frozen: false },
  { id: "activity_name", label: "Activity Name", dataType: "text", editable: false, formula: null, width: 260, alignment: "start", pinned: false, frozen: false },
  { id: "start", label: "Start", dataType: "date", editable: false, formula: null, width: 120, alignment: "end", pinned: false, frozen: false },
  { id: "finish", label: "Finish", dataType: "date", editable: false, formula: null, width: 120, alignment: "end", pinned: false, frozen: false },
  { id: "duration", label: "Duration", dataType: "duration", editable: false, formula: null, width: 110, alignment: "end", pinned: false, frozen: false },
  { id: "progress", label: "Progress", dataType: "decimal", editable: false, formula: null, width: 100, alignment: "end", pinned: false, frozen: false },
];

const DEFAULT_WORKSPACE_COLUMN_LABELS: Record<WorkspaceLocale, Record<string, string>> = {
  en: { activity_id: "Activity ID", activity_code: "Code", activity_name: "Activity Name", start: "Start", finish: "Finish", duration: "Duration", progress: "Progress" },
  fa: { activity_id: "شناسه فعالیت", activity_code: "کد", activity_name: "نام فعالیت", start: "شروع", finish: "پایان", duration: "مدت", progress: "پیشرفت" },
};

export function getDefaultWorkspaceColumns(locale: WorkspaceLocale = "en"): readonly WorkspaceColumn[] {
  return DEFAULT_WORKSPACE_COLUMNS.map((column) => Object.freeze({ ...column, label: translateWorkspaceText(locale, `column.${column.id}`, DEFAULT_WORKSPACE_COLUMN_LABELS[locale.split("-")[0] as "en" | "fa"]?.[column.id] ?? column.label) }));
}

export function createWorkspaceState(
  context: ProjectContext,
  locale: WorkspaceLocale = "en",
  calendarMode: WorkspaceCalendarMode = "gregorian",
): WorkspaceState {
  validateContext(context);
  return {
    context: Object.freeze({ ...context }),
    locale,
    direction: getWorkspaceLocaleDirection(locale),
    calendarMode,
    ganttScale: "day",
    activeMenu: "schedule",
    visiblePanels: {
      project_wbs: true,
      activity_grid: true,
      gantt: true,
      details: true,
    },
    selectedWbsId: null,
    selectedActivityId: null,
    columns: getDefaultWorkspaceColumns(locale),
    activities: [],
    wbsNodes: [],
    relationships: [],
    activityFilter: "",
    activitySort: null,
    controlSummary: null,
    smartGuide: null,
    siteDailyLogs: [],
    timecards: [],
    equipmentReports: [],
    fieldIssues: [],
    changeNotices: [],
    changeCases: [],
    claims: [],
    changeClaimImpacts: [],
    documents: [],
    procurementRecords: [],
    inspections: [],
    qualityRecords: [],
    safetyObservations: [],
    punchItems: [],
    p6FieldRegistry: null,
    p6Layout: null,
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

export function setActivityFilter(state: WorkspaceState, filterText: string): WorkspaceState {
  const normalized = filterText.slice(0, 200);
  if (normalized === state.activityFilter) return state;
  return { ...state, activityFilter: normalized };
}

export function setActivitySort(
  state: WorkspaceState,
  columnId: string | null,
  direction: "asc" | "desc" = "asc",
): WorkspaceState {
  if (columnId === null) {
    return state.activitySort === null ? state : { ...state, activitySort: null };
  }
  if (!state.columns.some((column) => column.id === columnId)) {
    throw new Error("SORT_COLUMN_NOT_FOUND");
  }
  const next = Object.freeze({ columnId, direction });
  if (
    state.activitySort?.columnId === next.columnId &&
    state.activitySort.direction === next.direction
  ) {
    return state;
  }
  return { ...state, activitySort: next };
}

export function toggleActivitySortDirection(state: WorkspaceState): WorkspaceState {
  if (!state.activitySort) return state;
  return {
    ...state,
    activitySort: Object.freeze({
      columnId: state.activitySort.columnId,
      direction: state.activitySort.direction === "asc" ? "desc" : "asc",
    }),
  };
}

export function setLocale(state: WorkspaceState, locale: WorkspaceLocale): WorkspaceState {
  return {
    ...state,
    locale,
    direction: getWorkspaceLocaleDirection(locale),
    columns: state.p6Layout ? state.columns : getDefaultWorkspaceColumns(locale),
  };
}

export function setCalendarMode(
  state: WorkspaceState,
  calendarMode: WorkspaceCalendarMode,
): WorkspaceState {
  return { ...state, calendarMode };
}

export function setGanttScale(
  state: WorkspaceState,
  ganttScale: WorkspaceGanttScale,
): WorkspaceState {
  if (ganttScale !== "day" && ganttScale !== "week" && ganttScale !== "month") {
    throw new Error("INVALID_GANTT_SCALE");
  }
  if (state.ganttScale === ganttScale) return state;
  return { ...state, ganttScale };
}

export function setSmartGuide(
  state: WorkspaceState,
  smartGuide: WorkspaceSmartGuide | null,
): WorkspaceState {
  return { ...state, smartGuide };
}

export function setControlSummary(
  state: WorkspaceState,
  controlSummary: WorkspaceControlSummary | null,
): WorkspaceState {
  return { ...state, controlSummary };
}

export function setSiteDailyLogs(
  state: WorkspaceState,
  siteDailyLogs: readonly WorkspaceSiteDailyLog[],
): WorkspaceState {
  return {
    ...state,
    siteDailyLogs: siteDailyLogs.map((log) => Object.freeze({ ...log, entries: [...log.entries] })),
  };
}

export function setFieldOperations(
  state: WorkspaceState,
  timecards: readonly WorkspaceTimecard[],
  equipmentReports: readonly WorkspaceEquipmentStatus[],
): WorkspaceState {
  return {
    ...state,
    timecards: timecards.map((card) => Object.freeze({ ...card })),
    equipmentReports: equipmentReports.map((report) => Object.freeze({ ...report })),
  };
}

export function setFieldIssues(
  state: WorkspaceState,
  fieldIssues: readonly WorkspaceFieldIssue[],
): WorkspaceState {
  return {
    ...state,
    fieldIssues: fieldIssues.map((issue) =>
      Object.freeze({ ...issue, activityIds: [...issue.activityIds] }),
    ),
  };
}

export function setFieldAssurance(
  state: WorkspaceState,
  assurance: {
    inspections: readonly WorkspaceInspection[];
    qualityRecords: readonly WorkspaceQualityRecord[];
    safetyObservations: readonly WorkspaceSafetyObservation[];
    punchItems: readonly WorkspacePunchItem[];
  },
): WorkspaceState {
  return {
    ...state,
    inspections: assurance.inspections.map((item) =>
      Object.freeze({ ...item, checklist: item.checklist.map((entry) => Object.freeze({ ...entry })) }),
    ),
    qualityRecords: assurance.qualityRecords.map((item) =>
      Object.freeze({ ...item, activityIds: [...item.activityIds] }),
    ),
    safetyObservations: assurance.safetyObservations.map((item) =>
      Object.freeze({ ...item, activityIds: [...item.activityIds] }),
    ),
    punchItems: assurance.punchItems.map((item) =>
      Object.freeze({ ...item, activityIds: [...item.activityIds] }),
    ),
  };
}

export function setChangeClaimRecords(
  state: WorkspaceState,
  records: {
    changeNotices: readonly WorkspaceChangeNotice[];
    changeCases: readonly WorkspaceChangeCase[];
    claims: readonly WorkspaceClaimRecord[];
    changeClaimImpacts: readonly WorkspaceChangeClaimImpact[];
  },
): WorkspaceState {
  return {
    ...state,
    changeNotices: records.changeNotices.map((item) => Object.freeze({ ...item, scheduleRefs: [...item.scheduleRefs], costRefs: [...item.costRefs], dependencyRefs: [...item.dependencyRefs] })),
    changeCases: records.changeCases.map((item) => Object.freeze({ ...item, scheduleRefs: [...item.scheduleRefs], costRefs: [...item.costRefs], dependencyRefs: [...item.dependencyRefs], impactLinkIds: [...item.impactLinkIds], implementationActivityIds: [...item.implementationActivityIds] })),
    claims: records.claims.map((item) => Object.freeze({ ...item, scheduleRefs: [...item.scheduleRefs], costRefs: [...item.costRefs], impactLinkIds: [...item.impactLinkIds] })),
    changeClaimImpacts: records.changeClaimImpacts.map((item) => Object.freeze({ ...item })),
  };
}

export function setDocuments(
  state: WorkspaceState,
  documents: readonly WorkspaceDocument[],
): WorkspaceState {
  return {
    ...state,
    documents: documents.map((document) =>
      Object.freeze({
        ...document,
        linkedEntityRefs: Object.freeze([...document.linkedEntityRefs]),
      }),
    ),
  };
}

export function setProcurementRecords(
  state: WorkspaceState,
  records: readonly WorkspaceProcurementRecord[],
): WorkspaceState {
  return {
    ...state,
    procurementRecords: records.map((record) =>
      Object.freeze({
        ...record,
        activityIds: Object.freeze([...record.activityIds]),
      }),
    ),
  };
}

export function setP6Presentation(
  state: WorkspaceState,
  registry: FieldRegistry,
  layout: LayoutDefinition,
): WorkspaceState {
  if (layout.revision < 0 || !Number.isInteger(layout.revision)) {
    throw new Error("INVALID_P6_LAYOUT_REVISION");
  }
  if (registry.registry_version !== "p6-field-registry.v1") {
    throw new Error("UNSUPPORTED_P6_FIELD_REGISTRY");
  }
  const fields = new Map(registry.fields.map((field) => [field.field_id, field]));
  const columns = layout.columns
    .filter((column) => column.visible)
    .sort((a, b) => a.order - b.order)
    .map((column) => {
      const field = fields.get(column.field_id);
      if (!field) throw new Error("P6_LAYOUT_FIELD_NOT_FOUND");
      return Object.freeze({
        id: field.field_id,
        label: column.label ?? field.display_name,
        dataType: toWorkspaceColumnDataType(field.data_type),
        editable: field.writable && !field.computed,
        formula: null,
        width: column.width,
        alignment: column.alignment,
        pinned: column.pinned,
        frozen: column.frozen,
      });
    });
  return { ...state, columns: Object.freeze(columns), p6FieldRegistry: registry, p6Layout: layout };
}

export function addP6Field(state: WorkspaceState, fieldId: string): WorkspaceState {
  if (!state.p6FieldRegistry || !state.p6Layout) throw new Error("P6_PRESENTATION_NOT_INITIALIZED");
  const field = state.p6FieldRegistry.fields.find((item) => item.field_id === fieldId);
  if (!field) throw new Error("P6_FIELD_NOT_FOUND");

  const existing = state.p6Layout.columns.find((column) => column.field_id === fieldId);
  if (existing) {
    if (existing.visible) throw new Error("FIELD_ALREADY_IN_LAYOUT");
    return setP6Presentation(state, state.p6FieldRegistry, updateFieldPresentation(state.p6Layout, fieldId, { visible: true }));
  }

  return setP6Presentation(state, state.p6FieldRegistry, addField(state.p6Layout, field));
}

export function removeP6Field(state: WorkspaceState, fieldId: string): WorkspaceState {
  if (!state.p6FieldRegistry || !state.p6Layout) throw new Error("P6_PRESENTATION_NOT_INITIALIZED");
  return setP6Presentation(state, state.p6FieldRegistry, removeField(state.p6Layout, fieldId));
}

export function reorderP6Fields(state: WorkspaceState, orderedFieldIds: readonly string[]): WorkspaceState {
  if (!state.p6FieldRegistry || !state.p6Layout) throw new Error("P6_PRESENTATION_NOT_INITIALIZED");
  return setP6Presentation(state, state.p6FieldRegistry, reorderFields(state.p6Layout, orderedFieldIds));
}

export function updateP6FieldPresentation(
  state: WorkspaceState,
  fieldId: string,
  patch: Parameters<typeof updateFieldPresentation>[2],
): WorkspaceState {
  if (!state.p6FieldRegistry || !state.p6Layout) throw new Error("P6_PRESENTATION_NOT_INITIALIZED");
  return setP6Presentation(state, state.p6FieldRegistry, updateFieldPresentation(state.p6Layout, fieldId, patch));
}

function toWorkspaceColumnDataType(dataType: string): WorkspaceColumnDataType {
  switch (dataType) {
    case "string":
      return "text";
    case "integer":
    case "decimal":
    case "double":
    case "percentage":
    case "cost":
    case "unit":
    case "date":
    case "datetime":
    case "duration":
    case "boolean":
    case "enum":
    case "object-id":
    case "object-id-array":
    case "string-array":
    case "complex":
    case "spread":
      return dataType;
    default:
      return "text";
  }
}

export function addFormulaColumn(state: WorkspaceState, column: WorkspaceColumn): WorkspaceState {
  if (column.formula === null || !column.formula.trim()) {
    throw new Error("FORMULA_REQUIRED");
  }
  if (state.columns.some((existing) => existing.id === column.id)) {
    throw new Error("COLUMN_ALREADY_EXISTS");
  }
  return {
    ...state,
    columns: [...state.columns, Object.freeze({ ...column })],
  };
}

export function withWbsNodes(
  state: WorkspaceState,
  nodes: readonly WorkspaceWbsNode[],
): WorkspaceState {
  const nodesById = new Map<string, WorkspaceWbsNode>();
  let rootCount = 0;
  for (const node of nodes) {
    if (
      !node.id ||
      nodesById.has(node.id) ||
      !node.name.trim() ||
      !node.localCode.trim() ||
      (node.parentKind !== "project" && node.parentKind !== "wbs") ||
      !Number.isSafeInteger(node.sequenceNumber) ||
      node.sequenceNumber < 0 ||
      !Number.isSafeInteger(node.recordRevision) ||
      node.recordRevision < 1
    ) {
      throw new Error("INVALID_WBS_NODES");
    }
    if (node.parentKind === "project") {
      if (node.parentWbsId !== null) throw new Error("INVALID_WBS_PARENT");
      rootCount += 1;
    } else if (!node.parentWbsId || node.parentWbsId === node.id) {
      throw new Error("INVALID_WBS_PARENT");
    }
    nodesById.set(node.id, node);
  }
  if (nodes.length && rootCount !== 1) throw new Error("INVALID_WBS_ROOT");

  for (const node of nodes) {
    if (node.parentKind === "wbs" && !nodesById.has(node.parentWbsId ?? "")) {
      throw new Error("INVALID_WBS_PARENT");
    }
    const visited = new Set<string>();
    let current: WorkspaceWbsNode | undefined = node;
    while (current?.parentKind === "wbs") {
      if (visited.has(current.id)) throw new Error("WORKSPACE_WBS_CYCLE");
      visited.add(current.id);
      current = nodesById.get(current.parentWbsId ?? "");
    }
  }
  for (const activity of state.activities) {
    if (!nodesById.has(activity.wbsId)) throw new Error("INVALID_ACTIVITY_WBS_REFERENCE");
  }

  return {
    ...state,
    wbsNodes: nodes.map((node) => Object.freeze({ ...node })),
    selectedWbsId: state.selectedWbsId && nodesById.has(state.selectedWbsId)
      ? state.selectedWbsId
      : null,
  };
}

/**
 * Projects authoritative date results into the activity grid and Gantt view.
 * It does not calculate or infer schedule values in the client.
 */
export function applyAuthoritativeScheduleFacts(
  state: WorkspaceState,
  facts: AuthoritativeScheduleFacts,
): WorkspaceState {
  if (!facts || typeof facts.activities !== "object" || facts.activities === null || Array.isArray(facts.activities)) {
    throw new Error("INVALID_AUTHORITATIVE_SCHEDULE_FACTS");
  }
  const rows = state.activities.map((activity) => {
    const scheduled = facts.activities[activity.id];
    if (!scheduled) return activity;
    if (
      typeof scheduled.start !== "string" ||
      typeof scheduled.finish !== "string" ||
      !Number.isFinite(Date.parse(scheduled.start)) ||
      !Number.isFinite(Date.parse(scheduled.finish)) ||
      Date.parse(scheduled.finish) < Date.parse(scheduled.start) ||
      (scheduled.duration !== undefined && (typeof scheduled.duration !== "number" || !Number.isFinite(scheduled.duration) || scheduled.duration < 0)) ||
      (scheduled.critical !== undefined && typeof scheduled.critical !== "boolean")
    ) {
      throw new Error("INVALID_AUTHORITATIVE_ACTIVITY_RESULT:" + activity.id);
    }
    for (const key of ["early_start", "early_finish", "late_start", "late_finish"] as const) {
      const value = scheduled[key];
      if (value !== undefined && (typeof value !== "string" || !Number.isFinite(Date.parse(value)))) {
        throw new Error("INVALID_AUTHORITATIVE_ACTIVITY_RESULT:" + activity.id);
      }
    }
    for (const key of ["total_float", "free_float"] as const) {
      const value = scheduled[key];
      if (value !== undefined && (typeof value !== "number" || !Number.isFinite(value))) {
        throw new Error("INVALID_AUTHORITATIVE_ACTIVITY_RESULT:" + activity.id);
      }
    }
    const progressCell = activity.cells?.progress;
    const progressPercent = activity.gantt?.progressPercent ??
      (typeof progressCell === "number" && Number.isFinite(progressCell) ? Math.max(0, Math.min(100, progressCell)) : 0);
    const gantt = Object.freeze({
      start: scheduled.start,
      finish: scheduled.finish,
      progressPercent,
      critical: scheduled.critical ?? false,
    });
    const cells: Record<string, WorkspaceCellValue> = {
      ...(activity.cells ?? {}),
      start: scheduled.start,
      finish: scheduled.finish,
    };
    if (scheduled.duration !== undefined) cells.duration = scheduled.duration;
    // Persisted P6 presentation columns are keyed by registry field IDs. The
    // same authoritative facts therefore populate those cells too; the browser
    // neither recalculates nor renames schedule results.
    if (scheduled.early_start !== undefined) cells["activity.early_start"] = scheduled.early_start;
    if (scheduled.early_finish !== undefined) cells["activity.early_finish"] = scheduled.early_finish;
    if (scheduled.late_start !== undefined) cells["activity.late_start"] = scheduled.late_start;
    if (scheduled.late_finish !== undefined) cells["activity.late_finish"] = scheduled.late_finish;
    if (scheduled.total_float !== undefined) cells["activity.total_float"] = scheduled.total_float;
    if (scheduled.free_float !== undefined) cells["activity.free_float"] = scheduled.free_float;
    if (scheduled.critical !== undefined) cells["activity.is_critical"] = scheduled.critical;
    return Object.freeze({
      ...activity,
      cells: Object.freeze(cells),
      gantt,
    });
  });
  if (rows.every((activity, index) => activity === state.activities[index])) return state;
  return { ...state, activities: Object.freeze(rows) };
}

export function withActivities(
  state: WorkspaceState,
  activities: readonly WorkspaceActivityRow[],
): WorkspaceState {
  const ids = new Set<string>();
  for (const activity of activities) {
    if (ids.has(activity.id) || !activity.id || !activity.wbsId || !activity.name) {
      throw new Error("INVALID_ACTIVITY_ROWS");
    }
    ids.add(activity.id);
    if (activity.gantt) {
      validateGanttData(activity.gantt);
    }
    if (activity.cells) {
      validateCells(activity.cells);
    }
  }

  const selectedActivityId =
    state.selectedActivityId && ids.has(state.selectedActivityId)
      ? state.selectedActivityId
      : null;

  return {
    ...state,
    activities: activities.map((activity) =>
      Object.freeze({
        ...activity,
        cells: activity.cells ? Object.freeze({ ...activity.cells }) : undefined,
        gantt: activity.gantt ? Object.freeze({ ...activity.gantt }) : undefined,
      }),
    ),
    selectedActivityId,
  };
}

export function withRelationships(
  state: WorkspaceState,
  relationships: readonly WorkspaceRelationshipRow[],
): WorkspaceState {
  const activityIds = new Set(state.activities.map((activity) => activity.id));
  const ids = new Set<string>();
  for (const relationship of relationships) {
    if (
      !relationship.id ||
      ids.has(relationship.id) ||
      !relationship.predecessorId ||
      !relationship.successorId ||
      relationship.predecessorId === relationship.successorId ||
      !activityIds.has(relationship.predecessorId) ||
      !activityIds.has(relationship.successorId) ||
      !["FS", "SS", "FF", "SF"].includes(relationship.type) ||
      !/^-?\d+(\.\d+)?$/.test(relationship.lagValue) ||
      !relationship.lagUnit ||
      !Number.isSafeInteger(relationship.recordRevision) ||
      relationship.recordRevision < 1
    ) {
      throw new Error("INVALID_WORKSPACE_RELATIONSHIPS");
    }
    ids.add(relationship.id);
  }
  return {
    ...state,
    relationships: relationships.map((relationship) => Object.freeze({ ...relationship })),
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

function validateGanttData(gantt: WorkspaceGanttData): void {
  const start = Date.parse(gantt.start);
  const finish = Date.parse(gantt.finish);
  if (
    !gantt.start ||
    !gantt.finish ||
    Number.isNaN(start) ||
    Number.isNaN(finish) ||
    finish < start ||
    !Number.isFinite(gantt.progressPercent) ||
    gantt.progressPercent < 0 ||
    gantt.progressPercent > 100 ||
    typeof gantt.critical !== "boolean"
  ) {
    throw new Error("INVALID_GANTT_DATA");
  }
}

function validateCells(cells: Readonly<Record<string, WorkspaceCellValue>>): void {
  for (const [key, value] of Object.entries(cells)) {
    if (!key.trim()) {
      throw new Error("INVALID_ACTIVITY_CELL");
    }
    if (
      value !== null &&
      typeof value !== "string" &&
      typeof value !== "number" &&
      typeof value !== "boolean"
    ) {
      throw new Error("INVALID_ACTIVITY_CELL");
    }
    if (typeof value === "number" && !Number.isFinite(value)) {
      throw new Error("INVALID_ACTIVITY_CELL");
    }
  }
}