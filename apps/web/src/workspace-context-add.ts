/**
 * Contextual "Add" commands for the right-hand command rail.
 *
 * Every entry maps to a stable `DesktopCommand` id that the workspace shell
 * already dispatches, so the rail, the toolbar and the application menu run the
 * same command instead of three separate implementations. An entry that the
 * current window, selection, permission or stored data cannot support stays
 * visible with an explicit reason; nothing here invents a create service.
 */
import type { WorkspaceMenuKey } from "./workspace-model.js";
import type { WorkspaceIconName } from "./workspace-icons.js";

export type ContextAddLabel = { en: string; fa: string };

export type ContextAddItem = {
  /** Stable desktop command id; never a window-local callback name. */
  command: string;
  label: ContextAddLabel;
  icon: WorkspaceIconName;
  disabledReason?: ContextAddLabel;
};

export type ContextAddState = {
  activeMenu: WorkspaceMenuKey;
  /** Planner or project administrator, derived from the authenticated session. */
  canWrite: boolean;
  hasWbs: boolean;
  hasSelectedActivity: boolean;
  hasCalendarCatalog: boolean;
};

const WRITE_REQUIRED: ContextAddLabel = {
  en: "Requires the project planner or administrator role.",
  fa: "به نقش برنامه‌ریز یا مدیر پروژه نیاز دارد.",
};
const WBS_REQUIRED: ContextAddLabel = {
  en: "Add a WBS element before creating activities.",
  fa: "پیش از ایجاد فعالیت، یک عنصر WBS اضافه کنید.",
};
const ACTIVITY_REQUIRED: ContextAddLabel = {
  en: "Select an activity in the register first.",
  fa: "ابتدا یک فعالیت را در فهرست انتخاب کنید.",
};
const BASE_CALENDAR_REQUIRED: ContextAddLabel = {
  en: "A base calendar must exist before a calendar can be created.",
  fa: "پیش از ایجاد تقویم، باید یک تقویم پایه وجود داشته باشد.",
};

function item(
  command: string,
  label: ContextAddLabel,
  icon: WorkspaceIconName,
  blocked?: ContextAddLabel,
): ContextAddItem {
  return blocked ? { command, label, icon, disabledReason: blocked } : { command, label, icon };
}

const ADD_WBS = item("project.add-wbs", { en: "Add WBS element", fa: "افزودن عنصر WBS" }, "wbs");
const ADD_ACTIVITY = item("project.add-activity", { en: "Add activity", fa: "افزودن فعالیت" }, "plus");
const ADD_RELATIONSHIP = item("edit.link", { en: "Add relationship", fa: "افزودن رابطه" }, "link");
const ASSIGN_RESOURCES = item("activity.assign-resources", { en: "Assign resources", fa: "تخصیص منابع" }, "assignment");

const MODULE_CREATES: Partial<Record<WorkspaceMenuKey, ContextAddItem>> = {
  resources: item("resource.create", { en: "New resource", fa: "منبع جدید" }, "resource"),
  assignments: item("assignment.create", { en: "New assignment", fa: "تخصیص جدید" }, "assignment"),
  roles: item("role.create", { en: "New role", fa: "نقش جدید" }, "roles"),
  calendars: item("calendar.create", { en: "New calendar", fa: "تقویم جدید" }, "calendar"),
  documents: item("document.create", { en: "New document", fa: "سند جدید" }, "documents"),
  risks: item("risk.create", { en: "New risk", fa: "ریسک جدید" }, "risks"),
  issues: item("issue.create", { en: "New issue", fa: "مسئله جدید" }, "issues"),
  expenses: item("expense.create", { en: "New expense", fa: "هزینه جدید" }, "expense"),
  thresholds: item("threshold.create", { en: "New threshold", fa: "آستانه جدید" }, "thresholds"),
};

export function contextAddCommands(state: ContextAddState): readonly ContextAddItem[] {
  const items: ContextAddItem[] = [];
  const writeBlocked = state.canWrite ? undefined : WRITE_REQUIRED;

  if (state.activeMenu === "schedule") {
    items.push(
      item("project.add-activity", ADD_ACTIVITY.label, ADD_ACTIVITY.icon, writeBlocked ?? (state.hasWbs ? undefined : WBS_REQUIRED)),
      item(
        "edit.link",
        ADD_RELATIONSHIP.label,
        ADD_RELATIONSHIP.icon,
        writeBlocked ?? (state.hasSelectedActivity ? undefined : ACTIVITY_REQUIRED),
      ),
    );
  }

  if (state.activeMenu === "wbs" || state.activeMenu === "project") {
    items.push(
      item("project.add-wbs", ADD_WBS.label, ADD_WBS.icon, writeBlocked),
      item("project.add-activity", ADD_ACTIVITY.label, ADD_ACTIVITY.icon, writeBlocked ?? (state.hasWbs ? undefined : WBS_REQUIRED)),
    );
  }

  const moduleCreate = MODULE_CREATES[state.activeMenu];
  if (moduleCreate) {
    const blocked =
      writeBlocked ??
      (state.activeMenu === "calendars" && !state.hasCalendarCatalog ? BASE_CALENDAR_REQUIRED : undefined);
    items.push(item(moduleCreate.command, moduleCreate.label, moduleCreate.icon, blocked));
  }

  if (state.activeMenu === "resources" || state.activeMenu === "assignments") {
    items.push(
      item(
        "activity.assign-resources",
        ASSIGN_RESOURCES.label,
        ASSIGN_RESOURCES.icon,
        writeBlocked ?? (state.hasSelectedActivity ? undefined : ACTIVITY_REQUIRED),
      ),
    );
  }

  // Windows without a real create service return no entries. The rail keeps the
  // Add button and shows an explicit empty state instead of inventing commands.
  return items;
}
