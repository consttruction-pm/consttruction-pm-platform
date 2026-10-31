    const liveSafeDialogs = new Set(["columns", "filters", "group-sort", "timescale", "bars", "bar-options", "font-row", "shortcuts", "about"]);
    if (state.project && !liveSafeDialogs.has(name)) { showLiveNotice(); return; }
/**
 * Desktop-style visual workspace shell.
 *
 * The default authenticated route supplies a server-backed WorkspaceState;
 * the shell projects its real project, WBS, activity, relationship and schedule
 * facts without recalculating or fabricating missing values. Unconnected modules
 * are clearly disabled placeholders. With no WorkspaceState, this module keeps
 * its isolated fixed-data visual fixture for local layout QA only.
 */
import { workspaceIcon } from "./workspace-icons.js";
import type { WorkspaceState } from "./workspace-model.js";

export type DemoWindowId =
  | "projects" | "wbs" | "activities" | "assignments" | "resources" | "calendars" | "reports"
  | "tracking" | "documents" | "expenses" | "thresholds" | "issues" | "risks" | "administration"
  | "network" | "trace" | "timeline" | "activity-profile" | "resource-profile" | "activity-sheet" | "resource-sheet";

type Label = { en: string; fa: string };
type Row = Record<string, string | number>;

const WINDOWS: Array<{ id: DemoWindowId; en: string; fa: string }> = [
  { id: "projects", en: "Projects", fa: "پروژه‌ها" },
  { id: "wbs", en: "WBS", fa: "WBS" },
  { id: "activities", en: "Activities", fa: "فعالیت‌ها" },
  { id: "assignments", en: "Resource Assignments", fa: "تخصیص منابع" },
  { id: "resources", en: "Resources", fa: "منابع" },
  { id: "calendars", en: "Calendars", fa: "تقویم‌ها" },
  { id: "reports", en: "Reports", fa: "گزارش‌ها" },
  { id: "tracking", en: "Tracking", fa: "پیگیری" },
  { id: "documents", en: "Documents", fa: "اسناد" },
  { id: "expenses", en: "Expenses", fa: "هزینه‌ها" },
  { id: "thresholds", en: "Thresholds", fa: "آستانه‌ها" },
  { id: "issues", en: "Issues", fa: "مسائل" },
  { id: "risks", en: "Risks", fa: "ریسک‌ها" },
  { id: "administration", en: "Administration", fa: "مدیریت" },
  { id: "network", en: "Activity Network", fa: "شبکه فعالیت" },
  { id: "trace", en: "Trace Logic", fa: "ردیابی منطق" },
  { id: "timeline", en: "Timeline", fa: "خط زمانی" },
  { id: "activity-profile", en: "Activity Usage Profile", fa: "پروفایل مصرف فعالیت" },
  { id: "resource-profile", en: "Resource Usage Profile", fa: "پروفایل مصرف منبع" },
  { id: "activity-sheet", en: "Activity Usage Spreadsheet", fa: "صفحهٔ مصرف فعالیت" },
  { id: "resource-sheet", en: "Resource Usage Spreadsheet", fa: "صفحهٔ مصرف منبع" },
];

const ACTIVITY_COLUMNS: Array<{ id: string; en: string; fa: string; width: number; numeric?: boolean }> = [
  { id: "id", en: "Activity ID", fa: "شناسه", width: 88 },
  { id: "name", en: "Activity Name", fa: "نام فعالیت", width: 226 },
  { id: "wbs", en: "WBS", fa: "WBS", width: 156 },
  { id: "type", en: "Activity Type", fa: "نوع", width: 120 },
  { id: "od", en: "Original Duration", fa: "مدت اولیه", width: 92, numeric: true },
  { id: "rd", en: "Remaining Duration", fa: "مدت باقی‌مانده", width: 92, numeric: true },
  { id: "ad", en: "Actual Duration", fa: "مدت واقعی", width: 84, numeric: true },
  { id: "start", en: "Start", fa: "شروع", width: 96 },
  { id: "finish", en: "Finish", fa: "پایان", width: 96 },
  { id: "es", en: "Early Start", fa: "شروع زود", width: 96 },
  { id: "ef", en: "Early Finish", fa: "پایان زود", width: 96 },
  { id: "ls", en: "Late Start", fa: "شروع دیر", width: 96 },
  { id: "lf", en: "Late Finish", fa: "پایان دیر", width: 96 },
  { id: "tf", en: "Total Float", fa: "شناوری کل", width: 76, numeric: true },
  { id: "ff", en: "Free Float", fa: "شناوری آزاد", width: 76, numeric: true },
  { id: "pct", en: "% Complete", fa: "درصد تکمیل", width: 76, numeric: true },
  { id: "status", en: "Status", fa: "وضعیت", width: 96 },
  { id: "calendar", en: "Calendar", fa: "تقویم", width: 140 },
  { id: "pred", en: "Predecessors", fa: "پیش‌نیازها", width: 110 },
  { id: "succ", en: "Successors", fa: "جانشین‌ها", width: 110 },
  { id: "res", en: "Resources", fa: "منابع", width: 140 },
  { id: "budgetUnits", en: "Budgeted Units", fa: "واحد بودجه", width: 96, numeric: true },
  { id: "actualUnits", en: "Actual Units", fa: "واحد واقعی", width: 90, numeric: true },
  { id: "remainingUnits", en: "Remaining Units", fa: "واحد باقی‌مانده", width: 96, numeric: true },
  { id: "budgetCost", en: "Budgeted Cost", fa: "هزینهٔ بودجه", width: 104, numeric: true },
  { id: "actualCost", en: "Actual Cost", fa: "هزینهٔ واقعی", width: 100, numeric: true },
  { id: "remainingCost", en: "Remaining Cost", fa: "هزینهٔ باقی‌مانده", width: 106, numeric: true },
  { id: "codes", en: "Activity Codes", fa: "کدهای فعالیت", width: 130 },
  { id: "constraint", en: "Constraints", fa: "محدودیت‌ها", width: 130 },
];

const DEFAULT_COLUMNS = ["id", "name", "wbs", "od", "rd", "start", "finish", "tf", "pct", "status", "res", "pred"];

type DemoActivity = {
  id: string; name: string; phase: string; wbs: string; type: string; od: number | null; rd: number | null; ad: number | null;
  start: string; finish: string; es: string; ef: string; ls: string; lf: string; tf: number | null; ff: number | null;
  pct: number | null; status: string; calendar: string; pred: string; succ: string; res: string;
  budgetUnits: number | null; actualUnits: number | null; remainingUnits: number | null; budgetCost: number | null; actualCost: number | null;
  remainingCost: number | null; codes: string; constraint: string; critical: boolean; milestone?: boolean; summary?: boolean; baseline?: string;
};

type DemoWbsNode = { code: string; name: string; level: number; total: number };
type DemoResource = { id: string; name: string; type: string; units: number; cost: number };
type DemoRelationship = { predecessorId: string; successorId: string; type: string; lagValue: string; lagUnit: string };
type LiveProjectData = {
  id: string;
  name: string;
  revision: number;
  activities: DemoActivity[];
  wbsNodes: DemoWbsNode[];
  relationships: DemoRelationship[];
  resources: DemoResource[];
  projectStart: string | null;
  projectFinish: string | null;
};

function act(
  id: string, name: string, phase: string, wbs: string, start: string, finish: string, od: number,
  pct: number, critical: boolean, extra: Partial<DemoActivity> = {},
): DemoActivity {
  const status = pct >= 100 ? "Completed" : pct > 0 ? "In Progress" : "Not Started";
  return {
    id, name, phase, wbs, type: "Task Dependent", od, rd: Math.round(od * (1 - pct / 100)), ad: Math.round(od * pct / 100),
    start, finish, es: start, ef: finish, ls: start, lf: finish, tf: critical ? 0 : 4, ff: critical ? 0 : 2,
    pct, status, calendar: "5-Day Workweek", pred: "—", succ: "—", res: "—",
    budgetUnits: 0, actualUnits: 0, remainingUnits: 0, budgetCost: 0, actualCost: 0, remainingCost: 0,
    codes: "CUBI-DEMO", constraint: "", critical, baseline: "BL-01", ...extra,
  };
}

const ACTIVITIES: DemoActivity[] = [
  act("A1000", "Project management", "Project Management", "01 Project Management", "2026-11-02", "2027-05-28", 148, 12, true, { type: "Level of Effort", res: "PM Office", budgetCost: 82000, actualCost: 9800, remainingCost: 72200, budgetUnits: 1480, actualUnits: 176, remainingUnits: 1304, succ: "A1100", critical: false }),
  act("A1010", "Kick-off and mobilisation", "Project Management", "01.01 Mobilisation", "2026-11-02", "2026-11-06", 5, 100, false, { milestone: false, pred: "—", succ: "A1100, A1200", res: "PM Office", budgetCost: 4500, actualCost: 4500, remainingCost: 0, budgetUnits: 80, actualUnits: 80, remainingUnits: 0 }),
  act("A1020", "Baseline and reporting setup", "Project Management", "01.02 Controls", "2026-11-09", "2026-11-20", 10, 55, false, { pred: "A1010", succ: "A1110", res: "Cost Engineer", budgetCost: 7800, actualCost: 4200, remainingCost: 3600, budgetUnits: 80, actualUnits: 44, remainingUnits: 36 }),
  act("A1100", "Design basis and studies", "Engineering", "02 Engineering", "2026-11-02", "2026-12-18", 35, 40, true, { type: "Hammock", res: "Engineering", budgetCost: 64500, actualCost: 25800, remainingCost: 38700, budgetUnits: 980, actualUnits: 392, remainingUnits: 588 }),
  act("A1110", "Process and hydraulic design", "Engineering", "02.01 Process", "2026-11-02", "2026-12-04", 25, 60, true, { milestone: false, pred: "A1010", succ: "A1120, A1200", res: "Process Lead", budgetCost: 26000, actualCost: 15600, remainingCost: 10400, budgetUnits: 400, actualUnits: 240, remainingUnits: 160 }),
  act("A1120", "Civil and structural design", "Engineering", "02.02 Civil", "2026-11-16", "2026-12-18", 25, 30, false, { pred: "A1110", succ: "A1300", res: "Structural Lead", budgetCost: 22000, actualCost: 6600, remainingCost: 15400, budgetUnits: 360, actualUnits: 108, remainingUnits: 252 }),
  act("A1130", "Design review gate", "Engineering", "02.03 Review", "2026-12-21", "2026-12-21", 0, 0, true, { milestone: true, type: "Finish Milestone", pred: "A1110, A1120", succ: "A1200", res: "Engineering Manager" }),
  act("A1200", "Procurement and long lead", "Procurement", "03 Procurement", "2026-11-23", "2027-02-26", 70, 18, true, { type: "Hammock", res: "Procurement", budgetCost: 148000, actualCost: 26600, remainingCost: 121400, budgetUnits: 240, actualUnits: 43, remainingUnits: 197 }),
  act("A1210", "Pump package purchase order", "Procurement", "03.01 Pumps", "2026-11-23", "2026-12-11", 15, 55, true, { pred: "A1110", succ: "A1220, A1410", res: "Buyer", budgetCost: 68000, actualCost: 37400, remainingCost: 30600, budgetUnits: 60, actualUnits: 33, remainingUnits: 27 }),
  act("A1220", "Valve package purchase order", "Procurement", "03.02 Valves", "2026-12-14", "2027-01-15", 25, 10, false, { pred: "A1210", succ: "A1410", res: "Buyer", budgetCost: 42000, actualCost: 4200, remainingCost: 37800, budgetUnits: 80, actualUnits: 8, remainingUnits: 72 }),
  act("A1230", "Pump delivery to site", "Procurement", "03.03 Delivery", "2027-02-08", "2027-02-26", 15, 0, true, { pred: "A1210", succ: "A1420", res: "Expeditor", budgetCost: 38000, actualCost: 0, remainingCost: 38000, budgetUnits: 40, actualUnits: 0, remainingUnits: 40 }),
  act("A1300", "Construction", "Construction", "04 Construction", "2027-01-04", "2027-04-30", 85, 8, true, { type: "Hammock", res: "Site team", budgetCost: 210000, actualCost: 16800, remainingCost: 193200, budgetUnits: 1400, actualUnits: 112, remainingUnits: 1288 }),
  act("A1310", "Site preparation", "Construction", "04.01 Enabling", "2027-01-04", "2027-01-15", 10, 100, true, { pred: "A1120", succ: "A1320", res: "Earthworks crew", budgetCost: 14000, actualCost: 14000, remainingCost: 0, budgetUnits: 120, actualUnits: 120, remainingUnits: 0 }),
  act("A1320", "Foundations and plinth", "Construction", "04.02 Civil", "2027-01-18", "2027-02-19", 25, 20, true, { pred: "A1310, A1130", succ: "A1330", res: "Concrete crew", budgetCost: 56000, actualCost: 11200, remainingCost: 44800, budgetUnits: 320, actualUnits: 64, remainingUnits: 256 }),
  act("A1330", "Structural steel erection", "Construction", "04.03 Steel", "2027-02-22", "2027-03-19", 20, 0, true, { pred: "A1320", succ: "A1340", res: "Steel crew", budgetCost: 72000, actualCost: 0, remainingCost: 72000, budgetUnits: 280, actualUnits: 0, remainingUnits: 280 }),
  act("A1340", "Mechanical installation", "Construction", "04.04 Mechanical", "2027-03-22", "2027-04-16", 20, 0, false, { pred: "A1330, A1230", succ: "A1350, A1500", res: "Mechanical crew", budgetCost: 68000, actualCost: 0, remainingCost: 68000, budgetUnits: 240, actualUnits: 0, remainingUnits: 240 }),
  act("A1350", "Electrical and controls", "Construction", "04.05 Electrical", "2027-04-05", "2027-04-30", 20, 0, false, { pred: "A1340", succ: "A1500", res: "Electrical crew", budgetCost: 42000, actualCost: 0, remainingCost: 42000, budgetUnits: 180, actualUnits: 0, remainingUnits: 180 }),
  act("A1400", "Testing and commissioning", "Testing & Commissioning", "05 Commissioning", "2027-05-03", "2027-05-28", 20, 0, false, { type: "Finish Milestone", res: "Commissioning", budgetCost: 36000, actualCost: 0, remainingCost: 36000, budgetUnits: 180, actualUnits: 0, remainingUnits: 180 }),
  act("A1410", "Pump alignment and run-in", "Testing & Commissioning", "05.01 Pumps", "2027-05-03", "2027-05-14", 10, 0, false, { pred: "A1340", succ: "A1420", res: "Commissioning", budgetCost: 18000, actualCost: 0, remainingCost: 18000, budgetUnits: 80, actualUnits: 0, remainingUnits: 80 }),
  act("A1420", "Performance test", "Testing & Commissioning", "05.02 Performance", "2027-05-17", "2027-05-21", 5, 0, false, { pred: "A1410, A1230", succ: "A1500", res: "Commissioning", budgetCost: 12000, actualCost: 0, remainingCost: 12000, budgetUnits: 40, actualUnits: 0, remainingUnits: 40 }),
  act("A1500", "Handover and close-out", "Testing & Commissioning", "05.03 Handover", "2027-05-28", "2027-05-28", 0, 0, false, { milestone: true, type: "Finish Milestone", pred: "A1420, A1350", succ: "—", res: "Project Manager" }),
];

const WBS_TREE = [
  { code: "1", name: "CUBI-DEMO-001 Riverside Pump Station", level: 0, total: 20 },
  { code: "1.1", name: "Project Management", level: 1, total: 3 },
  { code: "1.1.1", name: "Mobilisation", level: 2, total: 1 },
  { code: "1.1.2", name: "Controls", level: 2, total: 1 },
  { code: "1.1.3", name: "Close-out", level: 2, total: 1 },
  { code: "1.2", name: "Engineering", level: 1, total: 4 },
  { code: "1.2.1", name: "Process", level: 2, total: 1 },
  { code: "1.2.2", name: "Civil", level: 2, total: 1 },
  { code: "1.3", name: "Procurement", level: 1, total: 3 },
  { code: "1.4", name: "Construction", level: 1, total: 6 },
  { code: "1.5", name: "Testing & Commissioning", level: 1, total: 4 },
];

const RESOURCES = [
  { id: "R-100", name: "PM Office", type: "Labor", units: 1480, cost: 82000 },
  { id: "R-110", name: "Engineering", type: "Labor", units: 980, cost: 64500 },
  { id: "R-120", name: "Procurement", type: "Labor", units: 240, cost: 148000 },
  { id: "R-130", name: "Site team", type: "Labor", units: 1400, cost: 210000 },
  { id: "R-140", name: "Concrete crew", type: "Labor", units: 320, cost: 56000 },
  { id: "R-150", name: "Steel crew", type: "Labor", units: 280, cost: 72000 },
  { id: "R-160", name: "Commissioning", type: "Labor", units: 180, cost: 36000 },
  { id: "E-210", name: "Mobile crane 50t", type: "Equipment", units: 60, cost: 18000 },
];

type DemoState = {
  window: DemoWindowId;
  activityId: string;
  scale: "day" | "week" | "month" | "quarter" | "year";
  detailTab: string;
  calendarMonth: number;
  adminSection: string;
  filter: string;
  groupBy: "wbs" | "none";
  columns: string[];
  toolbars: string[];
  history: DemoWindowId[];
  forward: DemoWindowId[];
  detailsOpen: boolean;
  locale: string;
  /** When present, every displayed project/activity/WBS fact is mapped from the authenticated project read. */
  project: LiveProjectData | null;
};

function label(text: Label, locale: string): string {
  return locale.startsWith("fa") ? text.fa : text.en;
}

function t(locale: string, en: string, fa: string): string {
  return locale.startsWith("fa") ? fa : en;
}

function esc(value: unknown): string {
  return String(value ?? "")
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

function isIsoDate(value: string): boolean {
  if (value.length !== 10) return false;
  const timestamp = Date.parse(`${value}T00:00:00Z`);
  return Number.isFinite(timestamp) && new Date(timestamp).toISOString().slice(0, 10) === value;
}

function fmtDate(iso: string): string {
  if (!isIsoDate(iso)) return "—";
  const [y, m, d] = iso.split("-");
  return `${d}/${m}/${y.slice(2)}`;
}

function day(value: string): number {
  return Math.round(Date.parse(`${value}T00:00:00Z`) / 86400000);
}

const PROJECT_START = "2026-11-02";
const PROJECT_FINISH = "2027-05-28";
const PROJECT_DAYS = day(PROJECT_FINISH) + 1 - day(PROJECT_START);

function demoBarPosition(start: string, finish: string): { left: string; width: string } {
  const left = (day(start) - day(PROJECT_START)) / PROJECT_DAYS * 100;
  const width = Math.max(0.4, (day(finish) - day(start) + 1) / PROJECT_DAYS * 100);
  return { left: `${Math.max(0, left)}%`, width: `${Math.min(100, width)}%` };
}

function activitiesFor(state: DemoState): DemoActivity[] {
  return state.project?.activities ?? ACTIVITIES;
}

function wbsNodesFor(state: DemoState): DemoWbsNode[] {
  return state.project?.wbsNodes ?? WBS_TREE;
}

function resourcesFor(state: DemoState): DemoResource[] {
  return state.project?.resources ?? RESOURCES;
}

function projectIdFor(state: DemoState): string {
  return state.project?.id ?? "CUBI-DEMO-001";
}

function projectNameFor(state: DemoState): string {
  return state.project?.name ?? "Riverside Pump Station Upgrade";
}

function projectRangeFor(state: DemoState): { start: string; finish: string } | null {
  if (!state.project) return { start: PROJECT_START, finish: PROJECT_FINISH };
  if (!state.project.projectStart || !state.project.projectFinish) return null;
  return { start: state.project.projectStart, finish: state.project.projectFinish };
}

function numericDisplay(value: number | null, suffix = ""): string {
  return value === null || !Number.isFinite(value) ? "—" : `${value}${suffix}`;
}

function filterActivities(state: DemoState): DemoActivity[] {
  const rows = activitiesFor(state);
  const query = state.filter.trim().toLowerCase();
  if (!query) return rows;
  return rows.filter((row) => `${row.id} ${row.name} ${row.wbs} ${row.res}`.toLowerCase().includes(query));
}

function renderActivityTable(state: DemoState, columns: string[]): string {
  const rows = filterActivities(state);
  const phases = state.groupBy === "wbs" ? [...new Set(rows.map((row) => row.phase))] : [""];
  const header = `<thead><tr><th class="cp-vd-rownum">#</th>${columns.map((id) => {
    const column = ACTIVITY_COLUMNS.find((item) => item.id === id) ?? ACTIVITY_COLUMNS[0];
    return `<th style="width:${column.width}px" class="${column.numeric ? "is-numeric" : ""}">${esc(label(column, state.locale))}</th>`;
  }).join("")}</tr></thead>`;
  let index = 0;
  const body = phases.map((phase) => {
    const group = rows.filter((row) => row.phase === phase);
    const groupRow = phase
      ? `<tr class="cp-vd-band"><td colspan="${columns.length + 1}">▾ ${esc(phase)} <span>${group.length} ${esc(t(state.locale, "activities", "فعالیت"))}</span></td></tr>`
      : "";
    const dataRows = group.map((row, rowIndex) => {
      index += 1;
      return `<tr class="cp-vd-row${row.id === state.activityId ? " is-selected" : ""}${row.critical ? " is-critical" : ""}" data-vd-activity="${esc(row.id)}">
        <td class="cp-vd-rownum">${index}</td>
        ${columns.map((id) => {
          const column = ACTIVITY_COLUMNS.find((item) => item.id === id) ?? ACTIVITY_COLUMNS[0];
          let value: string | number = (row as unknown as Record<string, string | number>)[id] ?? "";
          if (["start", "finish", "es", "ef", "ls", "lf"].includes(id)) value = fmtDate(String(value));
          if (id === "pct") value = row.pct === null ? "—" : `${row.pct}%`;
          if (["budgetCost", "actualCost", "remainingCost"].includes(id)) value = value !== "" && Number(value) ? Number(value).toLocaleString("en-US") : "—";
          return `<td class="${column.numeric ? "is-numeric" : ""}${id === "id" ? " is-id" : ""}${row.critical && id === "tf" ? " is-red" : ""}">${esc(value)}</td>`;
        }).join("")}
      </tr>`;
    }).join("");
    return groupRow + dataRows;
  }).join("");
  return `<div class="cp-vd-tablewrap"><table class="cp-vd-table" data-vd-table>${header}<tbody>${body}</tbody></table></div>`;
}

function barPosition(start: string, finish: string, state: DemoState): { left: string; width: string } {
  const range = projectRangeFor(state);
  if (!range || !/^\\d{4}-\\d{2}-\\d{2}$/.test(start) || !/^\\d{4}-\\d{2}-\\d{2}$/.test(finish)) {
    return { left: "0%", width: "0%" };
  }
  const startDay = day(range.start);
  const endDay = day(range.finish) + 1;
  const total = Math.max(1, endDay - startDay);
  const left = (day(start) - startDay) / total * 100;
  const width = Math.max(0.4, (day(finish) - day(start) + 1) / total * 100);
  return { left: `${Math.max(0, left)}%`, width: `${Math.min(100, width)}%` };
}

type AxisBand = { label: string; left: number; width: number };
type GanttAxis = { rows: AxisBand[][]; column: string; minWidth: string };

function axisBand(label: string, from: number, to: number, rangeStart: number, rangeEnd: number): AxisBand {
  const left = Math.max(0, (from - rangeStart) / (rangeEnd - rangeStart) * 100);
  const width = Math.max(0, (Math.min(to, rangeEnd) - from) / (rangeEnd - rangeStart) * 100);
  return { label, left, width };
}

function isoWeek(dayNumber: number): number {
  const date = new Date(dayNumber * 86400000);
  const target = new Date(date.valueOf());
  target.setUTCDate(target.getUTCDate() - ((target.getUTCDay() + 6) % 7) + 3);
  const firstThursday = new Date(Date.UTC(target.getUTCFullYear(), 0, 4));
  return 1 + Math.round((target.getTime() - firstThursday.getTime()) / (7 * 86400000));
}

function monthLabel(dayNumber: number, locale: string): string {
  const date = new Date(dayNumber * 86400000);
  return new Intl.DateTimeFormat(locale.startsWith("fa") ? "fa-IR" : "en", {
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  }).format(date);
}

// The ruler is derived from the loaded project's scheduled date range. The
// visual shell never borrows dates from another fixture project.
function buildAxis(scale: DemoState["scale"], locale: string, state: DemoState): GanttAxis {
  const range = projectRangeFor(state);
  if (!range) return { rows: [], column: "100%", minWidth: "0px" };
  const start = day(range.start);
  const end = day(range.finish) + 1;
  if (end <= start) return { rows: [], column: "100%", minWidth: "0px" };
  const band = (label: string, from: number, to: number) => axisBand(label, from, to, start, end);
  const monthStart = (value: number) => {
    const date = new Date(value * 86400000);
    return Math.floor(Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), 1) / 86400000);
  };
  const nextMonth = (value: number) => {
    const date = new Date(value * 86400000);
    return Math.floor(Date.UTC(date.getUTCFullYear(), date.getUTCMonth() + 1, 1) / 86400000);
  };
  const firstMonth = monthStart(start);
  const monthStarts: number[] = [];
  for (let cursor = firstMonth; cursor < end; cursor = nextMonth(cursor)) {
    monthStarts.push(Math.max(start, cursor));
  }
  const months = monthStarts.map((from, index) => {
    const actualMonth = index === 0 ? firstMonth : monthStart(from);
    return band(monthLabel(actualMonth, locale), from, Math.min(end, nextMonth(actualMonth)));
  });
  const years: AxisBand[] = [];
  const firstYear = new Date(start * 86400000).getUTCFullYear();
  const lastYear = new Date((end - 1) * 86400000).getUTCFullYear();
  for (let year = firstYear; year <= lastYear; year += 1) {
    const from = Math.max(start, Math.floor(Date.UTC(year, 0, 1) / 86400000));
    const to = Math.min(end, Math.floor(Date.UTC(year + 1, 0, 1) / 86400000));
    years.push(band(String(year), from, to));
  }
  const quarters: AxisBand[] = [];
  const quarterStart = Math.floor(Date.UTC(firstYear, Math.floor(new Date(start * 86400000).getUTCMonth() / 3) * 3, 1) / 86400000);
  for (let cursor = quarterStart; cursor < end;) {
    const date = new Date(cursor * 86400000);
    const year = date.getUTCFullYear();
    const quarter = Math.floor(date.getUTCMonth() / 3) + 1;
    const next = Math.floor(Date.UTC(year, quarter * 3, 1) / 86400000);
    quarters.push(band(locale.startsWith("fa") ? `فصل ${quarter} ${year}` : `Q${quarter} ${year}`, Math.max(start, cursor), Math.min(end, next)));
    cursor = next;
  }
  const weeks: AxisBand[] = [];
  const weekStart = start - ((new Date(start * 86400000).getUTCDay() + 6) % 7);
  for (let from = weekStart; from < end; from += 7) {
    weeks.push(band(`W${String(isoWeek(from)).padStart(2, "0")}`, Math.max(start, from), Math.min(end, from + 7)));
  }
  const days: AxisBand[] = [];
  for (let from = start; from < end; from += 1) {
    days.push(band(String(new Date(from * 86400000).getUTCDate()), from, from + 1));
  }
  const totalDays = end - start;
  switch (scale) {
    case "day": return { rows: [months, days], column: `${100 / Math.max(1, days.length)}%`, minWidth: `${totalDays * 18}px` };
    case "week": return { rows: [months, weeks], column: `${100 / Math.max(1, weeks.length)}%`, minWidth: `${weeks.length * 30}px` };
    case "quarter": return { rows: [years, quarters], column: `${100 / Math.max(1, quarters.length)}%`, minWidth: "0px" };
    case "year": return { rows: [years, quarters], column: `${100 / Math.max(1, years.length)}%`, minWidth: "0px" };
    default: return { rows: [months], column: `${100 / Math.max(1, months.length)}%`, minWidth: "0px" };
  }
}

function renderGanttTools(state: DemoState): string {
  return `<div class="cp-vd-gantt-tools">
    <div class="cp-vd-scale" role="group" aria-label="${esc(t(state.locale, "Timescale", "مقیاس زمانی"))}">
      ${(["day", "week", "month", "quarter", "year"] as const).map((scale) => `<button type="button" data-vd-scale="${scale}" class="${scale === state.scale ? "is-active" : ""}">${esc(t(state.locale, scale, { day: "روز", week: "هفته", month: "ماه", quarter: "فصل", year: "سال" }[scale]))}</button>`).join("")}
    </div>
    <span class="cp-vd-ganttbar-spacer"></span>
    <span class="cp-vd-legend"><i class="is-normal"></i>${esc(t(state.locale, "Normal", "عادی"))}<i class="is-critical"></i>${esc(t(state.locale, "Critical", "بحرانی"))}<i class="is-summary"></i>${esc(t(state.locale, "Summary", "خلاصه"))}<i class="is-milestone"></i>${esc(t(state.locale, "Milestone", "نقطهٔ عطف"))}${state.project ? "" : `<i class="is-datadate"></i>${esc(t(state.locale, "Data date 03-Dec-2026", "تاریخ داده ۱۲ آذر ۱۴۰۵"))}`}</span>
  </div>`;
}

function renderGantt(state: DemoState): string {
  const rows = filterActivities(state);
  const groups = state.groupBy === "wbs"
    ? [...new Set(rows.map((row) => row.phase))].map((phase) => ({ phase, members: rows.filter((row) => row.phase === phase) }))
    : [{ phase: "", members: rows }];
  const axis = buildAxis(state.scale, state.locale, state);
  const range = projectRangeFor(state);
  if (!range) {
    return `<div class="cp-vd-gantt" data-vd-gantt><div class="cp-vd-empty">${esc(t(state.locale, "No authoritative schedule dates are available for this project yet.", "هنوز تاریخ‌های معتبر زمان‌بندی برای این پروژه موجود نیست."))}</div></div>`;
  }
  const dataDate = state.project ? null : (day("2026-12-03") - day(range.start)) / Math.max(1, day(range.finish) + 1 - day(range.start)) * 100;
  const rtl = state.locale.startsWith("fa");
  const ruler = axis.rows.map((bandRow) => `<div class="cp-vd-axisrow">${bandRow.map((band) => `<span style="inset-inline-start:${band.left}%;width:${band.width}%">${esc(band.label)}</span>`).join("")}</div>`).join("");

  // Lay the rows out once so dependency connectors can anchor to real row tops.
  let cursor = 0;
  const rowTop = new Map<string, number>();
  const body = groups.map((group) => {
    const band = group.phase
      ? `<div class="cp-vd-gantt-row is-band"><div class="cp-vd-gantt-track"></div></div>`
      : "";
    if (group.phase) cursor += 24;
    const members = group.members.map((row) => {
      const position = barPosition(row.start, row.finish, state);
      const summary = row.type === "Hammock" || row.id === "A1000" || row.id === "A1100" || row.id === "A1200" || row.id === "A1300" || row.id === "A1400";
      const shape = row.milestone ? "is-milestone" : summary ? "is-summary" : row.critical ? "is-critical" : "is-normal";
      rowTop.set(row.id, cursor + 13);
      cursor += 26;
      return `<div class="cp-vd-gantt-row${row.id === state.activityId ? " is-selected" : ""}" data-vd-activity="${esc(row.id)}">
        <div class="cp-vd-gantt-track">
          ${summary || state.project ? "" : `<span class="cp-vd-bar is-baseline" style="inset-inline-start:${position.left};width:${position.width}" title="BL-01"></span>`}
          ${row.milestone
            ? `<span class="cp-vd-bar ${shape} ${row.critical ? "is-critical" : ""}" style="inset-inline-start:${position.left}" title="${esc(row.name)}"></span>`
            : `<span class="cp-vd-bar ${shape}${summary && row.critical ? " is-critical" : ""}" style="inset-inline-start:${position.left};width:${position.width}" title="${esc(row.name)} — ${numericDisplay(row.pct, "%")}">
                ${summary || row.pct === null ? "" : `<span class="cp-vd-bar-progress" style="width:${row.pct}%"></span>`}
              </span>`}
          ${position.width !== "0%" ? `<span class="cp-vd-bar-label${summary ? " is-summary" : ""}" style="inset-inline-start:calc(${position.left} + ${summary ? "6px" : position.width})">${esc(row.name)}</span>` : ""}
        </div>
      </div>`;
    }).join("");
    return band + members;
  }).join("");
  const totalHeight = Math.max(1, cursor);

  // Finish-to-start relationships drawn from the bar dates of both activities.
  const links: Array<[string, string]> = state.project
    ? state.project.relationships.map((link) => [link.predecessorId, link.successorId])
    : [
      ["A1010", "A1100"], ["A1110", "A1120"], ["A1120", "A1130"], ["A1210", "A1220"],
      ["A1310", "A1320"], ["A1320", "A1330"], ["A1330", "A1340"], ["A1340", "A1410"], ["A1410", "A1420"],
    ];
  const toX = (value: number): number => (rtl ? 100 - value : value);
  const paths = links.map(([from, to]) => {
    const rowsForLinks = activitiesFor(state);
    const pred = rowsForLinks.find((item) => item.id === from);
    const succ = rowsForLinks.find((item) => item.id === to);
    const y1 = rowTop.get(from);
    const y2 = rowTop.get(to);
    if (!pred || !succ || y1 === undefined || y2 === undefined) return "";
    const predPosition = barPosition(pred.start, pred.finish, state);
    const succPosition = barPosition(succ.start, succ.finish, state);
    if (predPosition.width === "0%" || succPosition.width === "0%") return "";
    const start = parseFloat(predPosition.left);
    const width = parseFloat(predPosition.width);
    const x1 = toX(start + width);
    const x2 = toX(parseFloat(succPosition.left));
    const stub = x2 >= x1 ? 1.2 : -1.2;
    const marker = pred.critical || succ.critical ? "cp-vd-arrow-critical" : "cp-vd-arrow";
    return `<path d="M ${x1} ${y1} h ${stub} V ${y2} H ${x2}" class="${marker === "cp-vd-arrow-critical" ? "is-critical" : ""}" marker-end="url(#${marker})"></path>`;
  }).join("");

  return `<div class="cp-vd-gantt" data-vd-gantt data-scale="${state.scale}" style="--cp-vd-gantt-min:${axis.minWidth};--cp-vd-col:${axis.column}">
    <div class="cp-vd-gantt-months ${axis.rows.length > 1 ? "is-two" : ""}">${ruler}</div>
    <div class="cp-vd-gantt-body">
${dataDate === null ? "" : `<div class="cp-vd-gantt-today" style="inset-inline-start:${dataDate}%" title="${esc(t(state.locale, "Data date 03-Dec-2026", "تاریخ داده ۱۲ آذر ۱۴۰۵"))}"></div>`}
      ${body}
      <svg class="cp-vd-links" viewBox="0 0 100 ${totalHeight}" preserveAspectRatio="none" aria-hidden="true">
        <defs>
          <marker id="cp-vd-arrow" markerWidth="5" markerHeight="5" refX="4.5" refY="2.5" orient="auto"><path d="M0,0 L5,2.5 L0,5 z" fill="#44536a"></path></marker>
          <marker id="cp-vd-arrow-critical" markerWidth="5" markerHeight="5" refX="4.5" refY="2.5" orient="auto"><path d="M0,0 L5,2.5 L0,5 z" fill="#c0392b"></path></marker>
        </defs>
        ${paths}
      </svg>
    </div>
  </div>`;
}

function renderDetails(state: DemoState): string {
  const tabs = [
    ["general", "General", "عمومی"], ["status", "Status", "وضعیت"], ["resources", "Resources", "منابع"],
    ["predecessors", "Predecessors", "پیش‌نیازها"], ["successors", "Successors", "جانشین‌ها"], ["codes", "Codes", "کدها"],
    ["discussion", "Discussion", "بحث"], ["notebook", "Notebook", "دفترچه"], ["steps", "Steps", "گام‌ها"],
    ["feedback", "Feedback", "بازخورد"], ["documents", "Documents", "اسناد"], ["expenses", "Expenses", "هزینه‌ها"],
    ["summary", "Summary", "خلاصه"], ["relationships", "Relationships", "روابط"], ["risks", "Risks", "ریسک‌ها"],
    ["udfs", "UDFs", "فیلد سفارشی"], ["history", "Update History", "تاریخچه"],
  ];
  const rows = activitiesFor(state);
  const row = rows.find((item) => item.id === state.activityId) ?? rows[0] ?? null;
  if (!row) {
    return `<div class="cp-vd-empty">${esc(t(state.locale, "No activities are available in this project.", "در این پروژه فعالیتی موجود نیست."))}</div>`;
  }
  const index = rows.findIndex((item) => item.id === row.id);
  const prev = index > 0 ? rows[index - 1]?.id ?? "" : "";
  const next = rows[index + 1]?.id ?? "";
  const visibleTabs = state.project
    ? tabs.filter(([id]) => ["general", "status", "predecessors", "successors", "summary"].includes(String(id)))
    : tabs;
  if (state.project && !visibleTabs.some(([id]) => id === state.detailTab)) state.detailTab = "general";
  const fields = (pairs: Array<[string, string, string]>): string => `<div class="cp-vd-fields">${pairs.map(([en, fa, value]) => `<label><span>${esc(t(state.locale, en, fa))}</span><input value="${esc(value)}" readonly></label>`).join("")}</div>`;
  const contents: Record<string, string> = {
    general: row ? fields([["Activity ID", "شناسه", row.id], ["Activity name", "نام فعالیت", row.name], ["WBS", "WBS", row.wbs], ["Activity type", "نوع", row.type], ["Calendar", "تقویم", row.calendar], ["Original duration", "مدت اولیه", numericDisplay(row.od, " d")], ["Remaining duration", "مدت باقی‌مانده", numericDisplay(row.rd, " d")], ["% complete", "درصد تکمیل", numericDisplay(row.pct, "%")], ["Status", "وضعیت", row.status], ["Critical", "بحرانی", row.critical ? "Yes" : "No"], ["Resource", "منبع", row.res], ["Project", "پروژه", projectIdFor(state)]]) : "",
    status: row ? fields([["Status", "وضعیت", row.status], ["% complete", "درصد تکمیل", numericDisplay(row.pct, "%")], ["Start", "شروع", fmtDate(row.start)], ["Finish", "پایان", fmtDate(row.finish)], ["Total float", "شناوری کل", numericDisplay(row.tf, " d")], ["Remaining duration", "مدت باقی‌مانده", numericDisplay(row.rd, " d")]]) : "",
    resources: state.project
      ? `<p class="cp-vd-note">${esc(t(state.locale, "Resource assignments are not part of the current authenticated workspace read.", "تخصیص منابع هنوز در خواندن محیط کار متصل نشده است."))}</p>`
      : `<table class="cp-vd-mini"><thead><tr><th>${esc(t(state.locale, "Resource", "منبع"))}</th><th>${esc(t(state.locale, "Budgeted units", "واحد بودجه"))}</th><th>${esc(t(state.locale, "Cost", "هزینه"))}</th></tr></thead><tbody><tr><td>${esc(row.res)}</td><td>${numericDisplay(row.budgetUnits)}</td><td>${numericDisplay(row.budgetCost)}</td></tr></tbody></table><p class="cp-vd-note">${esc(t(state.locale, "Sample assignment shown for layout review.", "تخصیص نمونه برای بازبینی چیدمان."))}</p>`,
    predecessors: `<table class="cp-vd-mini"><thead><tr><th>${esc(t(state.locale, "Activity", "فعالیت"))}</th><th>${esc(t(state.locale, "Type", "نوع"))}</th><th>${esc(t(state.locale, "Lag", "تأخیر"))}</th></tr></thead><tbody>${(row?.pred === "—" || !row ? [] : row.pred.split(", ")).map((id) => {
      const link = state.project?.relationships.find((item) => item.predecessorId === id && item.successorId === row?.id);
      return `<tr><td>${esc(id)}</td><td>${esc(link?.type ?? "FS")}</td><td>${esc(link ? `${link.lagValue} ${link.lagUnit}` : "—")}</td></tr>`;
    }).join("") || `<tr><td colspan="3">${esc(t(state.locale, "No predecessors", "بدون پیش‌نیاز"))}</td></tr>`}</tbody></table>`,
    successors: `<table class="cp-vd-mini"><thead><tr><th>${esc(t(state.locale, "Activity", "فعالیت"))}</th><th>${esc(t(state.locale, "Type", "نوع"))}</th><th>${esc(t(state.locale, "Lag", "تأخیر"))}</th></tr></thead><tbody>${(row?.succ === "—" || !row ? [] : row.succ.split(", ")).map((id) => {
      const link = state.project?.relationships.find((item) => item.predecessorId === row?.id && item.successorId === id);
      return `<tr><td>${esc(id)}</td><td>${esc(link?.type ?? "FS")}</td><td>${esc(link ? `${link.lagValue} ${link.lagUnit}` : "—")}</td></tr>`;
    }).join("") || `<tr><td colspan="3">${esc(t(state.locale, "No successors", "بدون جانشین"))}</td></tr>`}</tbody></table>`,
    codes: state.project
      ? fields([["Activity code", "کد فعالیت", row.codes], ["Phase", "فاز", row.phase]])
      : fields([["Activity code", "کد فعالیت", row.codes], ["Phase", "فاز", row.phase], ["Discipline", "رشته", "Mechanical"]]),
    discussion: `<div class="cp-vd-note">${esc(t(state.locale, "Sample note: access route confirmed with the site team.", "یادداشت نمونه: مسیر دسترسی با تیم کارگاه تأیید شد."))}</div>`,
    notebook: `<div class="cp-vd-note">${esc(t(state.locale, "Sample notebook entry for visual review.", "مدخل نمونهٔ دفترچه برای بازبینی بصری."))}</div>`,
    steps: `<table class="cp-vd-mini"><thead><tr><th>#</th><th>${esc(t(state.locale, "Step", "گام"))}</th><th>${esc(t(state.locale, "Weight", "وزن"))}</th><th>${esc(t(state.locale, "% complete", "درصد"))}</th></tr></thead><tbody><tr><td>1</td><td>${esc(t(state.locale, "Prepare", "آماده‌سازی"))}</td><td>40</td><td>100</td></tr><tr><td>2</td><td>${esc(t(state.locale, "Install", "نصب"))}</td><td>60</td><td>25</td></tr></tbody></table>`,
    feedback: `<div class="cp-vd-note">${esc(t(state.locale, "Sample field feedback.", "بازخورد نمونهٔ کارگاه."))}</div>`,
    documents: `<table class="cp-vd-mini"><thead><tr><th>${esc(t(state.locale, "Document", "سند"))}</th><th>${esc(t(state.locale, "Revision", "ویرایش"))}</th></tr></thead><tbody><tr><td>ITP-Pump-01.pdf</td><td>B</td></tr></tbody></table>`,
    expenses: `<table class="cp-vd-mini"><thead><tr><th>${esc(t(state.locale, "Expense", "هزینه"))}</th><th>${esc(t(state.locale, "Budget", "بودجه"))}</th></tr></thead><tbody><tr><td>${esc(row.res)}</td><td>${numericDisplay(row.budgetCost)}</td></tr></tbody></table>`,
    summary: fields([["Early start", "شروع زود", fmtDate(row.es)], ["Early finish", "پایان زود", fmtDate(row.ef)], ["Late start", "شروع دیر", fmtDate(row.ls)], ["Late finish", "پایان دیر", fmtDate(row.lf)], ["Free float", "شناوری آزاد", numericDisplay(row.ff, " d")], ["Critical", "بحرانی", row.critical ? "Yes" : "No"]]),
    relationships: `<table class="cp-vd-mini"><thead><tr><th>${esc(t(state.locale, "Predecessor", "پیش‌نیاز"))}</th><th>${esc(t(state.locale, "Successor", "جانشین"))}</th><th>${esc(t(state.locale, "Type", "نوع"))}</th></tr></thead><tbody><tr><td>${esc(row.pred)}</td><td>${esc(row.succ)}</td><td>FS</td></tr></tbody></table>`,
    risks: `<table class="cp-vd-mini"><thead><tr><th>${esc(t(state.locale, "Risk", "ریسک"))}</th><th>${esc(t(state.locale, "Rating", "درجه"))}</th></tr></thead><tbody><tr><td>${esc(t(state.locale, "Weather delay", "تأخیر جوی"))}</td><td>Medium</td></tr></tbody></table>`,
    udfs: fields([["Custom field", "فیلد سفارشی", "—"]]),
    history: `<p class="cp-vd-note">${esc(t(state.locale, "No saved update history in the visual demo.", "در نمایش بصری تاریخچه‌ای ذخیره نشده است."))}</p>`,
  };
  return `<div class="cp-vd-details${state.detailsOpen ? "" : " is-collapsed"}">
    <div class="cp-vd-details-head">
      <button type="button" class="cp-vd-details-toggle" data-vd-details-toggle aria-expanded="${state.detailsOpen}" aria-controls="cp-vd-details-body" title="${esc(t(state.locale, state.detailsOpen ? "Collapse details" : "Expand details", state.detailsOpen ? "بستن جزئیات" : "باز کردن جزئیات"))}"><i>${state.detailsOpen ? "▾" : "▸"}</i><h3>${esc(t(state.locale, "Activity Details", "جزئیات فعالیت"))}</h3></button>
      <div class="cp-vd-nav">
        <button type="button" data-vd-prev="${esc(prev)}" ${prev ? "" : "disabled"} aria-label="${esc(t(state.locale, "Previous activity", "فعالیت قبلی"))}">‹</button>
        <strong>${esc(row.id)}</strong>
        <button type="button" data-vd-next="${esc(next)}" ${next ? "" : "disabled"} aria-label="${esc(t(state.locale, "Next activity", "فعالیت بعدی"))}">›</button>
        <button type="button" data-vd-dialog="customize-details" title="${esc(t(state.locale, "Customize tabs", "سفارشی‌سازی زبانه‌ها"))}">⚙</button>
      </div>
    </div>
    <div class="cp-vd-details-body" id="cp-vd-details-body">
      <div class="cp-vd-dtabs" role="tablist">${visibleTabs.map(([id, en, fa]) => `<button type="button" role="tab" data-vd-dtab="${id}" class="${state.detailTab === id ? "is-active" : ""}" aria-selected="${state.detailTab === id}">${esc(t(state.locale, en, fa))}</button>`).join("")}</div>
      <div class="cp-vd-dpanel" data-vd-dpanel>${contents[state.detailTab] ?? contents.general}</div>
    </div>
  </div>`;
}

const CAL_DAY_ORDER = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"] as const;
const CAL_DAY_NAMES: Record<string, [string, string]> = {
  Sun: ["Sun", "یکشنبه"], Mon: ["Mon", "دوشنبه"], Tue: ["Tue", "سه‌شنبه"], Wed: ["Wed", "چهارشنبه"],
  Thu: ["Thu", "پنجشنبه"], Fri: ["Fri", "جمعه"], Sat: ["Sat", "شنبه"],
};
const CAL_MONTHS: Array<[string, string, number, number]> = [
  ["November", "نوامبر", 2026, 10],
  ["December", "دسامبر", 2026, 11],
  ["January", "ژانویه", 2027, 0],
  ["February", "فوریه", 2027, 1],
  ["March", "مارس", 2027, 2],
  ["April", "آوریل", 2027, 3],
  ["May", "مه", 2027, 4],
];
const CAL_NONWORK = new Set(["Thu", "Fri"]);

// Persian weeks start on Saturday, so the column order mirrors while the actual
// weekday of day 1 (not an assumed Monday) decides the leading blanks.
function calendarGrid(locale: string, year: number, month: number): string {
  const order = locale.startsWith("fa") ? ["Sat", "Sun", "Mon", "Tue", "Wed", "Thu", "Fri"] : [...CAL_DAY_ORDER];
  const first = new Date(Date.UTC(year, month, 1));
  const lead = order.indexOf(CAL_DAY_ORDER[first.getUTCDay()]);
  const total = new Date(Date.UTC(year, month + 1, 0)).getUTCDate();
  const heads = order.map((key) => `<span class="is-head">${esc(t(locale, CAL_DAY_NAMES[key][0], CAL_DAY_NAMES[key][1]))}</span>`).join("");
  const blanks = Array.from({ length: lead }, () => "<span></span>").join("");
  const cells = Array.from({ length: total }, (_, offset) => {
    const dayNumber = offset + 1;
    const key = CAL_DAY_ORDER[(first.getUTCDay() + offset) % 7];
    const isDataDate = year === 2026 && month === 11 && dayNumber === 3;
    return `<span class="${CAL_NONWORK.has(key) ? "is-holiday" : ""}${isDataDate ? " is-today" : ""}"${isDataDate ? ` title="${esc(t(locale, "Data date", "تاریخ داده"))}"` : ""}>${dayNumber}</span>`;
  }).join("");
  return heads + blanks + cells;
}

function renderCalendars(state: DemoState): string {
  const fa = state.locale.startsWith("fa");
  const index = Math.max(0, Math.min(CAL_MONTHS.length - 1, state.calendarMonth));
  const [enMonth, faMonth, year, month] = CAL_MONTHS[index];
  const order = fa ? ["Sat", "Sun", "Mon", "Tue", "Wed", "Thu", "Fri"] : [...CAL_DAY_ORDER];
  const dayRows = order.map((key) => `<tr><td>${esc(t(state.locale, CAL_DAY_NAMES[key][0], CAL_DAY_NAMES[key][1]))}</td><td>${CAL_NONWORK.has(key) ? esc(t(state.locale, "Nonwork", "تعطیل")) : "08:00 – 16:00"}</td></tr>`).join("");
  const monthLabel = fa ? `${faMonth} ${year === 2026 ? "۲۰۲۶" : "۲۰۲۷"}` : `${enMonth} ${year}`;
  return `<section class="cp-vd-windowbody"><header class="cp-vd-winhead"><h2>${esc(t(state.locale, "Calendars", "تقویم‌ها"))}</h2><div class="cp-vd-winactions"><button type="button" class="cp-vd-btn" data-vd-dialog="calendar">${esc(t(state.locale, "Calendar editor", "ویرایش تقویم"))}</button></div></header>
    <div class="cp-vd-cal-layout">
      <div class="cp-vd-calendar">
        <div class="cp-vd-cal-head">
          <button type="button" data-vd-cal-prev ${index === 0 ? "disabled" : ""} aria-label="${esc(t(state.locale, "Previous month", "ماه قبل"))}">${fa ? "›" : "‹"}</button>
          <strong>${esc(monthLabel)}</strong>
          <button type="button" data-vd-cal-next ${index === CAL_MONTHS.length - 1 ? "disabled" : ""} aria-label="${esc(t(state.locale, "Next month", "ماه بعد"))}">${fa ? "‹" : "›"}</button>
        </div>
        <div class="cp-vd-cal-grid">${calendarGrid(state.locale, year, month)}</div>
        <div class="cp-vd-legend"><span class="is-standard">${esc(t(state.locale, "Standard", "استاندارد"))}</span><span class="is-nonwork">${esc(t(state.locale, "Nonwork", "تعطیل"))}</span><span class="is-datadate">${esc(t(state.locale, "Data date", "تاریخ داده"))}</span></div>
      </div>
      <aside class="cp-vd-cal-side">
        <h3>${esc(t(state.locale, "5-Day Workweek (Sat–Wed)", "هفتهٔ کاری ۵ روزه (شنبه–چهارشنبه)"))}</h3>
        <table class="cp-vd-mini"><thead><tr><th>${esc(t(state.locale, "Day", "روز"))}</th><th>${esc(t(state.locale, "Work hours", "ساعت کاری"))}</th></tr></thead><tbody>${dayRows}</tbody></table>
        <p class="cp-vd-note">${esc(t(state.locale, "Sample calendar for visual review. Holidays and work hours are fixed demo data.", "تقویم نمونه برای بازبینی بصری. تعطیلات و ساعت کاری دادهٔ ثابت نمایشی است."))}</p>
      </aside>
    </div></section>`;
}

const ADMIN_SECTIONS: Array<[string, string, string]> = [
  ["users", "Users", "کاربران"],
  ["security", "Security profiles", "پروفایل‌های امنیتی"],
  ["preferences", "Global preferences", "تنظیمات عمومی"],
  ["currencies", "Currencies", "ارزها"],
  ["codes", "Activity codes", "کدهای فعالیت"],
  ["udfs", "UDFs", "فیلدهای سفارشی"],
];

function renderAdministration(state: DemoState): string {
  const tr = (en: string, fa: string): string => t(state.locale, en, fa);
  const section = ADMIN_SECTIONS.some(([id]) => id === state.adminSection) ? state.adminSection : "users";
  const table = (heads: string[], body: string): string => `<table class="cp-vd-table"><thead><tr>${heads.map((head) => `<th>${esc(head)}</th>`).join("")}</tr></thead><tbody>${body}</tbody></table>`;
  const note = `<p class="cp-vd-note">${esc(tr("Sample administration data for visual review.", "دادهٔ نمونهٔ مدیریت برای بازبینی بصری."))}</p>`;
  const contents: Record<string, string> = {
    users: table(
      [tr("User", "کاربر"), tr("Name", "نام"), tr("Profile", "پروفایل"), tr("Status", "وضعیت")],
      `<tr><td>planner</td><td>Demo Planner</td><td>Project Manager</td><td>Active</td></tr><tr><td>viewer</td><td>Demo Viewer</td><td>Read only</td><td>Active</td></tr><tr><td>admin</td><td>Demo Administrator</td><td>Administrator</td><td>Active</td></tr>`,
    ) + note,
    security: table(
      [tr("Profile", "پروفایل"), tr("Users", "کاربران"), tr("Access", "دسترسی"), tr("Privileges", "اختیارات")],
      `<tr><td>Administrator</td><td>1</td><td>Full</td><td>All administrative commands</td></tr><tr><td>Project Manager</td><td>3</td><td>Project</td><td>Open, schedule, layout, baselines</td></tr><tr><td>Read only</td><td>5</td><td>View</td><td>View layouts and reports</td></tr>`,
    ) + note,
    preferences: `<div class="cp-vd-fields">
      <label><span>${esc(tr("Currency", "ارز"))}</span><input value="USD" readonly></label>
      <label><span>${esc(tr("Date format", "قالب تاریخ"))}</span><input value="DD-MMM-YYYY" readonly></label>
      <label><span>${esc(tr("Week starts on", "شروع هفته"))}</span><input value="${esc(tr("Saturday", "شنبه"))}" readonly></label>
      <label><span>${esc(tr("Language", "زبان"))}</span><input value="${esc(tr("English", "فارسی"))}" readonly></label>
      <label><span>${esc(tr("Data date", "تاریخ داده"))}</span><input value="03-Dec-2026" readonly></label>
      <label><span>${esc(tr("Timescale default", "مقیاس پیش‌فرض"))}</span><input value="${esc(tr("Month / Week", "ماه / هفته"))}" readonly></label>
    </div>${note}`,
    currencies: table(
      [tr("Code", "کد"), tr("Name", "نام"), tr("Symbol", "نماد"), tr("Rate to USD", "نرخ به دلار")],
      `<tr><td>USD</td><td>US dollar</td><td>$</td><td>1.0000</td></tr><tr><td>EUR</td><td>Euro</td><td>€</td><td>0.9200</td></tr><tr><td>IRR</td><td>Iranian rial</td><td>﷼</td><td>0.000024</td></tr>`,
    ) + note,
    codes: table(
      [tr("Code", "کد"), tr("Description", "توضیح"), tr("Scope", "دامنه"), tr("Values", "مقادیر")],
      `<tr><td>PHASE</td><td>Project phase</td><td>Activity</td><td>5</td></tr><tr><td>DISC</td><td>Discipline</td><td>Activity</td><td>6</td></tr><tr><td>CUBI-DEMO</td><td>Demo project tag</td><td>Project</td><td>1</td></tr>`,
    ) + note,
    udfs: table(
      [tr("Name", "نام"), tr("Subject", "موضوع"), tr("Data type", "نوع داده"), tr("Values", "مقادیر")],
      `<tr><td>Cost centre</td><td>Activity</td><td>Text</td><td>Definitions only</td></tr><tr><td>Shutdown window</td><td>Activity</td><td>Date</td><td>No value</td></tr><tr><td>Supplier rating</td><td>Resource</td><td>Integer</td><td>1 – 5</td></tr>`,
    ) + note,
  };
  return `<section class="cp-vd-windowbody"><header class="cp-vd-winhead"><h2>${esc(tr("Administration", "مدیریت"))}</h2></header>
    <div class="cp-vd-admin">
      <nav>${ADMIN_SECTIONS.map(([id, en, fa]) => `<button type="button" data-vd-admin="${id}" class="${section === id ? "is-active" : ""}" aria-pressed="${section === id}">${esc(t(state.locale, en, fa))}</button>`).join("")}</nav>
      <div>${contents[section]}</div>
    </div></section>`;
}

function renderTableWindow(state: DemoState, title: Label, headers: string[], rows: Row[], actions: string[] = []): string {
  return `<section class="cp-vd-windowbody">
    <header class="cp-vd-winhead"><h2>${esc(label(title, state.locale))}</h2><div class="cp-vd-winactions">${actions.map((action) => `<button type="button" class="cp-vd-btn" data-vd-dialog="${esc(action)}">${esc(t(state.locale, action, { "new-project": "New project", "assign-resources": "Assign resources", "assign-roles": "Assign roles", "schedule": "Schedule", "level": "Level resources", "import": "Import", "export": "Export", "print": "Print preview", "baselines": "Baselines", "report-wizard": "Report wizard" }[action] ?? action))}</button>`).join("")}</div></header>
    <div class="cp-vd-tablewrap"><table class="cp-vd-table"><thead><tr>${headers.map((header) => `<th>${esc(header)}</th>`).join("")}</tr></thead><tbody>${rows.map((row) => `<tr>${headers.map((header) => `<td>${esc(row[header] ?? "")}</td>`).join("")}</tr>`).join("")}</tbody></table></div>
  </section>`;
}

function renderLiveUnavailableWindow(state: DemoState): string {
  const title = WINDOWS.find((item) => item.id === state.window);
  const name = title ? label({ en: title.en, fa: title.fa }, state.locale) : "";
  return `<section class="cp-vd-windowbody cp-vd-live-unavailable">
    <header class="cp-vd-winhead"><h2>${esc(name)}</h2></header>
    <div class="cp-vd-empty">
      <strong>${esc(t(state.locale, "This view is not connected to live project data yet.", "این نما هنوز به داده‌های واقعی پروژه متصل نشده است."))}</strong>
      <p>${esc(t(state.locale, "No sample records are shown here. The live project, activities, WBS and relationships remain available in the connected views.", "در این بخش دادهٔ ساختگی نمایش داده نمی‌شود. پروژه، فعالیت‌ها، WBS و روابط واقعی در نماهای متصل در دسترس هستند."))}</p>
    </div>
  </section>`;
}

function renderWindow(state: DemoState): string {
  if (state.project && !["projects", "wbs", "activities"].includes(state.window)) {
    return renderLiveUnavailableWindow(state);
  }
  switch (state.window) {
    case "projects":
      return state.project
        ? renderTableWindow(state, { en: "Projects", fa: "پروژه‌ها" }, ["Project ID", "Project name", "Revision", "Status", "Start", "Finish", "Activities"], [
            { "Project ID": state.project.id, "Project name": state.project.name, Revision: state.project.revision, Status: "Open", Start: state.project.projectStart ? fmtDate(state.project.projectStart) : "—", Finish: state.project.projectFinish ? fmtDate(state.project.projectFinish) : "—", Activities: state.project.activities.length },
          ])
        : renderTableWindow(state, { en: "Projects", fa: "پروژه‌ها" }, ["Project ID", "Project name", "Status", "Start", "Finish", "Data date", "Activities"], [
            { "Project ID": "CUBI-DEMO-001", "Project name": "Riverside Pump Station Upgrade", Status: "Active", Start: "02-Nov-26", Finish: "28-May-27", "Data date": "03-Dec-26", Activities: 20 },
            { "Project ID": "CUBI-DEMO-002", "Project name": "Intake Screen Replacement", Status: "Planning", Start: "01-Feb-27", Finish: "30-Sep-27", "Data date": "—", Activities: 12 },
          ], ["new-project", "baselines"]);
    case "wbs":
      return `<section class="cp-vd-windowbody"><header class="cp-vd-winhead"><h2>${esc(t(state.locale, "Work Breakdown Structure", "ساختار شکست کار"))}</h2></header>
        <div class="cp-vd-tablewrap"><table class="cp-vd-table"><thead><tr><th>WBS Code</th><th>WBS Name</th><th class="is-numeric">Total Activities</th></tr></thead><tbody>
        ${wbsNodesFor(state).map((node) => `<tr class="${node.level === 0 ? "is-summary-row" : ""}"><td>${esc(node.code)}</td><td style="padding-inline-start:${8 + node.level * 22}px">${node.level < 2 ? "▾ " : "• "}${esc(node.name)}</td><td class="is-numeric">${node.total}</td></tr>`).join("")}
        </tbody></table></div></section>`;
    case "activities":
      return `<section class="cp-vd-windowbody cp-vd-activities">
        <header class="cp-vd-winhead"><h2>${esc(t(state.locale, "Activities", "فعالیت‌ها"))}</h2>
          <span class="cp-vd-chip">${esc(t(state.locale, "Classic Schedule Layout", "چیدمان کلاسیک زمان‌بندی"))}</span>
        </header>
        ${renderGanttTools(state)}
        <div class="cp-vd-split">
          <div class="cp-vd-pane">${renderActivityTable(state, state.columns)}</div>
          <div class="cp-vd-pane">${renderGantt(state)}</div>
        </div>
        ${renderDetails(state)}
      </section>`;
    case "assignments":
      return renderTableWindow(state, { en: "Resource Assignments", fa: "تخصیص منابع" }, ["Activity ID", "Activity name", "Resource", "Budgeted units", "Actual units", "Remaining units", "Cost"], ACTIVITIES.filter((row) => row.res !== "—").slice(0, 12).map((row) => ({ "Activity ID": row.id, "Activity name": row.name, Resource: row.res, "Budgeted units": row.budgetUnits, "Actual units": row.actualUnits, "Remaining units": row.remainingUnits, Cost: numericDisplay(row.budgetCost) })), ["assign-resources", "assign-roles"]);
    case "resources":
      return `<section class="cp-vd-windowbody"><header class="cp-vd-winhead"><h2>${esc(t(state.locale, "Resources", "منابع"))}</h2><div class="cp-vd-winactions"><button type="button" class="cp-vd-btn" data-vd-dialog="assign-resources">${esc(t(state.locale, "Assign resources", "تخصیص منابع"))}</button></div></header>
        <div class="cp-vd-tablewrap"><table class="cp-vd-table"><thead><tr><th>Resource ID</th><th>Resource name</th><th>Type</th><th class="is-numeric">Budgeted units</th><th class="is-numeric">Cost</th><th>Histogram</th></tr></thead><tbody>
        ${RESOURCES.map((row) => `<tr><td>${esc(row.id)}</td><td>${esc(row.name)}</td><td>${esc(row.type)}</td><td class="is-numeric">${row.units}</td><td class="is-numeric">${row.cost.toLocaleString("en-US")}</td><td><span class="cp-vd-minibar" style="width:${Math.min(100, row.cost / 2500)}%"></span></td></tr>`).join("")}
        </tbody></table></div></section>`;
    case "calendars":
      return renderCalendars(state);
    case "reports":
      return `<section class="cp-vd-windowbody"><header class="cp-vd-winhead"><h2>${esc(t(state.locale, "Reports", "گزارش‌ها"))}</h2><div class="cp-vd-winactions"><button type="button" class="cp-vd-btn" data-vd-dialog="report-wizard">${esc(t(state.locale, "Report wizard", "جادوگر گزارش"))}</button></div></header>
        <div class="cp-vd-report-list">${["Schedule report", "Cost report", "Resource report", "Critical path report"].map((name) => `<div class="cp-vd-report"><span>${esc(name)}</span><button type="button" class="cp-vd-btn" data-vd-dialog="print">${esc(t(state.locale, "Preview", "پیش‌نمایش"))}</button></div>`).join("")}</div></section>`;
    case "tracking":
      return renderTableWindow(state, { en: "Tracking", fa: "پیگیری" }, ["Activity ID", "Activity name", "Status", "% complete", "Actual start", "Actual finish", "Remaining duration"], ACTIVITIES.slice(0, 10).map((row) => ({ "Activity ID": row.id, "Activity name": row.name, Status: row.status, "% complete": `${row.pct}%`, "Actual start": row.pct ? fmtDate(row.start) : "—", "Actual finish": (row.pct ?? -1) >= 100 ? fmtDate(row.finish) : "—", "Remaining duration": numericDisplay(row.rd, " d") })));
    case "documents":
      return renderTableWindow(state, { en: "Documents", fa: "اسناد" }, ["Document", "Title", "Revision", "Status", "Owner"], [
        { Document: "ITP-Pump-01", Title: "Inspection and test plan", Revision: "B", Status: "Approved", Owner: "QA/QC" },
        { Document: "DS-Civil-04", Title: "Foundation design statement", Revision: "C", Status: "For review", Owner: "Engineering" },
        { Document: "PO-2026-118", Title: "Pump package purchase order", Revision: "A", Status: "Issued", Owner: "Procurement" },
      ], ["export"]);
    case "expenses":
      return renderTableWindow(state, { en: "Expenses", fa: "هزینه‌ها" }, ["Expense", "Activity ID", "Budgeted cost", "Actual cost", "Remaining cost"], ACTIVITIES.filter((row) => (row.budgetCost ?? 0) > 0).slice(0, 10).map((row) => ({ Expense: row.res, "Activity ID": row.id, "Budgeted cost": numericDisplay(row.budgetCost), "Actual cost": numericDisplay(row.actualCost), "Remaining cost": numericDisplay(row.remainingCost) })));
    case "thresholds":
      return renderTableWindow(state, { en: "Thresholds", fa: "آستانه‌ها" }, ["Threshold", "Type", "Warning", "Critical", "Status"], [
        { Threshold: "Total float", Type: "Activity", Warning: "< 5 d", Critical: "< 0 d", Status: "2 activities" },
        { Threshold: "Cost variance", Type: "Project", Warning: "> 5%", Critical: "> 10%", Status: "Within" },
        { Threshold: "Schedule variance", Type: "Project", Warning: "> 3 d", Critical: "> 7 d", Status: "1 activity" },
      ]);
    case "issues":
      return renderTableWindow(state, { en: "Issues", fa: "مسائل" }, ["Issue", "Priority", "Owner", "Due", "Status"], [
        { Issue: "Pump delivery window", Priority: "High", Owner: "Procurement", Due: "20-Feb-27", Status: "Open" },
        { Issue: "Site access permit", Priority: "Medium", Owner: "Construction", Due: "15-Jan-27", Status: "Open" },
      ]);
    case "risks":
      return renderTableWindow(state, { en: "Risks", fa: "ریسک‌ها" }, ["Risk", "Probability", "Impact", "Score", "Response"], [
        { Risk: "Weather delay", Probability: "Medium", Impact: "High", Score: 12, Response: "Mitigate" },
        { Risk: "Long-lead valve supply", Probability: "Low", Impact: "High", Score: 8, Response: "Transfer" },
        { Risk: "Commissioning resource", Probability: "Medium", Impact: "Medium", Score: 6, Response: "Accept" },
      ]);
    case "administration":
      return renderAdministration(state);
    case "network":
      return renderNetwork(state);
    case "trace":
      return renderTrace(state);
    case "timeline":
      return renderTimeline(state);
    case "activity-profile":
      return renderProfile(state, "activities");
    case "resource-profile":
      return renderProfile(state, "resources");
    case "activity-sheet":
      return renderSheet(state, "activity");
    case "resource-sheet":
      return renderSheet(state, "resource");
    default:
      return "";
  }
}

const NETWORK_NODES: Array<{ id: string; col: number; row: number }> = [
  { id: "A1010", col: 0, row: 0 }, { id: "A1020", col: 0, row: 1 }, { id: "A1210", col: 0, row: 2 },
  { id: "A1110", col: 1, row: 0 }, { id: "A1120", col: 1, row: 1 }, { id: "A1220", col: 1, row: 2 },
  { id: "A1130", col: 2, row: 0 }, { id: "A1310", col: 2, row: 1 }, { id: "A1320", col: 2, row: 2 },
  { id: "A1330", col: 3, row: 0 }, { id: "A1340", col: 3, row: 1 }, { id: "A1500", col: 3, row: 2 },
];
// Finish-to-start relationships exactly as they exist in the demo successor data.
const NETWORK_LINKS: Array<[string, string]> = [
  ["A1010", "A1110"], ["A1020", "A1110"], ["A1110", "A1120"], ["A1110", "A1130"], ["A1120", "A1130"],
  ["A1210", "A1220"], ["A1130", "A1320"], ["A1310", "A1320"], ["A1320", "A1330"], ["A1330", "A1340"],
  ["A1340", "A1500"],
];

const NETWORK_DEFS = `<defs>
  <marker id="cp-vd-net-arrow" markerWidth="5" markerHeight="5" refX="4.5" refY="2.5" orient="auto"><path d="M0,0 L5,2.5 L0,5 z" fill="#44536a"></path></marker>
  <marker id="cp-vd-net-arrow-critical" markerWidth="5" markerHeight="5" refX="4.5" refY="2.5" orient="auto"><path d="M0,0 L5,2.5 L0,5 z" fill="#c0392b"></path></marker>
</defs>`;

function renderNetwork(state: DemoState): string {
  const nodes = NETWORK_NODES.map((node) => {
    const row = ACTIVITIES.find((item) => item.id === node.id) ?? ACTIVITIES[0];
    return `<div class="cp-vd-node ${row.critical ? "is-critical" : ""}" data-vd-node="${esc(node.id)}" style="inset-inline-start:${3 + node.col * 23.5}%;top:${8 + node.row * 28}%"><span>${esc(row.id)}</span><strong>${esc(row.name)}</strong><em>${row.od}d · ${row.pct}%</em></div>`;
  }).join("");
  return `<section class="cp-vd-windowbody"><header class="cp-vd-winhead"><h2>${esc(t(state.locale, "Activity Network", "شبکه فعالیت"))}</h2><div class="cp-vd-winactions"><span class="cp-vd-chip">${esc(t(state.locale, "12 boxes · 11 links", "۱۲ جعبه · ۱۱ رابطه"))}</span><button type="button" class="cp-vd-btn" data-vd-dialog="network-options">${esc(t(state.locale, "Layout options", "تنظیمات چیدمان"))}</button></div></header>
    <div class="cp-vd-network" data-vd-network>
      ${nodes}
      <svg class="cp-vd-node-links" data-vd-netlinks aria-hidden="true">${NETWORK_DEFS}</svg>
    </div></section>`;
}

function renderTimeline(state: DemoState): string {
  const fa = state.locale.startsWith("fa");
  const axis = buildAxis("month", state.locale);
  const raster = axis.rows[0].map((band) => `<span style="inset-inline-start:${band.left}%;width:${band.width}%">${esc(band.label)}</span>`).join("");
  const lanes = [
    { en: "Project Management", fa: "مدیریت پروژه", start: "2026-11-02", finish: "2027-05-28" },
    { en: "Engineering", fa: "مهندسی", start: "2026-11-02", finish: "2026-12-21" },
    { en: "Procurement", fa: "تدارکات", start: "2026-11-23", finish: "2027-02-26" },
    { en: "Construction", fa: "ساخت", start: "2027-01-04", finish: "2027-04-30" },
    { en: "Testing & Commissioning", fa: "تست و راه‌اندازی", start: "2027-05-03", finish: "2027-05-28" },
  ];
  const milestones = [
    { id: "A1010", en: "Kick-off", fa: "آغاز", date: "2026-11-02", critical: false, low: false, end: false },
    { id: "A1130", en: "Design review", fa: "بازبینی طراحی", date: "2026-12-21", critical: true, low: true, end: false },
    { id: "A1230", en: "Pump delivery", fa: "تحویل پمپ", date: "2027-02-26", critical: true, low: false, end: false },
    { id: "A1400", en: "Testing", fa: "تست", date: "2027-05-03", critical: false, low: true, end: false },
    { id: "A1500", en: "Handover", fa: "تحویل نهایی", date: "2027-05-28", critical: false, low: false, end: true },
  ];
  const laneRows = lanes.map((lane, index) => {
    const position = demoBarPosition(lane.start, lane.finish);
    return `<div class="cp-vd-timeline-lane${index % 2 ? " is-alt" : ""}"><span class="cp-vd-timeline-name">${esc(t(state.locale, lane.en, lane.fa))}</span><div class="cp-vd-timeline-track"><span class="cp-vd-timeline-bar" style="inset-inline-start:${position.left};width:${position.width}">${esc(t(state.locale, lane.en, lane.fa))}</span></div></div>`;
  }).join("");
  const marks = milestones.map((mark) => {
    const position = demoBarPosition(mark.date, mark.date);
    return `<span class="cp-vd-timeline-mark${mark.low ? " is-low" : ""}${mark.critical ? " is-critical" : ""}${mark.end ? " is-end" : ""}" style="inset-inline-start:${Math.min(99.4, Math.max(0.6, parseFloat(position.left)))}%" title="${esc(mark.id)} · ${fmtDate(mark.date)}"><i></i><b>${esc(t(state.locale, mark.en, mark.fa))}</b><em><bdi dir="ltr">${esc(fmtDate(mark.date))}</bdi></em></span>`;
  }).join("");
  const dataDate = (day("2026-12-03") - day(PROJECT_START)) / PROJECT_DAYS;
  return `<section class="cp-vd-windowbody"><header class="cp-vd-winhead"><h2>${esc(t(state.locale, "Timeline", "خط زمانی"))}</h2><div class="cp-vd-winactions"><span class="cp-vd-chip">${esc(t(state.locale, "Summary bars · milestones", "میله‌های خلاصه · نقاط عطف"))}</span><button type="button" class="cp-vd-btn" data-vd-dialog="timeline-options">${esc(t(state.locale, "Timeline options", "تنظیمات خط زمانی"))}</button></div></header>
    <div class="cp-vd-timeline">
      <div class="cp-vd-timeline-head"><span></span><div class="cp-vd-timeline-axis">${raster}</div></div>
      <div class="cp-vd-timeline-body">
        <span class="cp-vd-timeline-datadate" style="inset-inline-start:calc(170px + (100% - 170px) * ${dataDate.toFixed(4)})" title="${esc(t(state.locale, "Data date 03-Dec-2026", "تاریخ داده ۱۲ آذر ۱۴۰۵"))}"><b>${esc(t(state.locale, "Data date", "تاریخ داده"))}</b></span>
        ${laneRows}
      </div>
      <div class="cp-vd-timeline-head is-markers"><span>${esc(t(state.locale, "Milestones", "نقاط عطف"))}</span><div class="cp-vd-timeline-marks">${marks}</div></div>
    </div></section>`;
}

function renderTrace(state: DemoState): string {
  const row = ACTIVITIES.find((item) => item.id === state.activityId) ?? ACTIVITIES[0];
  const preds = row.pred === "—" ? [] : row.pred.split(", ");
  return `<section class="cp-vd-windowbody"><header class="cp-vd-winhead"><h2>${esc(t(state.locale, "Trace Logic", "ردیابی منطق"))}</h2><span class="cp-vd-chip">${esc(row.id)}</span></header>
    <div class="cp-vd-trace" data-vd-trace>
      <svg class="cp-vd-trace-links" data-vd-tracelinks aria-hidden="true">${NETWORK_DEFS}</svg>
      <div class="cp-vd-trace-col"><h4>${esc(t(state.locale, "Predecessors", "پیش‌نیازها"))}</h4>${preds.map((id) => { const p = ACTIVITIES.find((item) => item.id === id.replace(/[^A-Z0-9-]/gi, "")) ?? ACTIVITIES[1]; return `<div class="cp-vd-tnode" data-trace-pred="${esc(p.id)}"><span>${esc(p.id)}</span>${esc(p.name)}<em><bdi dir="ltr">${esc(fmtDate(p.start))} → ${esc(fmtDate(p.finish))}</bdi></em></div>`; }).join("") || `<div class="cp-vd-tnode is-muted">—</div>`}</div>
      <div class="cp-vd-trace-col"><h4>${esc(t(state.locale, "Selected activity", "فعالیت انتخاب‌شده"))}</h4><div class="cp-vd-tnode is-selected" data-trace-selected="${esc(row.id)}"><span>${esc(row.id)}</span>${esc(row.name)}<em><bdi dir="ltr">${esc(fmtDate(row.start))} → ${esc(fmtDate(row.finish))}</bdi></em></div></div>
      <div class="cp-vd-trace-col"><h4>${esc(t(state.locale, "Successors", "جانشین‌ها"))}</h4>${(row.succ === "—" ? [] : row.succ.split(", ")).map((id) => { const s = ACTIVITIES.find((item) => item.id === id.replace(/[^A-Z0-9-]/gi, "")) ?? ACTIVITIES[2]; return `<div class="cp-vd-tnode" data-trace-succ="${esc(s.id)}"><span>${esc(s.id)}</span>${esc(s.name)}<em><bdi dir="ltr">${esc(fmtDate(s.start))} → ${esc(fmtDate(s.finish))}</bdi></em></div>`; }).join("") || `<div class="cp-vd-tnode is-muted">—</div>`}</div>
      <p class="cp-vd-trace-note">${esc(t(state.locale, "One level of predecessors and successors around the selected activity. Relationship lines follow the demo finish-to-start logic.", "یک سطح پیش‌نیاز و جانشین پیرامون فعالیت انتخاب‌شده. خطوط رابطه از منطق پایان‌به‌شروع دادهٔ نمایشی پیروی می‌کنند."))}</p>
    </div></section>`;
}


// One column per calendar week of the demo project, keyed by the same ISO week
// numbers the timescale uses so profile and spreadsheet line up with the Gantt.
const PROJECT_WEEKS: string[] = (() => {
  const total = Math.ceil((day(PROJECT_FINISH) - day(PROJECT_START) + 1) / 7);
  return Array.from({ length: total }, (_, index) => `W${String(isoWeek(day(PROJECT_START) + index * 7)).padStart(2, "0")}`);
})();

function weekSpan(start: string, finish: string): [number, number] {
  const last = PROJECT_WEEKS.length - 1;
  const first = Math.max(0, Math.min(last, Math.floor((day(start) - day(PROJECT_START)) / 7)));
  const end = Math.max(first, Math.min(last, Math.floor((day(finish) - day(PROJECT_START)) / 7)));
  return [first, end];
}

function renderProfile(state: DemoState, kind: "activities" | "resources"): string {
  const count = PROJECT_WEEKS.length;
  const bars = Array.from({ length: count }, (_, index) => {
    const ramp = Math.min(1, (index + 1) / 4);
    const tail = Math.min(1, (count - index) / 4);
    const wave = 0.8 + 0.2 * Math.sin(index * 0.75);
    return Math.max(8, Math.round((kind === "activities" ? 64 : 58) * ramp * tail * wave));
  });
  return `<section class="cp-vd-windowbody"><header class="cp-vd-winhead"><h2>${esc(t(state.locale, kind === "activities" ? "Activity Usage Profile" : "Resource Usage Profile", kind === "activities" ? "پروفایل مصرف فعالیت" : "پروفایل مصرف منبع"))}</h2><span class="cp-vd-chip">${esc(t(state.locale, "Hours per week · 30 weeks", "ساعت در هفته · ۳۰ هفته"))}</span></header>
    <div class="cp-vd-profile">
      <div class="cp-vd-profile-axis"><span>80</span><span>60</span><span>40</span><span>20</span><span>0</span></div>
      <div class="cp-vd-profile-plot">
        <div class="cp-vd-profile-bars">${bars.map((height) => `<div class="cp-vd-profile-bar" style="height:${height}%"></div>`).join("")}</div>
        <div class="cp-vd-profile-labels">${PROJECT_WEEKS.map((week) => `<span>${week}</span>`).join("")}</div>
      </div>
    </div>
    <div class="cp-vd-tablewrap"><table class="cp-vd-table"><thead><tr><th>${esc(t(state.locale, "Week", "هفته"))}</th><th class="is-numeric">${esc(t(state.locale, "Planned", "برنامه‌ای"))}</th><th class="is-numeric">${esc(t(state.locale, "Actual", "واقعی"))}</th><th class="is-numeric">${esc(t(state.locale, "Remaining", "باقی‌مانده"))}</th></tr></thead><tbody>${bars.map((height, index) => `<tr><td>${PROJECT_WEEKS[index]}</td><td class="is-numeric">${height * 2}</td><td class="is-numeric">${Math.round(height * 1.2)}</td><td class="is-numeric">${height}</td></tr>`).join("")}</tbody></table></div></section>`;
}

function renderSheet(state: DemoState, kind: "activity" | "resource"): string {
  const rows = kind === "activity"
    ? ACTIVITIES.map((row) => ({ label: `${row.id} ${row.name}`, units: row.budgetUnits, start: row.start, finish: row.finish }))
    : RESOURCES.map((resource) => {
      const assigned = ACTIVITIES.filter((row) => row.res === resource.name);
      const start = assigned.length ? assigned.map((row) => row.start).sort()[0] : PROJECT_START;
      const finish = assigned.length ? assigned.map((row) => row.finish).sort().slice(-1)[0] : PROJECT_FINISH;
      return { label: `${resource.id} ${resource.name}`, units: resource.units, start, finish };
    });
  return `<section class="cp-vd-windowbody"><header class="cp-vd-winhead"><h2>${esc(t(state.locale, kind === "activity" ? "Activity Usage Spreadsheet" : "Resource Usage Spreadsheet", kind === "activity" ? "صفحهٔ مصرف فعالیت" : "صفحهٔ مصرف منبع"))}</h2><span class="cp-vd-chip">${esc(t(state.locale, "Budgeted units per week", "واحد بودجه در هفته"))}</span></header>
    <div class="cp-vd-tablewrap"><table class="cp-vd-table cp-vd-sheet"><thead><tr><th>${esc(t(state.locale, kind === "activity" ? "Activity" : "Resource", kind === "activity" ? "فعالیت" : "منبع"))}</th>${PROJECT_WEEKS.map((week) => `<th class="is-numeric">${week}</th>`).join("")}<th class="is-numeric">${esc(t(state.locale, "Total", "جمع"))}</th></tr></thead><tbody>
    ${rows.map((row) => {
      const [first, end] = weekSpan(row.start, row.finish);
      const perWeek = (row.units ?? 0) / (end - first + 1);
      return `<tr><td>${esc(row.label)}</td>${PROJECT_WEEKS.map((_, week) => `<td class="is-numeric">${week >= first && week <= end && (row.units ?? 0) ? perWeek.toFixed(1) : ""}</td>`).join("")}<td class="is-numeric">${(row.units ?? 0).toLocaleString("en-US")}</td></tr>`;
    }).join("")}
    </tbody></table></div></section>`;
}

type MenuAction = { window?: DemoWindowId; dialog?: string; command?: string; reason?: Label };

const MENUS: Array<{ id: string; label: Label; items: Array<{ label: Label; shortcut?: string; action?: MenuAction; checked?: string; children?: Array<{ label: Label; action?: MenuAction; checked?: string }> }> }> = [
  { id: "workspace", label: { en: "Workspace", fa: "محیط کار" }, items: [
    { label: { en: "New project…", fa: "پروژهٔ جدید…" }, action: { dialog: "new-project" } },
    { label: { en: "Open project…", fa: "بازکردن پروژه…" }, action: { window: "projects" } },
    { label: { en: "Project properties…", fa: "مشخصات پروژه…" }, action: { dialog: "project-properties" } },
    { label: { en: "Import / Export", fa: "ورود / خروجی" }, children: [
      { label: { en: "Import…", fa: "ورود…" }, action: { dialog: "import" } },
      { label: { en: "Export…", fa: "خروجی…" }, action: { dialog: "export" } },
    ] },
    { label: { en: "Print preview", fa: "پیش‌نمایش چاپ" }, shortcut: "Ctrl+P", action: { dialog: "print" } },
    { label: { en: "Close window", fa: "بستن پنجره" }, shortcut: "Ctrl+W", action: { command: "close-window" } },
  ] },
  { id: "edit", label: { en: "Edit", fa: "ویرایش" }, items: [
    { label: { en: "Undo", fa: "بازگردانی" }, shortcut: "Ctrl+Z", action: { command: "undo" } },
    { label: { en: "Redo", fa: "تکرار" }, shortcut: "Ctrl+Y", action: { command: "redo" } },
    { label: { en: "Cut", fa: "برش" }, shortcut: "Ctrl+X", action: { command: "noop" } },
    { label: { en: "Copy", fa: "رونوشت" }, shortcut: "Ctrl+C", action: { command: "noop" } },
    { label: { en: "Paste", fa: "چسباندن" }, shortcut: "Ctrl+V", action: { command: "noop" } },
    { label: { en: "Find…", fa: "یافتن…" }, shortcut: "Ctrl+F", action: { dialog: "find" } },
    { label: { en: "Find and Replace…", fa: "یافتن و جایگزینی…" }, action: { dialog: "find-replace" } },
    { label: { en: "Renumber Activity IDs…", fa: "شماره‌گذاری دوبارهٔ شناسه‌ها…" }, action: { dialog: "renumber" } },
  ] },
  { id: "view", label: { en: "View", fa: "نما" }, items: [
    { label: { en: "Toolbars", fa: "نوارهای ابزار" }, children: [
      { label: { en: "Standard", fa: "استاندارد" }, action: { command: "toolbar:standard" } },
      { label: { en: "Project", fa: "پروژه" }, action: { command: "toolbar:project" } },
      { label: { en: "Edit", fa: "ویرایش" }, action: { command: "toolbar:edit" } },
      { label: { en: "View", fa: "نما" }, action: { command: "toolbar:view" } },
      { label: { en: "Layout", fa: "چیدمان" }, action: { command: "toolbar:layout" } },
      { label: { en: "Reports", fa: "گزارش‌ها" }, action: { command: "toolbar:reports" } },
    ] },
    { label: { en: "Columns…", fa: "ستون‌ها…" }, action: { dialog: "columns" } },
    { label: { en: "Layouts", fa: "چیدمان‌ها" }, children: [
      { label: { en: "Activity Network", fa: "شبکه فعالیت" }, action: { window: "network" } },
      { label: { en: "Trace Logic", fa: "ردیابی منطق" }, action: { window: "trace" } },
      { label: { en: "Timeline", fa: "خط زمانی" }, action: { window: "timeline" } },
      { label: { en: "Activity Usage Profile", fa: "پروفایل مصرف فعالیت" }, action: { window: "activity-profile" } },
      { label: { en: "Resource Usage Profile", fa: "پروفایل مصرف منبع" }, action: { window: "resource-profile" } },
      { label: { en: "Activity Usage Spreadsheet", fa: "صفحهٔ مصرف فعالیت" }, action: { window: "activity-sheet" } },
      { label: { en: "Resource Usage Spreadsheet", fa: "صفحهٔ مصرف منبع" }, action: { window: "resource-sheet" } },
      { label: { en: "Resource Assignments", fa: "تخصیص منابع" }, action: { window: "assignments" } },
      { label: { en: "Tracking", fa: "پیگیری" }, action: { window: "tracking" } },
      { label: { en: "Documents", fa: "اسناد" }, action: { window: "documents" } },
      { label: { en: "Expenses", fa: "هزینه‌ها" }, action: { window: "expenses" } },
      { label: { en: "Thresholds", fa: "آستانه‌ها" }, action: { window: "thresholds" } },
      { label: { en: "Issues", fa: "مسائل" }, action: { window: "issues" } },
      { label: { en: "Risks", fa: "ریسک‌ها" }, action: { window: "risks" } },
      { label: { en: "Calendars", fa: "تقویم‌ها" }, action: { window: "calendars" } },
      { label: { en: "Reports", fa: "گزارش‌ها" }, action: { window: "reports" } },
    ] },
    { label: { en: "Filters…", fa: "فیلترها…" }, action: { dialog: "filters" } },
    { label: { en: "Group and Sort…", fa: "گروه‌بندی و ترتیب…" }, action: { dialog: "group-sort" } },
    { label: { en: "Timescale…", fa: "مقیاس زمانی…" }, action: { dialog: "timescale" } },
    { label: { en: "Bars…", fa: "میله‌ها…" }, action: { dialog: "bars" } },
    { label: { en: "Bar Chart Options…", fa: "تنظیمات نمودار میله‌ای…" }, action: { dialog: "bar-options" } },
    { label: { en: "Table Font and Row…", fa: "قلم و ردیف جدول…" }, action: { dialog: "font-row" } },
    { label: { en: "Layout Manager…", fa: "مدیر چیدمان…" }, action: { dialog: "layout-manager" } },
    { label: { en: "Customize Activity Details…", fa: "سفارشی‌سازی جزئیات…" }, action: { dialog: "customize-details" } },
  ] },
  { id: "project", label: { en: "Project", fa: "پروژه" }, items: [
    { label: { en: "Activities", fa: "فعالیت‌ها" }, children: [
      { label: { en: "Add activity", fa: "افزودن فعالیت" }, action: { dialog: "add-activity" } },
      { label: { en: "Assign resources…", fa: "تخصیص منابع…" }, action: { dialog: "assign-resources" } },
      { label: { en: "Assign roles…", fa: "تخصیص نقش…" }, action: { dialog: "assign-roles" } },
      { label: { en: "Assign predecessors…", fa: "تخصیص پیش‌نیاز…" }, action: { dialog: "assign-predecessors" } },
      { label: { en: "Assign successors…", fa: "تخصیص جانشین…" }, action: { dialog: "assign-successors" } },
    ] },
    { label: { en: "WBS…", fa: "WBS…" }, action: { window: "wbs" } },
    { label: { en: "Baselines…", fa: "خطوط مبنا…" }, action: { dialog: "baselines" } },
    { label: { en: "Schedule…", fa: "زمان‌بندی…" }, shortcut: "F9", action: { dialog: "schedule" } },
    { label: { en: "Level resources…", fa: "تسطیح منابع…" }, action: { dialog: "level" } },
  ] },
  { id: "organization", label: { en: "Organization", fa: "سازمان" }, items: [
    { label: { en: "Resources", fa: "منابع" }, action: { window: "resources" } },
    { label: { en: "Resource assignments", fa: "تخصیص منابع" }, action: { window: "assignments" } },
    { label: { en: "Calendars", fa: "تقویم‌ها" }, action: { window: "calendars" } },
    { label: { en: "Roles", fa: "نقش‌ها" }, action: { dialog: "roles" } },
    { label: { en: "Dictionaries", fa: "واژه‌نامه‌ها" }, children: [
      { label: { en: "Activity codes", fa: "کدهای فعالیت" }, action: { dialog: "dictionaries" } },
      { label: { en: "UDFs", fa: "فیلدهای سفارشی" }, action: { dialog: "dictionaries" } },
    ] },
  ] },
  { id: "tools", label: { en: "Tools", fa: "ابزارها" }, items: [
    { label: { en: "Schedule", fa: "زمان‌بندی" }, shortcut: "F9", action: { dialog: "schedule" } },
    { label: { en: "Level resources…", fa: "تسطیح منابع…" }, action: { dialog: "level" } },
    { label: { en: "Reports", fa: "گزارش‌ها" }, children: [
      { label: { en: "Report wizard…", fa: "جادوگر گزارش…" }, action: { dialog: "report-wizard" } },
      { label: { en: "Report preview", fa: "پیش‌نمایش گزارش" }, action: { window: "reports" } },
    ] },
    { label: { en: "Preferences…", fa: "تنظیمات…" }, action: { dialog: "preferences" } },
  ] },
  { id: "administration", label: { en: "Administration", fa: "مدیریت" }, items: [
    { label: { en: "Users…", fa: "کاربران…" }, action: { window: "administration" } },
    { label: { en: "Security profiles…", fa: "پروفایل امنیتی…" }, action: { dialog: "security-profiles" } },
    { label: { en: "Administration preferences…", fa: "تنظیمات مدیریت…" }, action: { dialog: "admin-preferences" } },
    { label: { en: "Dictionaries…", fa: "واژه‌نامه‌ها…" }, action: { dialog: "dictionaries" } },
  ] },
  { id: "help", label: { en: "Help", fa: "راهنما" }, items: [
    { label: { en: "Keyboard shortcuts", fa: "کلیدهای میانبر" }, shortcut: "F1", action: { dialog: "shortcuts" } },
    { label: { en: "Activity Network", fa: "شبکه فعالیت" }, action: { window: "network" } },
    { label: { en: "Trace Logic", fa: "ردیابی منطق" }, action: { window: "trace" } },
    { label: { en: "About CUBI Workspace", fa: "دربارهٔ محیط کار CUBI" }, action: { dialog: "about" } },
  ] },
];

const TOOLBARS: Array<{ id: string; label: Label; items: Array<{ icon: string; label: Label; action: MenuAction }> }> = [
  { id: "standard", label: { en: "Standard", fa: "استاندارد" }, items: [
    { icon: "file", label: { en: "New", fa: "جدید" }, action: { dialog: "new-project" } },
    { icon: "book", label: { en: "Open", fa: "بازکردن" }, action: { window: "projects" } },
    { icon: "print", label: { en: "Print", fa: "چاپ" }, action: { dialog: "print" } },
  ] },
  { id: "project", label: { en: "Project", fa: "پروژه" }, items: [
    { icon: "tree", label: { en: "WBS", fa: "WBS" }, action: { window: "wbs" } },
    { icon: "activity", label: { en: "Activity", fa: "فعالیت" }, action: { dialog: "add-activity" } },
    { icon: "calendar", label: { en: "Schedule", fa: "زمان‌بندی" }, action: { dialog: "schedule" } },
  ] },
  { id: "edit", label: { en: "Edit", fa: "ویرایش" }, items: [
    { icon: "edit", label: { en: "Edit", fa: "ویرایش" }, action: { dialog: "project-properties" } },
    { icon: "undo", label: { en: "Undo", fa: "بازگردانی" }, action: { command: "undo" } },
    { icon: "redo", label: { en: "Redo", fa: "تکرار" }, action: { command: "redo" } },
  ] },
  { id: "view", label: { en: "View", fa: "نما" }, items: [
    { icon: "columns", label: { en: "Columns", fa: "ستون‌ها" }, action: { dialog: "columns" } },
    { icon: "filter", label: { en: "Filter", fa: "فیلتر" }, action: { dialog: "filters" } },
    { icon: "sort", label: { en: "Group", fa: "گروه" }, action: { dialog: "group-sort" } },
    { icon: "clock", label: { en: "Timescale", fa: "مقیاس" }, action: { dialog: "timescale" } },
    { icon: "bars", label: { en: "Bars", fa: "میله‌ها" }, action: { dialog: "bars" } },
  ] },
  { id: "assign", label: { en: "Assign", fa: "تخصیص" }, items: [
    { icon: "resource", label: { en: "Resources", fa: "منابع" }, action: { dialog: "assign-resources" } },
    { icon: "link", label: { en: "Predecessors", fa: "پیش‌نیاز" }, action: { dialog: "assign-predecessors" } },
    { icon: "network", label: { en: "Network", fa: "شبکه" }, action: { window: "network" } },
  ] },
  { id: "tools", label: { en: "Tools", fa: "ابزارها" }, items: [
    { icon: "clock", label: { en: "Level", fa: "تسطیح" }, action: { dialog: "level" } },
    { icon: "activity", label: { en: "Trace", fa: "ردیابی" }, action: { window: "trace" } },
  ] },
  { id: "organization", label: { en: "Organization", fa: "سازمان" }, items: [
    { icon: "resource", label: { en: "Resources", fa: "منابع" }, action: { window: "resources" } },
    { icon: "calendar", label: { en: "Calendars", fa: "تقویم‌ها" }, action: { window: "calendars" } },
  ] },
  { id: "dictionaries", label: { en: "Dictionaries", fa: "واژه‌نامه" }, items: [
    { icon: "book", label: { en: "Codes", fa: "کدها" }, action: { dialog: "dictionaries" } },
  ] },
  { id: "find", label: { en: "Find", fa: "یافتن" }, items: [
    { icon: "find", label: { en: "Find", fa: "یافتن" }, action: { dialog: "find" } },
    { icon: "find", label: { en: "Replace", fa: "جایگزینی" }, action: { dialog: "find-replace" } },
  ] },
  { id: "move", label: { en: "Move", fa: "جابه‌جایی" }, items: [
    { icon: "left", label: { en: "Back", fa: "عقب" }, action: { command: "back" } },
    { icon: "right", label: { en: "Forward", fa: "جلو" }, action: { command: "forward" } },
  ] },
  { id: "print", label: { en: "Print", fa: "چاپ" }, items: [
    { icon: "print", label: { en: "Print preview", fa: "پیش‌نمایش" }, action: { dialog: "print" } },
  ] },
  { id: "publish", label: { en: "Publish", fa: "انتشار" }, items: [
    { icon: "book", label: { en: "Documents", fa: "اسناد" }, action: { window: "documents" } },
  ] },
  { id: "reports", label: { en: "Reports", fa: "گزارش‌ها" }, items: [
    { icon: "table", label: { en: "Reports", fa: "گزارش‌ها" }, action: { window: "reports" } },
    { icon: "help", label: { en: "Wizard", fa: "جادوگر" }, action: { dialog: "report-wizard" } },
  ] },
  { id: "layout", label: { en: "Layout", fa: "چیدمان" }, items: [
    { icon: "columns", label: { en: "Layout", fa: "چیدمان" }, action: { dialog: "layout-manager" } },
    { icon: "table", label: { en: "Font and row", fa: "قلم و ردیف" }, action: { dialog: "font-row" } },
  ] },
  { id: "top-layout", label: { en: "Top Layout", fa: "چیدمان بالا" }, items: [
    { icon: "activity", label: { en: "Activities", fa: "فعالیت‌ها" }, action: { window: "activities" } },
  ] },
  { id: "bottom-layout", label: { en: "Bottom Layout", fa: "چیدمان پایین" }, items: [
    { icon: "table", label: { en: "Details", fa: "جزئیات" }, action: { dialog: "customize-details" } },
  ] },
  { id: "administrator", label: { en: "Administrator", fa: "مدیر" }, items: [
    { icon: "settings", label: { en: "Users", fa: "کاربران" }, action: { window: "administration" } },
    { icon: "settings", label: { en: "Preferences", fa: "تنظیمات" }, action: { dialog: "admin-preferences" } },
  ] },
];

// View → Toolbars is generated from the toolbar register so every bar that can
// be shown or hidden is also listed, with no second hand-maintained list.
const toolbarMenu = MENUS.find((menu) => menu.id === "view")?.items.find((item) => item.label.en === "Toolbars");
if (toolbarMenu) {
  toolbarMenu.children = TOOLBARS.map((bar) => ({ label: bar.label, action: { command: `toolbar:${bar.id}` } }));
}

function renderMenus(state: DemoState): string {
  // Toolbar entries are checkable: the tick reflects which toolbars are shown.
  const isChecked = (action?: MenuAction): boolean =>
    Boolean(action?.command?.startsWith("toolbar:") && state.toolbars.includes(action.command.slice(8)));
  const mark = (action?: MenuAction): string => `<span class="cp-vd-menutick" aria-hidden="true">${isChecked(action) ? "✓" : ""}</span>`;
  return `<div class="cp-vd-menubar" role="menubar">${MENUS.map((menu) => `<div class="cp-vd-menu" data-vd-menu="${menu.id}">
    <button type="button" class="cp-vd-menu-trigger" aria-haspopup="true" aria-expanded="false">${esc(label(menu.label, state.locale))}</button>
    <div class="cp-vd-popup" hidden>${menu.items.map((item) => item.children
      ? `<div class="cp-vd-submenu"><button type="button" class="cp-vd-menu-item" data-vd-submenu>${esc(label(item.label, state.locale))}<span>▸</span></button><div class="cp-vd-subpopup" hidden>${item.children.map((child) => `<button type="button" class="cp-vd-menu-item${isChecked(child.action) ? " is-checked" : ""}" data-vd-action='${JSON.stringify(child.action ?? {})}'>${mark(child.action)}${esc(label(child.label, state.locale))}</button>`).join("")}</div></div>`
      : `<button type="button" class="cp-vd-menu-item${item.action?.reason ? " is-disabled" : ""}" ${item.action?.reason ? "disabled" : `data-vd-action='${JSON.stringify(item.action ?? {})}'`}>${mark(item.action)}${esc(label(item.label, state.locale))}${item.shortcut ? `<kbd>${esc(item.shortcut)}</kbd>` : ""}${item.action?.reason ? `<small>${esc(label(item.action.reason, state.locale))}</small>` : ""}</button>`).join("")}</div>
  </div>`).join("")}</div>`;
}

function renderToolbars(state: DemoState): string {
  return `<div class="cp-vd-toolbars" role="toolbar">${TOOLBARS.filter((bar) => state.toolbars.includes(bar.id)).map((bar) => `<div class="cp-vd-tgroup" title="${esc(label(bar.label, state.locale))}">${bar.items.map((item) => `<button type="button" class="cp-vd-tbtn" title="${esc(label(item.label, state.locale))}" data-vd-action='${JSON.stringify(item.action)}'>${workspaceIcon(item.icon)}<span>${esc(label(item.label, state.locale))}</span></button>`).join("")}</div>`).join("")}</div>`;
}

function renderTabs(state: DemoState): string {
  const index = WINDOWS.findIndex((window) => window.id === state.window);
  return `<div class="cp-vd-tabs" role="tablist">
    <button type="button" class="cp-vd-navbtn" data-vd-command="back" ${state.history.length ? "" : "disabled"} title="${esc(t(state.locale, "Back", "عقب"))}">‹</button>
    <button type="button" class="cp-vd-navbtn" data-vd-command="forward" ${state.forward.length ? "" : "disabled"} title="${esc(t(state.locale, "Forward", "جلو"))}">›</button>
    <div class="cp-vd-tablist">${WINDOWS.map((window) => `<button type="button" role="tab" class="cp-vd-tab${window.id === state.window ? " is-active" : ""}" data-vd-window="${window.id}" aria-selected="${window.id === state.window}">${esc(label(window, state.locale))}</button>`).join("")}</div>
    <span class="cp-vd-tabspacer"></span>
    <button type="button" class="cp-vd-navbtn" data-vd-window="${WINDOWS[(index - 1 + WINDOWS.length) % WINDOWS.length].id}" title="${esc(t(state.locale, "Previous window", "پنجرهٔ قبلی"))}">⇤</button>
    <button type="button" class="cp-vd-navbtn" data-vd-window="${WINDOWS[(index + 1) % WINDOWS.length].id}" title="${esc(t(state.locale, "Next window", "پنجرهٔ بعدی"))}">⇥</button>
  </div>`;
}

function dialogContent(name: string, state: DemoState): string {
  const rows = (head: string[], body: string): string => `<table class="cp-vd-mini"><thead><tr>${head.map((h) => `<th>${esc(h)}</th>`).join("")}</tr></thead><tbody>${body}</tbody></table>`;
  switch (name) {
    case "columns":
      return `<div class="cp-vd-two"><div><strong>${esc(t(state.locale, "Available columns", "ستون‌های موجود"))}</strong><ul>${ACTIVITY_COLUMNS.map((column) => `<li><label><input type="checkbox" data-vd-column="${column.id}" ${state.columns.includes(column.id) ? "checked" : ""}> ${esc(label(column, state.locale))}</label></li>`).join("")}</ul></div><div class="cp-vd-hintbox">${esc(t(state.locale, "Tick a column to add it to the activity table. Order follows the list.", "برای افزودن ستون به جدول آن را علامت بزنید. ترتیب مطابق فهرست است."))}</div></div>`;
    case "filters":
      return `<div class="cp-vd-form"><label>${esc(t(state.locale, "Filter name", "نام فیلتر"))}<input name="filter" value="${esc(state.filter)}" placeholder="${esc(t(state.locale, "Type to filter activities", "برای فیلتر فعالیت‌ها تایپ کنید"))}"></label><div class="cp-vd-radios"><label><input type="radio" checked> ${esc(t(state.locale, "Any criteria", "هر معیار"))}</label><label><input type="radio"> ${esc(t(state.locale, "All criteria", "همهٔ معیارها"))}</label></div>${rows(["Field", "Operator", "Value"], `<tr><td>Activity ID / Name</td><td>contains</td><td><input value="${esc(state.filter)}"></td></tr>`)}</div>`;
    case "group-sort":
      return `<div class="cp-vd-form"><label>${esc(t(state.locale, "Group by", "گروه‌بندی"))}<select name="group"><option value="wbs"${state.groupBy === "wbs" ? " selected" : ""}>WBS</option><option value="none"${state.groupBy === "none" ? " selected" : ""}>${esc(t(state.locale, "No grouping", "بدون گروه"))}</option></select></label><label>${esc(t(state.locale, "Sort by", "ترتیب بر اساس"))}<select name="sort"><option>Activity ID</option><option>Activity Name</option><option>Total Float</option></select></label><div class="cp-vd-radios"><label><input type="radio" checked> ${esc(t(state.locale, "Ascending", "صعودی"))}</label><label><input type="radio"> ${esc(t(state.locale, "Descending", "نزولی"))}</label></div><label class="cp-vd-check"><input type="checkbox" checked> ${esc(t(state.locale, "Show group totals", "نمایش جمع گروه"))}</label></div>`;
    case "timescale":
      return `<div class="cp-vd-form"><label>${esc(t(state.locale, "Timescale format", "قالب مقیاس"))}<select name="scale">${(["day", "week", "month", "quarter", "year"] as const).map((scale) => `<option value="${scale}"${scale === state.scale ? " selected" : ""}>${esc(t(state.locale, scale, { day: "روز", week: "هفته", month: "ماه", quarter: "فصل", year: "سال" }[scale]))}</option>`).join("")}</select></label><label>${esc(t(state.locale, "Date interval", "بازهٔ تاریخ"))}<select><option>Month / Day</option><option>Quarter / Month</option><option>Year / Month</option></select></label><label class="cp-vd-check"><input type="checkbox" checked> ${esc(t(state.locale, "Show ordinal dates", "نمایش تاریخ ترتیبی"))}</label></div>`;
    case "bars":
      return `<div class="cp-vd-form">${rows(["Bar", "Shape", "Colour"], `<tr><td>Normal</td><td>Rounded bar</td><td><input type="color" value="#2f5fa8"></td></tr><tr><td>Critical</td><td>Rounded bar</td><td><input type="color" value="#c0392b"></td></tr><tr><td>Summary</td><td>Bracket</td><td><input type="color" value="#4f9a3c"></td></tr><tr><td>Milestone</td><td>Diamond</td><td><input type="color" value="#1f2937"></td></tr>`)}<label class="cp-vd-check"><input type="checkbox" checked> ${esc(t(state.locale, "Show baseline bars", "نمایش میله‌های مبنا"))}</label></div>`;
    case "bar-options":
      return `<div class="cp-vd-form">${rows(["Option", "Value"], `<tr><td>Row height</td><td>24 px</td></tr><tr><td>Bar height</td><td>16 px</td></tr><tr><td>Label position</td><td>Right of bar</td></tr>`)}<label class="cp-vd-check"><input type="checkbox" checked> ${esc(t(state.locale, "Show relationship lines", "نمایش خطوط روابط"))}</label></div>`;
    case "font-row":
      return `<div class="cp-vd-form"><label>${esc(t(state.locale, "Font", "قلم"))}<select><option>Inter 11</option><option>Inter 12</option><option>Vazirmatn 12</option></select></label><div class="cp-vd-radios"><label><input type="radio" checked> ${esc(t(state.locale, "Compact rows", "ردیف فشرده"))}</label><label><input type="radio"> ${esc(t(state.locale, "Comfortable rows", "ردیف راحت"))}</label></div></div>`;
    case "layout-manager":
      return `${rows(["Layout", "Scope", "Status"], `<tr><td>CUBI Classic Schedule Layout</td><td>Project</td><td>Current</td></tr><tr><td>Cost and resource view</td><td>Project</td><td>Available</td></tr><tr><td>Commissioning look-ahead</td><td>Project</td><td>Available</td></tr>`)}<p class="cp-vd-note">${esc(t(state.locale, "Layouts are visual examples in this demo.", "چیدمان‌ها در این نمایش نمونهٔ بصری هستند."))}</p>`;
    case "customize-details":
      return `<div class="cp-vd-two"><div><strong>${esc(t(state.locale, "Available tabs", "زبانه‌های موجود"))}</strong><ul>${["Cost", "Duration", "WPs & Docs", "Feedback"].map((item) => `<li><label><input type="checkbox"> ${esc(item)}</label></li>`).join("")}</ul></div><div><strong>${esc(t(state.locale, "Display tabs", "زبانه‌های نمایش"))}</strong><ul>${["General", "Status", "Resources", "Predecessors", "Successors"].map((item) => `<li><label><input type="checkbox" checked> ${esc(item)}</label></li>`).join("")}</ul></div></div>`;
    case "new-project":
      return `<div class="cp-vd-form"><label>${esc(t(state.locale, "Project ID", "شناسهٔ پروژه"))}<input value="CUBI-DEMO-002"></label><label>${esc(t(state.locale, "Project name", "نام پروژه"))}<input value="Intake Screen Replacement"></label><label>${esc(t(state.locale, "Start date", "تاریخ شروع"))}<input value="2027-02-01"></label></div>`;
    case "project-properties":
      return `<div class="cp-vd-form"><label>${esc(t(state.locale, "Project ID", "شناسهٔ پروژه"))}<input value="CUBI-DEMO-001" readonly></label><label>${esc(t(state.locale, "Name", "نام"))}<input value="Riverside Pump Station Upgrade"></label><label>${esc(t(state.locale, "Data date", "تاریخ داده"))}<input value="2026-12-03"></label></div>`;
    case "calendar":
      return `<div class="cp-vd-two"><div class="cp-vd-calendar"><div class="cp-vd-cal-head"><button type="button" aria-label="${esc(t(state.locale, "Previous month", "ماه قبل"))}">‹</button><strong>${esc(t(state.locale, "December 2026", "دسامبر ۲۰۲۶"))}</strong><button type="button" aria-label="${esc(t(state.locale, "Next month", "ماه بعد"))}">›</button></div><div class="cp-vd-cal-grid">${calendarGrid(state.locale, 2026, 11)}</div></div><div class="cp-vd-form"><label>${esc(t(state.locale, "Work hours", "ساعت کار"))}<input value="08:00 – 16:00"></label><label>${esc(t(state.locale, "Nonwork", "غیرکاری"))}<input value="${esc(t(state.locale, "Thursday, Friday", "پنجشنبه، جمعه"))}"></label></div></div>`;
    case "schedule":
      return `<div class="cp-vd-form"><label>${esc(t(state.locale, "Data date", "تاریخ داده"))}<input value="2026-12-03"></label><label>${esc(t(state.locale, "Schedule mode", "حالت زمان‌بندی"))}<select><option>Forward and backward</option><option>Forward only</option></select></label><label class="cp-vd-check"><input type="checkbox" checked> ${esc(t(state.locale, "Level resources", "تسطیح منابع"))}</label><p class="cp-vd-note">${esc(t(state.locale, "Visual demo: no schedule run is executed.", "نمایش بصری: هیچ محاسبهٔ زمان‌بندی اجرا نمی‌شود."))}</p></div>`;
    case "level":
      return `<div class="cp-vd-form"><label>${esc(t(state.locale, "Level within float only", "تسطیح فقط در محدودهٔ شناوری"))}<input type="checkbox" checked></label><label>${esc(t(state.locale, "Priority", "اولویت"))}<select><option>Total float</option><option>Activity ID</option></select></label></div>`;
    case "baselines":
      return `${rows(["Baseline", "Date", "Activities"], `<tr><td>BL-01</td><td>03-Nov-2026</td><td>20</td></tr><tr><td>BL-02</td><td>—</td><td>—</td></tr>`)}`;
    case "find":
      return `<div class="cp-vd-form"><label>${esc(t(state.locale, "Find activity", "یافتن فعالیت"))}<input name="filter" value="${esc(state.filter)}"></label><div class="cp-vd-radios"><label><input type="radio" checked> ${esc(t(state.locale, "Activity ID", "شناسه"))}</label><label><input type="radio"> ${esc(t(state.locale, "Activity name", "نام"))}</label></div></div>`;
    case "find-replace":
      return `<div class="cp-vd-form"><label>${esc(t(state.locale, "Find", "یافتن"))}<input></label><label>${esc(t(state.locale, "Replace with", "جایگزینی با"))}<input></label><label class="cp-vd-check"><input type="checkbox"> ${esc(t(state.locale, "Match case", "تطابق حروف"))}</label></div>`;
    case "renumber":
      return `<div class="cp-vd-form"><label>${esc(t(state.locale, "Prefix", "پیشوند"))}<input value="A"></label><label>${esc(t(state.locale, "Start number", "شمارهٔ شروع"))}<input value="1000"></label><label>${esc(t(state.locale, "Increment", "گام"))}<input value="10"></label></div>`;
    case "assign-resources":
      return `<div class="cp-vd-form"><label>${esc(t(state.locale, "Activity", "فعالیت"))}<input value="${esc(state.activityId)}" readonly></label><label>${esc(t(state.locale, "Resource", "منبع"))}<select>${RESOURCES.map((resource) => `<option>${esc(resource.name)}</option>`).join("")}</select></label><label>${esc(t(state.locale, "Budgeted units", "واحد بودجه"))}<input value="40"></label></div>`;
    case "assign-roles":
      return `<div class="cp-vd-form"><label>${esc(t(state.locale, "Role", "نقش"))}<select><option>Site engineer</option><option>Planner</option><option>Cost engineer</option></select></label><label>${esc(t(state.locale, "Units", "واحد"))}<input value="1"></label></div>`;
    case "assign-predecessors":
      return `${rows(["Activity", "Type", "Lag"], `<tr><td>A1100</td><td>FS</td><td>0</td></tr><tr><td>A1200</td><td>SS</td><td>5</td></tr>`)}`;
    case "assign-successors":
      return `${rows(["Activity", "Type", "Lag"], `<tr><td>A1340</td><td>FS</td><td>0</td></tr>`)}`;
    case "add-activity":
      return `<div class="cp-vd-form"><label>${esc(t(state.locale, "Activity ID", "شناسه"))}<input value="A1160"></label><label>${esc(t(state.locale, "Activity name", "نام"))}<input value="New activity"></label><label>${esc(t(state.locale, "Duration", "مدت"))}<input value="5"></label></div>`;
    case "import":
      return `<div class="cp-vd-form"><label>${esc(t(state.locale, "Format", "قالب"))}<select><option>XER</option><option>XML</option><option>Excel</option></select></label><label>${esc(t(state.locale, "File", "فایل"))}<input value="CUBI-DEMO-001.xer" readonly></label><p class="cp-vd-note">${esc(t(state.locale, "Visual demo: no file is read.", "نمایش بصری: هیچ فایلی خوانده نمی‌شود."))}</p></div>`;
    case "export":
      return `<div class="cp-vd-form"><label>${esc(t(state.locale, "Format", "قالب"))}<select><option>XER</option><option>Excel</option><option>PDF</option></select></label><label>${esc(t(state.locale, "Destination", "مقصد"))}<input value="CUBI-DEMO-001-export.xer"></label></div>`;
    case "print":
      return `<div class="cp-vd-print"><div class="cp-vd-print-page"><h3>CUBI-DEMO-001</h3><p>Riverside Pump Station Upgrade</p><table class="cp-vd-mini">${ACTIVITIES.slice(0, 6).map((row) => `<tr><td>${esc(row.id)}</td><td>${esc(row.name)}</td><td>${row.pct}%</td></tr>`).join("")}</table></div><div class="cp-vd-form"><label>${esc(t(state.locale, "Copies", "نسخه‌ها"))}<input value="1"></label><label>${esc(t(state.locale, "Paper", "کاغذ"))}<select><option>A4 landscape</option><option>A3 landscape</option></select></label></div></div>`;
    case "report-wizard":
      return `<div class="cp-vd-form"><label>${esc(t(state.locale, "Report", "گزارش"))}<select><option>Schedule report</option><option>Cost report</option><option>Resource report</option></select></label><label>${esc(t(state.locale, "Group by", "گروه‌بندی"))}<select><option>WBS</option><option>Resource</option></select></label><label class="cp-vd-check"><input type="checkbox" checked> ${esc(t(state.locale, "Include Gantt chart", "شامل نمودار گانت"))}</label></div>`;
    case "preferences":
      return `<div class="cp-vd-form"><label>${esc(t(state.locale, "Language", "زبان"))}<select><option>English</option><option>فارسی</option></select></label><label>${esc(t(state.locale, "Date format", "قالب تاریخ"))}<select><option>DD-MMM-YY</option><option>YYYY-MM-DD</option></select></label><label class="cp-vd-check"><input type="checkbox" checked> ${esc(t(state.locale, "Confirm before delete", "تأیید پیش از حذف"))}</label></div>`;
    case "admin-preferences":
      return `<div class="cp-vd-form"><label>${esc(t(state.locale, "Industry", "صنعت"))}<select><option>Construction</option><option>Engineering</option></select></label><label>${esc(t(state.locale, "Week starts on", "شروع هفته"))}<select><option>Sunday</option><option>Saturday</option></select></label></div>`;
    case "dictionaries":
      return `${rows(["Dictionary", "Values"], `<tr><td>Activity codes</td><td>Phase, Discipline</td></tr><tr><td>UDFs</td><td>Package, Zone</td></tr><tr><td>Currencies</td><td>USD</td></tr>`)}`;
    case "roles":
      return `${rows(["Role", "Units", "Rate"], `<tr><td>Site engineer</td><td>2.0</td><td>85</td></tr><tr><td>Planner</td><td>1.0</td><td>95</td></tr>`)}`;
    case "security-profiles":
      return `${rows(["Profile", "Users", "Access"], `<tr><td>Administrator</td><td>1</td><td>Full</td></tr><tr><td>Project Manager</td><td>3</td><td>Project</td></tr><tr><td>Read only</td><td>5</td><td>View</td></tr>`)}<p class="cp-vd-note">${esc(t(state.locale, "Sample profiles for layout review.", "پروفایل‌های نمونه برای بازبینی چیدمان."))}</p>`;
    case "network-options":
      return `<div class="cp-vd-form"><label>${esc(t(state.locale, "Box template", "قالب جعبه"))}<select><option>Activity ID / Name / Dates</option><option>Activity ID / Name</option></select></label><label class="cp-vd-check"><input type="checkbox" checked> ${esc(t(state.locale, "Critical path border", "حاشیهٔ مسیر بحرانی"))}</label></div>`;
    case "timeline-options":
      return `<div class="cp-vd-two"><div><strong>${esc(t(state.locale, "Show on timeline", "نمایش در خط زمانی"))}</strong><ul>${[["Summary bars", "میله‌های خلاصه"], ["Milestones", "نقاط عطف"], ["Data date", "تاریخ داده"], ["Phase labels", "برچسب فازها"]].map((item) => `<li><label><input type="checkbox" checked> ${esc(t(state.locale, item[0], item[1]))}</label></li>`).join("")}</ul></div><div class="cp-vd-form"><label>${esc(t(state.locale, "Date format", "قالب تاریخ"))}<select><option>DD-MMM-YY</option><option>DD/MM/YYYY</option></select></label><label>${esc(t(state.locale, "Bar height", "ارتفاع میله"))}<input value="14 px"></label></div></div>`;
    case "shortcuts":
      return `${rows(["Command", "Shortcut"], `<tr><td>Find</td><td><kbd>Ctrl+F</kbd></td></tr><tr><td>Schedule</td><td><kbd>F9</kbd></td></tr><tr><td>Close window</td><td><kbd>Ctrl+W</kbd></td></tr><tr><td>Back</td><td><kbd>Alt+Left</kbd></td></tr><tr><td>Help</td><td><kbd>F1</kbd></td></tr>`)}`;
    case "about":
      return `<p>${esc(t(state.locale, "CUBI Professional Workspace — visual demonstration with fixed sample data. No schedule, cost or resource calculation is performed.", "محیط کار حرفه‌ای CUBI — نمایش بصری با دادهٔ نمونهٔ ثابت. هیچ محاسبهٔ زمان‌بندی، هزینه یا منبع انجام نمی‌شود."))}</p>`;
    default:
      return `<p class="cp-vd-note">${esc(t(state.locale, "This dialog is a visual example.", "این دیالوگ یک نمونهٔ بصری است."))}</p>`;
  }
}

function dialogTitle(name: string, locale: string): string {
  const titles: Record<string, [string, string]> = {
    columns: ["Columns", "ستون‌ها"], filters: ["Filters", "فیلترها"], "group-sort": ["Group and Sort", "گروه‌بندی و ترتیب"],
    timescale: ["Timescale", "مقیاس زمانی"], bars: ["Bars", "میله‌ها"], "bar-options": ["Bar Chart Options", "تنظیمات نمودار"],
    "font-row": ["Table Font and Row", "قلم و ردیف جدول"], "layout-manager": ["Layout Manager", "مدیر چیدمان"],
    "customize-details": ["Customize Activity Details", "سفارشی‌سازی جزئیات"], "new-project": ["New Project", "پروژهٔ جدید"],
    "project-properties": ["Project Properties", "مشخصات پروژه"], calendar: ["Calendar Editor", "ویرایش تقویم"],
    schedule: ["Schedule", "زمان‌بندی"], level: ["Level Resources", "تسطیح منابع"], baselines: ["Baselines", "خطوط مبنا"],
    find: ["Find", "یافتن"], "find-replace": ["Find and Replace", "یافتن و جایگزینی"], renumber: ["Renumber Activity IDs", "شماره‌گذاری دوباره"],
    "assign-resources": ["Assign Resources", "تخصیص منابع"], "assign-roles": ["Assign Roles", "تخصیص نقش"],
    "assign-predecessors": ["Assign Predecessors", "تخصیص پیش‌نیاز"], "assign-successors": ["Assign Successors", "تخصیص جانشین"],
    "add-activity": ["Add Activity", "افزودن فعالیت"], import: ["Import", "ورود"], export: ["Export", "خروجی"],
    print: ["Print Preview", "پیش‌نمایش چاپ"], "report-wizard": ["Report Wizard", "جادوگر گزارش"], preferences: ["Preferences", "تنظیمات"],
    "admin-preferences": ["Administration Preferences", "تنظیمات مدیریت"], dictionaries: ["Dictionaries", "واژه‌نامه‌ها"],
    roles: ["Roles", "نقش‌ها"], "network-options": ["Activity Network Options", "تنظیمات شبکه"], "timeline-options": ["Timeline Options", "تنظیمات خط زمانی"], shortcuts: ["Keyboard Shortcuts", "کلیدهای میانبر"], about: ["About CUBI Workspace", "دربارهٔ CUBI"],
    "security-profiles": ["Security Profiles", "پروفایل‌های امنیتی"],
  };
  const entry = titles[name] ?? [name, name];
  return t(locale, entry[0], entry[1]);
}

function renderDialogs(state: DemoState): string {
  const allNames = ["columns", "filters", "group-sort", "timescale", "bars", "bar-options", "font-row", "layout-manager", "customize-details", "new-project", "project-properties", "calendar", "schedule", "level", "baselines", "find", "find-replace", "renumber", "assign-resources", "assign-roles", "assign-predecessors", "assign-successors", "add-activity", "import", "export", "print", "report-wizard", "preferences", "admin-preferences", "dictionaries", "roles", "network-options", "timeline-options", "shortcuts", "about", "security-profiles"];
  const names = state.project
    ? allNames.filter((name) => ["columns", "filters", "group-sort", "timescale", "bars", "bar-options", "font-row", "shortcuts", "about"].includes(name))
    : allNames;
  return names.map((name) => `<dialog class="cp-vd-dialog" data-vd-dialog="${name}">
    <form method="dialog" data-vd-form="${name}">
      <div class="cp-vd-dialog-title"><span>${esc(dialogTitle(name, state.locale))}</span><button type="button" data-vd-close aria-label="Close">×</button></div>
      <div class="cp-vd-dialog-body">${dialogContent(name, state)}</div>
      <div class="cp-vd-dialog-actions"><button type="submit" class="is-primary">${esc(t(state.locale, "OK", "تأیید"))}</button><button type="button" data-vd-default>${esc(t(state.locale, "Default", "پیش‌فرض"))}</button><button type="button" data-vd-close>${esc(t(state.locale, "Cancel", "لغو"))}</button></div>
    </form>
  </dialog>`).join("");
}

export function renderVisualDemo(state: DemoState): string {
  const index = WINDOWS.findIndex((window) => window.id === state.window);
  const projectId = projectIdFor(state);
  const projectName = projectNameFor(state);
  const badge = state.project
    ? t(state.locale, "Connected project · read-only visual shell", "پروژهٔ متصل · پوستهٔ بصری فقط‌خواندنی")
    : t(state.locale, "Visual demo · sample data", "نمایش بصری · دادهٔ نمونه");
  const exitLabel = state.project
    ? t(state.locale, "Open classic workspace for editing", "بازکردن محیط کلاسیک برای ویرایش")
    : t(state.locale, "Return to workspace", "بازگشت به محیط کار");
  return `<div class="cp-vd" data-visual-demo dir="${state.locale.startsWith("fa") ? "rtl" : "ltr"}">
    <div class="cp-vd-titlebar"><strong>CUBI</strong><span>${esc(t(state.locale, "Professional Workspace", "محیط کار حرفه‌ای"))}</span><span class="cp-vd-project">${esc(projectId)} — ${esc(projectName)}</span><span class="cp-vd-demo-badge">${esc(badge)}</span><span class="cp-vd-titlebar-spacer"></span><button type="button" class="cp-vd-exit" data-vd-exit>${esc(exitLabel)}</button></div>
    ${renderMenus(state)}
    ${renderToolbars(state)}
    ${renderTabs(state)}
    <div class="cp-vd-layoutbar"><span>${esc(t(state.locale, "Layout", "چیدمان"))}: <strong>CUBI Classic Schedule Layout</strong></span><span>${esc(t(state.locale, "Filter", "فیلتر"))}: <strong>${esc(state.filter || t(state.locale, "All Activities", "همهٔ فعالیت‌ها"))}</strong></span><span class="cp-vd-layoutspacer"></span><button type="button" class="cp-vd-btn" data-vd-dialog="columns">${workspaceIcon("columns")}${esc(t(state.locale, "Columns", "ستون‌ها"))}</button><button type="button" class="cp-vd-btn" data-vd-dialog="filters">${workspaceIcon("filter")}${esc(t(state.locale, "Filters", "فیلترها"))}</button><button type="button" class="cp-vd-btn" data-vd-dialog="group-sort">${workspaceIcon("sort")}${esc(t(state.locale, "Group and Sort", "گروه و ترتیب"))}</button><button type="button" class="cp-vd-btn" data-vd-dialog="timescale">${workspaceIcon("clock")}${esc(t(state.locale, "Timescale", "مقیاس"))}</button><button type="button" class="cp-vd-btn" data-vd-dialog="bars">${workspaceIcon("bars")}${esc(t(state.locale, "Bars", "میله‌ها"))}</button></div>
    <div class="cp-vd-main">${renderWindow(state)}</div>
    <div class="cp-vd-status"><span>${esc(t(state.locale, "Project", "پروژه"))}: ${esc(projectId)}</span><span>${esc(t(state.locale, "Revision", "ویرایش"))}: ${state.project?.revision ?? "—"}</span><span>${esc(t(state.locale, "Activities", "فعالیت‌ها"))}: ${state.project?.activities.length ?? ACTIVITIES.length}</span><span>${esc(t(state.locale, "Window", "پنجره"))}: ${esc(label(WINDOWS[index] ?? WINDOWS[0], state.locale))}</span><span class="cp-vd-status-end">${esc(state.project ? t(state.locale, "Server project data · no edits are sent from this visual shell", "دادهٔ پروژه از سرور · ویرایش از این پوسته ارسال نمی‌شود") : t(state.locale, "Preview data — not saved or calculated", "دادهٔ پیش‌نمایش — ذخیره یا محاسبه نشده"))}</span></div>
    ${renderDialogs(state)}
  </div>`;
}

function liveProjectData(workspace: WorkspaceState): LiveProjectData {
  const nodesById = new Map(workspace.wbsNodes.map((node) => [node.id, node]));
  const numberFrom = (record: Readonly<Record<string, unknown>>, keys: string[]): number | null => {
    for (const key of keys) {
      const value = record[key];
      if (typeof value === "number" && Number.isFinite(value)) return value;
      if (typeof value === "string" && value.trim() !== "") {
        const parsed = Number(value);
        if (Number.isFinite(parsed)) return parsed;
      }
    }
    return null;
  };
  const textFrom = (record: Readonly<Record<string, unknown>>, keys: string[]): string => {
    for (const key of keys) {
      const value = record[key];
      if (typeof value === "string" && value.trim() !== "") return value;
      if (typeof value === "number" || typeof value === "boolean") return String(value);
    }
    return "";
  };
  const predecessors = new Map<string, string[]>();
  const successors = new Map<string, string[]>();
  for (const link of workspace.relationships) {
    const pred = predecessors.get(link.successorId) ?? [];
    pred.push(link.predecessorId);
    predecessors.set(link.successorId, pred);
    const succ = successors.get(link.predecessorId) ?? [];
    succ.push(link.successorId);
    successors.set(link.predecessorId, succ);
  };
  const activities: DemoActivity[] = workspace.activities.map((activity) => {
    const cells = activity.cells ?? {};
    const wbs = nodesById.get(activity.wbsId);
    const start = activity.gantt?.start ?? textFrom(cells, ["start", "activity.early_start"]);
    const finish = activity.gantt?.finish ?? textFrom(cells, ["finish", "activity.early_finish"]);
    const duration = numberFrom(cells, ["activity.planned_duration", "duration"]);
    const pct = activity.gantt?.progressPercent ?? numberFrom(cells, ["activity.duration_percent_complete", "progress"]);
    const rowPreds = predecessors.get(activity.id) ?? [];
    const rowSuccs = successors.get(activity.id) ?? [];
    const displayWbs = wbs ? `${wbs.localCode} ${wbs.name}` : "Unassigned";
    return {
      id: activity.id,
      name: activity.name,
      phase: wbs?.name ?? "Unassigned",
      wbs: displayWbs,
      type: textFrom(cells, ["activity.type", "activity.activity_type"]) || "—",
      od: duration,
      rd: numberFrom(cells, ["activity.remaining_duration"]),
      ad: null,
      start,
      finish,
      es: textFrom(cells, ["activity.early_start"]),
      ef: textFrom(cells, ["activity.early_finish"]),
      ls: textFrom(cells, ["activity.late_start"]),
      lf: textFrom(cells, ["activity.late_finish"]),
      tf: numberFrom(cells, ["activity.total_float"]),
      ff: numberFrom(cells, ["activity.free_float"]),
      pct,
      status: textFrom(cells, ["activity.status", "activity.status_code"]) || "—",
      calendar: textFrom(cells, ["activity.calendar"]) || "—",
      pred: rowPreds.length ? rowPreds.join(", ") : "—",
      succ: rowSuccs.length ? rowSuccs.join(", ") : "—",
      res: "—",
      budgetUnits: null,
      actualUnits: null,
      remainingUnits: null,
      budgetCost: null,
      actualCost: null,
      remainingCost: null,
      codes: textFrom(cells, ["activity.activity_code"]) || "—",
      constraint: textFrom(cells, ["activity.constraint_type"]) || "—",
      critical: activity.gantt?.critical ?? cells["activity.is_critical"] === true,
      milestone: duration === 0,
      baseline: "—",
    };
  });
  for (const activity of workspace.activities) {
    let current: string | null = activity.wbsId;
    while (current) {
      activityCounts.set(current, (activityCounts.get(current) ?? 0) + 1);
      current = nodesById.get(current)?.parentWbsId ?? null;
    }
  }
  const levels = new Map<string, number>();
  const levelOf = (id: string): number => {
    const cached = levels.get(id);
    if (cached !== undefined) return cached;
    const node = nodesById.get(id);
    const level = !node || node.parentKind === "project" || !node.parentWbsId
      ? 0
      : levelOf(node.parentWbsId) + 1;
    levels.set(id, level);
    return level;
  };
  const wbsNodes = workspace.wbsNodes.map((node) => ({
    code: node.localCode,
    name: node.name,
    level: levelOf(node.id),
    total: activityCounts.get(node.id) ?? 0,
  }));
  const dates = activities.flatMap((activity) => [activity.start, activity.finish])
    .filter(isIsoDate)
    .sort();
  const root = workspace.wbsNodes.find((node) => node.parentKind === "project");
  return {
    id: workspace.context.project_id,
    name: root?.name ?? workspace.context.project_id,
    revision: workspace.context.revision,
    activities,
    wbsNodes,
    relationships: workspace.relationships.map((link) => ({
      predecessorId: link.predecessorId,
      successorId: link.successorId,
      type: link.type,
      lagValue: link.lagValue,
      lagUnit: link.lagUnit,
    })),
    // This preview does not invent resources, budgets, baselines or a Data Date.
    resources: [],
    projectStart: dates[0] ?? null,
    projectFinish: dates[dates.length - 1] ?? null,
  };
}

export function createVisualDemoState(locale: string, workspace?: WorkspaceState): DemoState {
  const project = workspace ? liveProjectData(workspace) : null;
  return {
    window: "activities",
    activityId: project?.activities[0]?.id ?? "A1320",
    scale: "month",
    detailTab: "general",
    calendarMonth: 1,
    adminSection: "users",
    filter: "",
    groupBy: "wbs",
    columns: [...DEFAULT_COLUMNS],
    toolbars: TOOLBARS.map((bar) => bar.id),
    history: [],
    forward: [],
    detailsOpen: true,
    locale,
    project,
  };
}

type DemoRuntime = { state: DemoState };
const demoRuntimes = new WeakMap<HTMLElement, DemoRuntime>();
const demoBoundHosts = new WeakSet<HTMLElement>();

type ConnectorBox = { left: number; right: number; middle: number };

function boxOf(element: Element | null, origin: DOMRect): ConnectorBox | null {
  if (!element) return null;
  const rect = element.getBoundingClientRect();
  return { left: rect.left - origin.left, right: rect.right - origin.left, middle: rect.top - origin.top + rect.height / 2 };
}

// Orthogonal relationship line: forward links step through the gap between
// boxes, stacked links loop around the outside edge, so the path always starts
// and ends on a real box edge instead of a guessed percentage.
function routeLink(from: ConnectorBox, to: ConnectorBox, outward: 1 | -1): string {
  if (to.left >= from.right + 12) {
    const mid = (from.right + to.left) / 2;
    return `M ${from.right} ${from.middle} H ${mid} V ${to.middle} H ${to.left - 1}`;
  }
  if (from.left >= to.right + 12) {
    const mid = (to.right + from.left) / 2;
    return `M ${from.left} ${from.middle} H ${mid} V ${to.middle} H ${to.right + 1}`;
  }
  const edge = outward > 0 ? from.right : from.left;
  return `M ${edge} ${from.middle} h ${22 * outward} V ${to.middle} h ${-22 * outward}`;
}

// Connectors are measured from the painted boxes, so they stay correct at every
// width, in both text directions, without a second source of coordinates.
function layoutConnectors(root: HTMLElement): void {
  const rtl = root.querySelector<HTMLElement>(".cp-vd")?.dir === "rtl";
  const outward: 1 | -1 = rtl ? -1 : 1;
  const network = root.querySelector<HTMLElement>("[data-vd-network]");
  const networkSvg = network?.querySelector<SVGSVGElement>("[data-vd-netlinks]");
  if (network && networkSvg) {
    const origin = network.getBoundingClientRect();
    const paths = NETWORK_LINKS.map(([from, to]) => {
      const start = boxOf(network.querySelector(`[data-vd-node="${from}"]`), origin);
      const end = boxOf(network.querySelector(`[data-vd-node="${to}"]`), origin);
      if (!start || !end) return "";
      const critical = Boolean(
        ACTIVITIES.find((item) => item.id === from)?.critical && ACTIVITIES.find((item) => item.id === to)?.critical,
      );
      const marker = critical ? "cp-vd-net-arrow-critical" : "cp-vd-net-arrow";
      return `<path d="${routeLink(start, end, outward)}" class="${critical ? "is-critical" : ""}" marker-end="url(#${marker})"></path>`;
    }).join("");
    networkSvg.innerHTML = NETWORK_DEFS + paths;
  }
  const trace = root.querySelector<HTMLElement>("[data-vd-trace]");
  const traceSvg = trace?.querySelector<SVGSVGElement>("[data-vd-tracelinks]");
  if (trace && traceSvg) {
    const origin = trace.getBoundingClientRect();
    const selected = boxOf(trace.querySelector("[data-trace-selected]"), origin);
    const paths: string[] = [];
    if (selected) {
      const selectedId = trace.querySelector<HTMLElement>("[data-trace-selected]")?.dataset.traceSelected ?? "";
      const selectedCritical = Boolean(ACTIVITIES.find((item) => item.id === selectedId)?.critical);
      trace.querySelectorAll<HTMLElement>("[data-trace-pred]").forEach((node) => {
        const box = boxOf(node, origin);
        if (!box) return;
        const critical = selectedCritical && Boolean(ACTIVITIES.find((item) => item.id === node.dataset.tracePred)?.critical);
        paths.push(`<path d="${routeLink(box, selected, outward)}" class="${critical ? "is-critical" : ""}" marker-end="url(#${critical ? "cp-vd-net-arrow-critical" : "cp-vd-net-arrow"})"></path>`);
      });
      trace.querySelectorAll<HTMLElement>("[data-trace-succ]").forEach((node) => {
        const box = boxOf(node, origin);
        if (!box) return;
        const critical = selectedCritical && Boolean(ACTIVITIES.find((item) => item.id === node.dataset.traceSucc)?.critical);
        paths.push(`<path d="${routeLink(selected, box, outward)}" class="${critical ? "is-critical" : ""}" marker-end="url(#${critical ? "cp-vd-net-arrow-critical" : "cp-vd-net-arrow"})"></path>`);
      });
    }
    traceSvg.innerHTML = NETWORK_DEFS + paths.join("");
  }
}

export function mountVisualDemo(root: HTMLElement, state: DemoState): void {
  // Events are delegated once per host; every redraw replaces the markup but
  // keeps the same state object, so the demo never accumulates listeners.
  demoRuntimes.set(root, { state });
  root.innerHTML = renderVisualDemo(state);
  layoutConnectors(root);
  if (!demoBoundHosts.has(root)) {
    bind(root);
    demoBoundHosts.add(root);
    window.addEventListener("resize", () => layoutConnectors(root));
  }
}

function bind(root: HTMLElement): void {
  const runtime = demoRuntimes.get(root);
  if (!runtime) return;
  const state = runtime.state;
  const draw = (): void => {
    root.innerHTML = renderVisualDemo(state);
    layoutConnectors(root);
  };
  const openMenu = (id: string): void => {
    root.querySelectorAll<HTMLElement>("[data-vd-menu]").forEach((menu) => {
      const trigger = menu.querySelector<HTMLElement>(".cp-vd-menu-trigger");
      const popup = menu.querySelector<HTMLElement>(":scope > .cp-vd-popup");
      const selected = menu.dataset.vdMenu === id;
      trigger?.setAttribute("aria-expanded", selected ? "true" : "false");
      if (popup) popup.hidden = !selected;
    });
  };
  const closeMenus = (): void => openMenu("");
  const navigate = (id: DemoWindowId): void => {
    if (id === state.window) return;
    state.history.push(state.window);
    state.forward.length = 0;
    state.window = id;
    draw();
  };
  const showLiveNotice = (): void => {
    const existing = root.querySelector<HTMLElement>(".cp-vd-live-notice");
    existing?.remove();
    const notice = document.createElement("div");
    notice.className = "cp-vd-live-notice";
    notice.setAttribute("role", "status");
    notice.textContent = t(state.locale, "This command is not connected to the live project yet. No project data was changed.", "این فرمان هنوز به پروژهٔ واقعی متصل نیست؛ هیچ داده‌ای تغییر نکرد.");
    root.querySelector(".cp-vd")?.append(notice);
  };
  const openDialog = (name: string): void => {
    closeMenus();
    const liveSafeDialogs = new Set(["columns", "filters", "group-sort", "timescale", "bars", "bar-options", "font-row", "shortcuts", "about"]);
    if (state.project && !liveSafeDialogs.has(name)) { showLiveNotice(); return; }
    // Buttons and the dialog element share the same name marker, so the
    // lookup must target the <dialog> itself rather than the opening button.
    const dialog = root.querySelector<HTMLDialogElement>(`dialog.cp-vd-dialog[data-vd-dialog="${name}"]`);
    if (!dialog) return;
    if (typeof dialog.showModal === "function") dialog.showModal();
    else dialog.setAttribute("open", "");
  };
  const closeDialog = (dialog: HTMLDialogElement | null): void => {
    if (!dialog) return;
    if (typeof dialog.close === "function") dialog.close();
    else dialog.removeAttribute("open");
  };
  const run = (action: MenuAction | undefined): void => {
    if (!action || action.reason) return;
    if (state.project && action.command && !["back", "forward", "close-window", "undo", "redo", "noop"].includes(action.command) && !action.command.startsWith("toolbar:")) { showLiveNotice(); return; }
    if (state.project && action.window && !["projects", "wbs", "activities"].includes(action.window)) { showLiveNotice(); return; }
    if (action.window) { navigate(action.window); return; }
    if (action.dialog) { openDialog(action.dialog); return; }
    switch (action.command) {
      case "back": {
        const previous = state.history.pop();
        if (previous) { state.forward.push(state.window); state.window = previous; draw(); }
        return;
      }
      case "forward": {
        const next = state.forward.pop();
        if (next) { state.history.push(state.window); state.window = next; draw(); }
        return;
      }
      case "close-window": navigate("projects"); return;
      case "undo": case "redo": case "noop": return;
      default: {
        // Any toolbar name from the toolbar register can be shown or hidden.
        if (action.command?.startsWith("toolbar:")) {
          const id = action.command.slice(8);
          if (!TOOLBARS.some((bar) => bar.id === id)) return;
          state.toolbars = state.toolbars.includes(id) ? state.toolbars.filter((item) => item !== id) : [...state.toolbars, id];
          draw();
        }
        return;
      }
    }
  };

  root.addEventListener("click", (event) => {
    const target = event.target as HTMLElement | null;
    if (!target || typeof target.closest !== "function") return;

    const trigger = target.closest<HTMLElement>(".cp-vd-menu-trigger");
    if (trigger) {
      event.stopPropagation();
      const menu = trigger.parentElement;
      const expanded = trigger.getAttribute("aria-expanded") === "true";
      openMenu(expanded ? "" : menu?.dataset.vdMenu ?? "");
      return;
    }
    const submenu = target.closest<HTMLElement>("[data-vd-submenu]");
    if (submenu) {
      const popup = submenu.parentElement?.querySelector<HTMLElement>(".cp-vd-subpopup");
      if (popup) popup.hidden = !popup.hidden;
      return;
    }
    const actionTarget = target.closest<HTMLElement>("[data-vd-action]");
    if (actionTarget) {
      closeMenus();
      try { run(JSON.parse(actionTarget.dataset.vdAction ?? "{}") as MenuAction); } catch { /* malformed action */ }
      return;
    }
    const tab = target.closest<HTMLElement>("[data-vd-window]");
    if (tab?.dataset.vdWindow) { navigate(tab.dataset.vdWindow as DemoWindowId); return; }
    const scale = target.closest<HTMLElement>("[data-vd-scale]");
    if (scale?.dataset.vdScale) {
      state.scale = scale.dataset.vdScale as DemoState["scale"];
      draw();
      return;
    }
    const calPrev = target.closest<HTMLElement>("[data-vd-cal-prev]");
    if (calPrev) { state.calendarMonth = Math.max(0, state.calendarMonth - 1); draw(); return; }
    const calNext = target.closest<HTMLElement>("[data-vd-cal-next]");
    if (calNext) { state.calendarMonth = Math.min(CAL_MONTHS.length - 1, state.calendarMonth + 1); draw(); return; }
    const adminSection = target.closest<HTMLElement>("[data-vd-admin]");
    if (adminSection?.dataset.vdAdmin) { state.adminSection = adminSection.dataset.vdAdmin; draw(); return; }
    const activity = target.closest<HTMLElement>("[data-vd-activity]");
    if (activity?.dataset.vdActivity) {
      state.activityId = activity.dataset.vdActivity;
      draw();
      return;
    }
    const detailTab = target.closest<HTMLElement>("[data-vd-dtab]");
    if (detailTab?.dataset.vdDtab) {
      state.detailTab = detailTab.dataset.vdDtab;
      const panel = root.querySelector<HTMLElement>("[data-vd-dpanel]");
      root.querySelectorAll<HTMLElement>("[data-vd-dtab]").forEach((button) => {
        button.classList.toggle("is-active", button.dataset.vdDtab === state.detailTab);
        button.setAttribute("aria-selected", button.dataset.vdDtab === state.detailTab ? "true" : "false");
      });
      const temp = document.createElement("div");
      temp.innerHTML = renderDetails(state);
      if (panel) panel.innerHTML = temp.querySelector<HTMLElement>("[data-vd-dpanel]")?.innerHTML ?? "";
      return;
    }
    const detailsToggle = target.closest<HTMLElement>("[data-vd-details-toggle]");
    if (detailsToggle) { state.detailsOpen = !state.detailsOpen; draw(); return; }
    const prev = target.closest<HTMLElement>("[data-vd-prev]");
    if (prev?.dataset.vdPrev) { state.activityId = prev.dataset.vdPrev; draw(); return; }
    const next = target.closest<HTMLElement>("[data-vd-next]");
    if (next?.dataset.vdNext) { state.activityId = next.dataset.vdNext; draw(); return; }
    const command = target.closest<HTMLElement>("[data-vd-command]");
    if (command?.dataset.vdCommand) { run({ command: command.dataset.vdCommand }); return; }
    const exit = target.closest<HTMLElement>("[data-vd-exit]");
    if (exit) {
      const url = new URL(window.location.href);
      if (state.project) url.searchParams.set("view", "classic"); else url.searchParams.delete("view");
      window.location.assign(url.toString());
      return;
    }
    // Only buttons open dialogs; the <dialog> element itself also carries a
    // data-vd-dialog marker for closing and lookup.
    const dialogTarget = target.closest<HTMLElement>("button[data-vd-dialog]");
    if (dialogTarget?.dataset.vdDialog) { openDialog(dialogTarget.dataset.vdDialog); return; }
    const close = target.closest<HTMLElement>("[data-vd-close]");
    if (close) { closeDialog(close.closest<HTMLDialogElement>("dialog")); return; }
    const reset = target.closest<HTMLElement>("[data-vd-default]");
    if (reset) {
      const dialog = reset.closest<HTMLDialogElement>("dialog");
      closeDialog(dialog);
      state.filter = "";
      state.groupBy = "wbs";
      state.scale = "month";
      state.columns = [...DEFAULT_COLUMNS];
      state.detailTab = "general";
      state.detailsOpen = true;
      draw();
      return;
    }
    if (!target.closest(".cp-vd-menu")) closeMenus();
  });

  root.addEventListener("submit", (event) => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement) || !form.dataset.vdForm) return;
    event.preventDefault();
    const name = form.dataset.vdForm;
    const data = new FormData(form);
    if (name === "columns") {
      state.columns = ACTIVITY_COLUMNS.filter((column) => data.has(column.id)).map((column) => column.id);
      if (!state.columns.length) state.columns = [...DEFAULT_COLUMNS];
    }
    if (name === "filters" || name === "find") state.filter = String(data.get("filter") ?? "");
    if (name === "group-sort") state.groupBy = data.get("group") === "none" ? "none" : "wbs";
    if (name === "timescale") {
      const scale = String(data.get("scale") ?? "");
      if (["day", "week", "month", "quarter", "year"].includes(scale)) state.scale = scale as DemoState["scale"];
    }
    closeDialog(form.closest<HTMLDialogElement>("dialog"));
    draw();
  });

  root.addEventListener("change", (event) => {
    const target = event.target as HTMLElement | null;
    if (!target || target.getAttribute("type") !== "checkbox") return;
    const column = target.getAttribute("data-vd-column");
    if (!column) return;
    const checked = (target as HTMLInputElement).checked;
    state.columns = checked ? [...state.columns, column] : state.columns.filter((id) => id !== column);
    // Keep the canonical order regardless of click order.
    state.columns = ACTIVITY_COLUMNS.filter((item) => state.columns.includes(item.id)).map((item) => item.id);
    draw();
    openDialog("columns");
  });

  root.addEventListener("scroll", (event) => {
    // The table and the Gantt scroll as one vertical surface, like the desktop
    // product: whichever pane the pointer is over drives the other.
    const pane = event.target;
    if (!(pane instanceof HTMLElement) || !pane.classList.contains("cp-vd-pane")) return;
    const panes = root.querySelectorAll<HTMLElement>(".cp-vd-pane");
    const other = panes[0] === pane ? panes[1] : panes[0];
    if (other && other.scrollTop !== pane.scrollTop) other.scrollTop = pane.scrollTop;
  }, true);

  root.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeMenus();
  });
}
