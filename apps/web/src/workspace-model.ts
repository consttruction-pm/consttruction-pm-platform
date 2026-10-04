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

export type WorkspaceCellValue = string | number | boolean | null;

export type WorkspaceColumn = {
  id: string;
  label: string;
  dataType: WorkspaceColumnDataType;
  editable: boolean;
  formula: string | null;
  width: number;
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
  { id: "activity_id", label: "Activity ID", dataType: "text", editable: false, formula: null, width: 120 },
  { id: "activity_code", label: "Code", dataType: "text", editable: false, formula: null, width: 100 },
  { id: "activity_name", label: "Activity Name", dataType: "text", editable: true, formula: null, width: 260 },
  { id: "start", label: "Start", dataType: "date", editable: false, formula: null, width: 120 },
  { id: "finish", label: "Finish", dataType: "date", editable: false, formula: null, width: 120 },
  { id: "duration", label: "Duration", dataType: "duration", editable: false, formula: null, width: 110 },
  { id: "progress", label: "Progress", dataType: "decimal", editable: false, formula: null, width: 100 },
];

const DEFAULT_WORKSPACE_COLUMN_LABELS: Record<WorkspaceLocale, Record<string, string>> = {
  en: { activity_id: "Activity ID", activity_code: "Code", activity_name: "Activity Name", start: "Start", finish: "Finish", duration: "Duration", progress: "Progress" },
  fa: { activity_id: "شناسه فعالیت", activity_code: "کد", activity_name: "نام فعالیت", start: "شروع", finish: "پایان", duration: "مدت", progress: "پیشرفت" },
};

export function getDefaultWorkspaceColumns(locale: WorkspaceLocale = "en"): readonly WorkspaceColumn[] {
  return DEFAULT_WORKSPACE_COLUMNS.map((column) => Object.freeze({ ...column, label: DEFAULT_WORKSPACE_COLUMN_LABELS[locale][column.id] ?? column.label }));
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
    columns: getDefaultWorkspaceColumns(locale),
    activities: [],
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
    case "integer": return "integer";
    case "decimal":
    case "double":
    case "percentage":
    case "cost":
    case "unit": return "decimal";
    case "date":
    case "datetime": return "date";
    case "duration": return "duration";
    case "boolean": return "boolean";
    default: return "text";
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
