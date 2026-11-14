import type { DesktopCommand, LocalizedLabel } from "./workspace-desktop-shell.js";
import type { WorkspaceMenuKey } from "./workspace-model.js";
import type { WorkspaceIconName } from "./workspace-icons.js";

/**
 * One authoritative command registry for both tool rails.
 *
 * A command is defined exactly once. A definition may be placed in more than
 * one toolbar family (Version 26 repeats standard commands across toolbars),
 * but the id, label, icon, target and enabled rules never diverge because both
 * rails read this table.
 */

export type ToolbarRailId = "left" | "right" | "floating";

export type ToolbarFamilyDefinition = {
  id: string;
  label: LocalizedLabel;
  rail: Exclude<ToolbarRailId, "floating">;
  /** Shown in the Customize dialog and the toolbar context menu. */
  description: LocalizedLabel;
};

export const TOOLBAR_FAMILIES: readonly ToolbarFamilyDefinition[] = [
  // Left rail: navigation destinations and creation verbs. The rail is a tool
  // rail, not a hard-coded menu: every entry below is a registry command.
  { id: "navigation", rail: "left", label: { en: "Navigation", fa: "پیمایش" }, description: { en: "Open project windows", fa: "بازکردن پنجره‌های پروژه" } },
  { id: "project", rail: "left", label: { en: "Project", fa: "پروژه" }, description: { en: "Project-level actions", fa: "اقدامات سطح پروژه" } },
  { id: "planning", rail: "left", label: { en: "Planning", fa: "برنامه‌ریزی" }, description: { en: "Schedule, WBS and activity planning", fa: "زمان‌بندی، WBS و برنامه‌ریزی فعالیت" } },
  { id: "resources-cost", rail: "left", label: { en: "Resources & Cost", fa: "منابع و هزینه" }, description: { en: "Create resources, roles, expenses and thresholds", fa: "ایجاد منابع، نقش‌ها، هزینه‌ها و آستانه‌ها" } },
  { id: "information", rail: "left", label: { en: "Information", fa: "اطلاعات" }, description: { en: "Documents, risks and issues", fa: "اسناد، ریسک‌ها و مسائل" } },
  { id: "administration", rail: "left", label: { en: "CUBI Administration", fa: "مدیریت CUBI" }, description: { en: "Forms, preferences and administration", fa: "فرم‌ها، ترجیحات و مدیریت" } },

  // Right rail: the Version 26 toolbar families.
  { id: "project-tools", rail: "right", label: { en: "Project Tools", fa: "ابزارهای پروژه" }, description: { en: "Interchange and project tooling", fa: "تبادل داده و ابزارهای پروژه" } },
  { id: "assign", rail: "right", label: { en: "Assign", fa: "تخصیص" }, description: { en: "Assign resources and roles", fa: "تخصیص منابع و نقش‌ها" } },
  { id: "edit", rail: "right", label: { en: "Edit", fa: "ویرایش" }, description: { en: "Selection, linking and layout history", fa: "انتخاب، پیوند و تاریخچهٔ چیدمان" } },
  { id: "layout", rail: "right", label: { en: "Layout", fa: "چیدمان" }, description: { en: "Layout, columns, bars and preferences", fa: "چیدمان، ستون‌ها، میله‌ها و ترجیحات" } },
  { id: "enterprise", rail: "right", label: { en: "Enterprise", fa: "سازمان" }, description: { en: "Enterprise-wide administration", fa: "مدیریت در سطح سازمان" } },
  { id: "print", rail: "right", label: { en: "Print", fa: "چاپ" }, description: { en: "Print the current view", fa: "چاپ نمای جاری" } },
  { id: "action", rail: "right", label: { en: "Action", fa: "اقدام" }, description: { en: "Contextual workspace actions", fa: "اقدامات زمینه‌ای محیط کار" } },
  { id: "administrator", rail: "right", label: { en: "Administrator", fa: "مدیر" }, description: { en: "User and workspace administration", fa: "مدیریت کاربر و محیط کار" } },
  { id: "bottom-layout", rail: "right", label: { en: "Bottom Layout", fa: "چیدمان پایین" }, description: { en: "Choose the bottom pane", fa: "انتخاب پنل پایین" } },
  { id: "display", rail: "right", label: { en: "Display", fa: "نمایش" }, description: { en: "Zoom, hierarchy and chart display", fa: "بزرگ‌نمایی، سلسله‌مراتب و نمایش نمودار" } },
  { id: "find", rail: "right", label: { en: "Find", fa: "یافتن" }, description: { en: "Find and select activities", fa: "یافتن و انتخاب فعالیت‌ها" } },
  { id: "dictionaries", rail: "right", label: { en: "Dictionaries", fa: "واژه‌نامه‌ها" }, description: { en: "Codes and user-defined fields", fa: "کدها و فیلدهای سفارشی" } },
  { id: "publish", rail: "right", label: { en: "Publish", fa: "انتشار" }, description: { en: "Publish the project view", fa: "انتشار نمای پروژه" } },
  { id: "standard-reports", rail: "right", label: { en: "Standard Reports", fa: "گزارش‌های استاندارد" }, description: { en: "Reports and tracking", fa: "گزارش‌ها و رهگیری" } },
  { id: "tools", rail: "right", label: { en: "Tools", fa: "ابزارها" }, description: { en: "Schedule, formula and data tools", fa: "زمان‌بندی، فرمول و ابزارهای داده" } },
  { id: "activity", rail: "right", label: { en: "Activity", fa: "فعالیت" }, description: { en: "Edit the selected activity", fa: "ویرایش فعالیت انتخاب‌شده" } },
  { id: "critical-check", rail: "right", label: { en: "Critical Check", fa: "بررسی بحرانی" }, description: { en: "Critical path hierarchy and scheduling", fa: "سلسله‌مراتب مسیر بحرانی و زمان‌بندی" } },
  { id: "schedule", rail: "right", label: { en: "Schedule", fa: "زمان‌بندی" }, description: { en: "Run and inspect the schedule", fa: "اجرا و بررسی زمان‌بندی" } },
];

export const TOOLBAR_FAMILY_IDS: readonly string[] = TOOLBAR_FAMILIES.map((family) => family.id);

export function toolbarFamily(id: string): ToolbarFamilyDefinition | null {
  return TOOLBAR_FAMILIES.find((family) => family.id === id) ?? null;
}

export type ToolbarCapabilities = {
  hasWbs: boolean;
  hasSelectedActivity: boolean;
  hasMultiSelection: boolean;
  hasActivities: boolean;
  hasRelationships: boolean;
  hasLayout: boolean;
  canUndoLayout: boolean;
  canRedoLayout: boolean;
  groupByWbs: boolean;
  canAdminister: boolean;
  canOpenFieldChooser: boolean;
};

export type ToolbarContext = {
  activeWindow: WorkspaceMenuKey;
  locale: string;
  capabilities: ToolbarCapabilities;
  detailsVisible?: boolean;
  ganttVisible?: boolean;
  lineNumbers?: boolean;
};

export type ToolbarCommandTarget =
  | { kind: "command"; command: DesktopCommand }
  | { kind: "window"; window: WorkspaceMenuKey }
  | { kind: "rail"; action: string }
  | { kind: "fullscreen" };

export type ToolbarCommandAction =
  | "move"
  | "hide"
  | "rename"
  | "style"
  | "group"
  | "reset";

export type ToolbarCommandDefinition = {
  id: string;
  label: LocalizedLabel;
  tooltip: LocalizedLabel;
  icon: WorkspaceIconName;
  families: readonly string[];
  target: ToolbarCommandTarget;
  /** Windows where the command is meaningful; elsewhere it is disabled with a reason. */
  windows?: readonly WorkspaceMenuKey[];
  /** Only a session with the administrator role can use the command. */
  adminOnly?: boolean;
  defaultVisible: boolean;
  active?: (context: ToolbarContext) => boolean;
  /** A null result means enabled. */
  disabledReason?: (context: ToolbarContext) => LocalizedLabel | null;
  /** Customizations the command supports in its icon context menu. */
  actions?: readonly ToolbarCommandAction[];
};

const ALL_ACTIONS: readonly ToolbarCommandAction[] = ["move", "hide", "rename", "style", "group", "reset"];

const reason = (en: string, fa: string): LocalizedLabel => ({ en, fa });
const always = (label: LocalizedLabel) => () => label;

// Honest, stable reasons reused by several commands. A disabled button always
// says why it cannot run; none of these commands is presented as operational.
const R = {
  selection: reason("Select an activity in the grid first", "ابتدا یک فعالیت را در جدول انتخاب کنید"),
  activities: reason("Load activities in the Activities window first", "ابتدا فعالیت‌ها را در پنجرهٔ فعالیت‌ها بارگذاری کنید"),
  clipboard: reason("The activity clipboard is not connected to this workspace yet", "کلیپ‌بورد فعالیت هنوز به این محیط کار متصل نشده است"),
  deleteActivity: reason("Deleting activities is not available in this workspace yet", "حذف فعالیت هنوز در این محیط کار در دسترس نیست"),
  fillDown: reason("Fill Down needs editable table cells; edit each activity in Activity Details", "پرکردن به پایین به سلول‌های ویرایش‌پذیر نیاز دارد؛ هر فعالیت را در جزئیات فعالیت ویرایش کنید"),
  dissolve: reason("Dissolving a WBS band has no server contract; move its activities and delete the band instead", "انحلال باند WBS قرارداد سمت سرور ندارد؛ فعالیت‌ها را منتقل و باند را حذف کنید"),
  baseline: reason("Baseline management is not available in this workspace yet", "مدیریت خط مبنا هنوز در این محیط کار در دسترس نیست"),
  additional: reason("CUBI keeps one canonical Activities window per project; use the window tabs instead of a second table", "CUBI برای هر پروژه یک پنجرهٔ فعالیت متعارف نگه می‌دارد؛ به‌جای جدول دوم از زبانه‌های پنجره استفاده کنید"),
  users: reason("User administration is not available in this workspace yet", "مدیریت کاربران هنوز در این محیط کار در دسترس نیست"),
  security: reason("Security profiles are not available in this workspace yet", "پروفایل‌های امنیتی هنوز در این محیط کار در دسترس نیستند"),
  currencies: reason("Currency administration is not available in this workspace yet", "مدیریت ارزها هنوز در این محیط کار در دسترس نیست"),
  audit: reason("The audit history is not available in this workspace yet", "تاریخچهٔ ممیزی هنوز در این محیط کار در دسترس نیست"),
  udfs: reason("Enterprise user-defined fields are not available in this workspace yet", "فیلدهای سفارشی سازمانی هنوز در این محیط کار در دسترس نیستند"),
  codes: reason("Enterprise code dictionaries are not available in this workspace yet", "واژه‌نامه‌های کد سازمانی هنوز در این محیط کار در دسترس نیستند"),
  reports: reason("Report generation is not available in this workspace yet", "ساخت گزارش هنوز در این محیط کار در دسترس نیست"),
  publish: reason("Publishing requires the report renderer, which is not connected", "انتشار به موتور گزارش نیاز دارد که متصل نیست"),
  pageSetup: reason("Printing uses the browser print dialog; a separate page-setup surface is not implemented", "چاپ از دیالوگ چاپ مرورگر استفاده می‌کند؛ سطح تنظیم صفحه جداگانه پیاده‌سازی نشده است"),
  findNext: reason("Find Next needs the current result set; use Find in the activity table", "یافتن مورد بعدی به نتیجهٔ فیلتر جاری نیاز دارد؛ از یافتن در جدول فعالیت استفاده کنید"),
  admin: reason("Requires the project administrator role", "به نقش مدیر پروژه نیاز دارد"),
  activitiesWindow: reason("Switch to the Activities window to use this command", "برای استفاده از این فرمان به پنجرهٔ فعالیت‌ها بروید"),
  layout: reason("This project has no saved layout to write", "این پروژه چیدمان ذخیره‌شده‌ای برای نوشتن ندارد"),
  fields: reason("No saved field layout is available for this project", "چیدمان فیلد ذخیره‌شده‌ای برای این پروژه در دسترس نیست"),
  undo: reason("No earlier layout change is available", "تغییر قبلی چیدمان در دسترس نیست"),
  redo: reason("No layout change to reapply", "تغییری برای اعمال دوباره وجود ندارد"),
  wbs: reason("Create a WBS element before adding activities", "پیش از افزودن فعالیت، یک عنصر WBS بسازید"),
  wbsGroup: reason("Group the activity table by WBS to use hierarchy commands", "برای فرمان‌های سلسله‌مراتب، جدول فعالیت را بر اساس WBS گروه‌بندی کنید"),
  multi: reason("Select at least two activities to unlink", "برای قطع پیوند، دست‌کم دو فعالیت را انتخاب کنید"),
  relationships: reason("This project has no persisted relationships", "این پروژه رابطهٔ ذخیره‌شده‌ای ندارد"),
};

const scheduleOnly: readonly WorkspaceMenuKey[] = ["schedule"];
const chartWindows: readonly WorkspaceMenuKey[] = ["schedule", "wbs"];

function whenWindow(windows?: readonly WorkspaceMenuKey[], base?: (context: ToolbarContext) => LocalizedLabel | null) {
  return (context: ToolbarContext): LocalizedLabel | null => {
    if (windows && !windows.includes(context.activeWindow)) return R.activitiesWindow;
    return base ? base(context) : null;
  };
}

const cmd = (
  id: string,
  label: LocalizedLabel,
  icon: WorkspaceIconName,
  families: readonly string[],
  target: ToolbarCommandTarget,
  extra: Partial<ToolbarCommandDefinition> = {},
): ToolbarCommandDefinition => ({
  id,
  label,
  tooltip: extra.tooltip ?? label,
  icon,
  families,
  target,
  defaultVisible: true,
  actions: ALL_ACTIONS,
  ...extra,
});

const win = (window: WorkspaceMenuKey): ToolbarCommandTarget => ({ kind: "window", window });
const run = (command: DesktopCommand): ToolbarCommandTarget => ({ kind: "command", command });
const rail = (action: string): ToolbarCommandTarget => ({ kind: "rail", action });

export const TOOLBAR_COMMANDS: readonly ToolbarCommandDefinition[] = [
  // Left rail — navigation destinations.
  cmd("nav.all", { en: "All Menus", fa: "همهٔ منوها" }, "group", ["navigation"], rail("navigation"), { tooltip: { en: "Open every menu and category", fa: "بازکردن همهٔ منوها و دسته‌ها" } }),
  cmd("nav.projects", { en: "Projects", fa: "پروژه‌ها" }, "portfolio", ["navigation"], win("project")),
  cmd("nav.wbs", { en: "WBS", fa: "ساختار شکست" }, "wbs", ["navigation"], win("wbs")),
  cmd("nav.activities", { en: "Activities", fa: "فعالیت‌ها" }, "activity", ["navigation"], win("schedule")),
  cmd("nav.progress", { en: "Progress", fa: "پیشرفت" }, "progress", ["navigation"], win("progress")),
  cmd("nav.resources", { en: "Resources", fa: "منابع" }, "resource", ["navigation"], win("resources")),
  cmd("nav.assignments", { en: "Assignments", fa: "تخصیص‌ها" }, "assignment", ["navigation"], win("assignments")),
  cmd("nav.calendars", { en: "Calendars", fa: "تقویم‌ها" }, "calendar", ["navigation"], win("calendars")),
  cmd("nav.roles", { en: "Roles", fa: "نقش‌ها" }, "roles", ["navigation"], win("roles")),
  cmd("nav.cost", { en: "Cost", fa: "هزینه" }, "money", ["navigation"], win("cost")),
  cmd("nav.expenses", { en: "Expenses", fa: "هزینه‌ها" }, "expense", ["navigation"], win("expenses")),
  cmd("nav.documents", { en: "Documents", fa: "اسناد" }, "documents", ["navigation"], win("documents")),
  cmd("nav.reports", { en: "Reports", fa: "گزارش‌ها" }, "reports", ["navigation"], win("reports")),
  cmd("nav.tracking", { en: "Tracking", fa: "رهگیری" }, "tracking", ["navigation"], win("tracking")),
  cmd("nav.risks", { en: "Risks", fa: "ریسک‌ها" }, "risks", ["navigation"], win("risks")),
  cmd("nav.issues", { en: "Issues", fa: "مسائل" }, "issues", ["navigation"], win("issues")),
  cmd("nav.thresholds", { en: "Thresholds", fa: "آستانه‌ها" }, "thresholds", ["navigation"], win("thresholds")),
  cmd("nav.settings", { en: "Settings", fa: "تنظیمات" }, "settings", ["navigation"], win("settings")),
  cmd("nav.administration", { en: "Administration", fa: "مدیریت" }, "administration", ["navigation"], win("administration")),
  cmd("nav.exchange", { en: "Import / Export", fa: "ورود / خروجی" }, "exchange", ["navigation"], win("exchange")),
  cmd("nav.backup", { en: "Backup / Recovery", fa: "پشتیبان‌گیری / بازیابی" }, "backup", ["navigation"], win("backup")),

  // Left rail — project and planning actions.
  cmd("project.properties", { en: "Project Properties", fa: "مشخصات پروژه" }, "project", ["project"], run("project.settings")),
  cmd("project.interchange", { en: "Import / Export", fa: "ورود / خروجی" }, "exchange", ["project-tools", "tools", "project"], run("project.interchange")),
  cmd("project.baselines", { en: "Baselines", fa: "خطوط مبنا" }, "baseline", ["project-tools", "project"], run("workspace.refresh"), { disabledReason: always(R.baseline) }),
  cmd("project.additional-activities", { en: "Additional Activities View", fa: "نمای فعالیت‌های بیشتر" }, "activity", ["project-tools"], run("workspace.refresh"), { disabledReason: always(R.additional) }),
  cmd("planning.add-wbs", { en: "Add WBS", fa: "افزودن WBS" }, "tree", ["planning", "activity"], run("project.add-wbs")),
  cmd("planning.add-activity", { en: "Add Activity", fa: "افزودن فعالیت" }, "plus", ["planning", "activity"], run("project.add-activity"), { windows: scheduleOnly, disabledReason: whenWindow(scheduleOnly, (context) => (context.capabilities.hasWbs ? null : R.wbs)) }),
  cmd("planning.collapse-to", { en: "Collapse To", fa: "بستن تا" }, "collapseTo", ["planning", "critical-check"], run("view.collapse-to"), { windows: chartWindows, disabledReason: whenWindow(chartWindows, (context) => (context.capabilities.hasWbs && context.capabilities.groupByWbs ? null : R.wbsGroup)) }),

  // Left rail — creation verbs.
  cmd("resources.create", { en: "New Resource", fa: "منبع جدید" }, "resource", ["resources-cost", "assign"], run("resource.create")),
  cmd("assignments.create", { en: "New Assignment", fa: "تخصیص جدید" }, "assignment", ["resources-cost", "assign"], run("assignment.create")),
  cmd("roles.create", { en: "New Role", fa: "نقش جدید" }, "roles", ["resources-cost"], run("role.create")),
  cmd("expenses.create", { en: "New Expense", fa: "هزینهٔ جدید" }, "expense", ["resources-cost"], run("expense.create")),
  cmd("thresholds.create", { en: "New Threshold", fa: "آستانهٔ جدید" }, "thresholds", ["resources-cost"], run("threshold.create")),
  cmd("calendars.create", { en: "New Calendar", fa: "تقویم جدید" }, "calendar", ["resources-cost"], run("calendar.create")),
  cmd("documents.create", { en: "New Document", fa: "سند جدید" }, "documents", ["information"], run("document.create")),
  cmd("risks.create", { en: "New Risk", fa: "ریسک جدید" }, "risks", ["information"], run("risk.create")),
  cmd("issues.create", { en: "New Issue", fa: "مسئلهٔ جدید" }, "issues", ["information"], run("issue.create")),
  cmd("forms.open", { en: "Form Builder", fa: "فرم‌ساز" }, "forms", ["tools", "administration"], run("forms.open")),

  // Right rail — Project Tools.
  cmd("tools.refresh", { en: "Refresh", fa: "به‌روزرسانی" }, "refresh", ["project-tools", "tools"], run("workspace.refresh"), { tooltip: { en: "Re-read the project from the server", fa: "خواندن دوبارهٔ پروژه از سرور" } }),

  // Right rail — Assign.
  cmd("assign.activity", { en: "Assign Resources", fa: "تخصیص منابع" }, "link", ["assign"], run("activity.assign-resources"), { windows: ["schedule", "resources", "assignments"], disabledReason: whenWindow(["schedule", "resources", "assignments"], (context) => (context.capabilities.hasSelectedActivity ? null : R.selection)) }),

  // Right rail — Edit.
  cmd("edit.undo", { en: "Undo", fa: "بازگردانی" }, "undo", ["edit"], run("edit.undo"), { disabledReason: (context) => (context.capabilities.canUndoLayout ? null : R.undo) }),
  cmd("edit.redo", { en: "Redo", fa: "تکرار" }, "redo", ["edit"], run("edit.redo"), { disabledReason: (context) => (context.capabilities.canRedoLayout ? null : R.redo) }),
  cmd("edit.select-all", { en: "Select All", fa: "انتخاب همه" }, "check", ["edit", "find"], run("edit.select-all"), { windows: scheduleOnly, disabledReason: whenWindow(scheduleOnly, (context) => (context.capabilities.hasActivities ? null : R.activities)) }),
  cmd("edit.link", { en: "Link", fa: "پیوند" }, "link", ["edit"], run("edit.link"), { windows: scheduleOnly, disabledReason: whenWindow(scheduleOnly, (context) => (context.capabilities.hasSelectedActivity ? null : R.selection)) }),
  cmd("edit.unlink", { en: "Unlink", fa: "قطع پیوند" }, "unlink", ["edit"], run("edit.unlink"), { windows: scheduleOnly, disabledReason: whenWindow(scheduleOnly, (context) => (!context.capabilities.hasMultiSelection ? R.multi : context.capabilities.hasRelationships ? null : R.relationships)) }),
  cmd("edit.fill-down", { en: "Fill Down", fa: "پرکردن به پایین" }, "fill", ["edit"], run("edit.select-all"), { windows: scheduleOnly, disabledReason: always(R.fillDown) }),
  cmd("edit.dissolve", { en: "Dissolve", fa: "انحلال" }, "dissolve", ["edit"], run("view.collapse-to"), { windows: chartWindows, disabledReason: always(R.dissolve) }),

  // Right rail — Layout.
  cmd("layout.open", { en: "Open Layout", fa: "بازکردن چیدمان" }, "folder", ["layout"], run("layout.open"), { windows: scheduleOnly, disabledReason: whenWindow(scheduleOnly, (context) => (context.capabilities.canOpenFieldChooser ? null : R.fields)) }),
  cmd("layout.save", { en: "Save Layout", fa: "ذخیرهٔ چیدمان" }, "save", ["layout"], run("layout.save"), { windows: scheduleOnly, disabledReason: whenWindow(scheduleOnly, (context) => (context.capabilities.hasLayout ? null : R.layout)) }),
  cmd("layout.save-as", { en: "Save Layout As", fa: "ذخیرهٔ چیدمان با نام" }, "saveAs", ["layout"], run("layout.save-as"), { windows: scheduleOnly, disabledReason: whenWindow(scheduleOnly, (context) => (context.capabilities.hasLayout ? null : R.layout)) }),
  cmd("layout.bars", { en: "Bars", fa: "میله‌ها" }, "bars", ["layout"], run("dialog.bars"), { windows: chartWindows }),
  cmd("layout.columns", { en: "Columns", fa: "ستون‌ها" }, "columns", ["layout"], run("view.fields"), { windows: scheduleOnly, disabledReason: whenWindow(scheduleOnly, (context) => (context.capabilities.canOpenFieldChooser ? null : R.fields)) }),
  cmd("layout.timescale", { en: "Timescale", fa: "مقیاس زمانی" }, "clock", ["layout"], run("dialog.timescale"), { windows: chartWindows }),
  cmd("layout.filters", { en: "Filters", fa: "فیلترها" }, "filter", ["layout"], run("dialog.filters"), { windows: scheduleOnly }),
  cmd("layout.group-sort", { en: "Group & Sort", fa: "گروه و ترتیب" }, "sort", ["layout"], run("dialog.group-sort"), { windows: scheduleOnly }),
  cmd("layout.group-wbs", { en: "Group by WBS", fa: "گروه‌بندی بر اساس WBS" }, "group", ["layout", "activity"], run("edit.group-wbs"), { windows: scheduleOnly, active: (context) => context.capabilities.groupByWbs }),
  cmd("layout.line-numbers", { en: "Line Numbers", fa: "شمارهٔ ردیف" }, "lineNumbers", ["layout"], run("view.line-numbers"), { windows: scheduleOnly, active: (context) => Boolean(context.lineNumbers) }),
  cmd("layout.font-row", { en: "Table Font", fa: "قلم جدول" }, "font", ["layout"], run("dialog.font-row"), { windows: scheduleOnly }),
  cmd("prefs.user", { en: "User Preferences", fa: "ترجیحات کاربر" }, "settings", ["layout", "administrator", "administration"], run("dialog.user-preferences")),

  // Right rail — Enterprise (all honest disabled entries).
  cmd("enterprise.users", { en: "Users", fa: "کاربران" }, "roles", ["enterprise"], run("admin.language"), { disabledReason: always(R.users), adminOnly: true }),
  cmd("enterprise.security", { en: "Security Profiles", fa: "پروفایل‌های امنیتی" }, "lock", ["enterprise"], run("admin.language"), { disabledReason: always(R.security), adminOnly: true }),
  cmd("enterprise.currencies", { en: "Currencies", fa: "ارزها" }, "money", ["enterprise"], run("admin.language"), { disabledReason: always(R.currencies), adminOnly: true }),
  cmd("enterprise.audit", { en: "Audit History", fa: "تاریخچهٔ ممیزی" }, "book", ["enterprise"], run("admin.language"), { disabledReason: always(R.audit), adminOnly: true }),
  cmd("enterprise.udfs", { en: "User-Defined Fields", fa: "فیلدهای سفارشی" }, "columns", ["enterprise", "dictionaries"], run("admin.language"), { disabledReason: always(R.udfs), adminOnly: true }),

  // Right rail — Print.
  cmd("print.print", { en: "Print", fa: "چاپ" }, "print", ["print", "standard-reports"], run("file.print")),
  cmd("print.page-setup", { en: "Page Setup", fa: "تنظیم صفحه" }, "file", ["print"], run("file.print"), { disabledReason: always(R.pageSetup) }),

  // Right rail — Action.
  cmd("action.comments", { en: "Comments", fa: "نظرات" }, "comment", ["action"], rail("comments")),
  cmd("action.notes", { en: "Notebook", fa: "دفترچه" }, "book", ["action"], rail("notebook")),
  cmd("action.details", { en: "Record Details", fa: "جزئیات رکورد" }, "details", ["action"], rail("details")),
  cmd("action.proposals", { en: "Suggested Actions", fa: "اقدامات پیشنهادی" }, "proposal", ["action"], rail("proposals")),
  cmd("action.assistant", { en: "CUBI Assistant", fa: "دستیار CUBI" }, "assistant", ["action"], rail("assistant")),
  cmd("action.help", { en: "Help", fa: "راهنما" }, "help", ["action"], rail("help")),

  // Right rail — Administrator.
  cmd("admin.language", { en: "Language", fa: "زبان" }, "language", ["administrator", "administration"], run("admin.language")),
  cmd("admin.calendar", { en: "Calendar Display", fa: "نمایش تقویم" }, "calendar", ["administrator"], run("admin.calendar")),
  cmd("admin.permissions", { en: "Permission Matrix", fa: "ماتریس دسترسی" }, "lock", ["administrator", "administration"], win("administration"), { adminOnly: true }),
  cmd("admin.categories", { en: "Categories", fa: "دسته‌ها" }, "group", ["administrator"], win("administration"), { adminOnly: true }),
  cmd("admin.settings", { en: "Administration", fa: "مدیریت" }, "administration", ["administrator"], win("settings"), { adminOnly: true }),

  // Right rail — Bottom Layout.
  cmd("bottom.details", { en: "Show Details", fa: "نمایش جزئیات" }, "details", ["bottom-layout"], run("view.bottom-details"), { windows: scheduleOnly, active: (context) => Boolean(context.detailsVisible) }),
  cmd("bottom.trace", { en: "Show Trace Logic", fa: "نمایش ردیابی منطق" }, "network", ["bottom-layout"], run("view.bottom-trace"), { windows: scheduleOnly }),
  cmd("bottom.usage-profile", { en: "Show Usage Profile", fa: "نمایش نمودار استفاده" }, "progress", ["bottom-layout"], run("view.bottom-usage-profile"), { windows: scheduleOnly }),
  cmd("bottom.usage-spreadsheet", { en: "Show Usage Spreadsheet", fa: "نمایش جدول استفاده" }, "table", ["bottom-layout"], run("view.bottom-usage-spreadsheet"), { windows: scheduleOnly }),
  cmd("bottom.none", { en: "Hide Details", fa: "پنهان‌کردن جزئیات" }, "close", ["bottom-layout"], run("view.bottom-none"), { windows: scheduleOnly }),

  // Right rail — Display.
  cmd("display.zoom-in", { en: "Zoom In", fa: "بزرگ‌نمایی" }, "zoomIn", ["display"], run("view.zoom-in"), { windows: chartWindows }),
  cmd("display.zoom-out", { en: "Zoom Out", fa: "کوچک‌نمایی" }, "zoomOut", ["display"], run("view.zoom-out"), { windows: chartWindows }),
  cmd("display.fit", { en: "Fit", fa: "تناسب" }, "fit", ["display"], run("view.fit"), { windows: chartWindows }),
  cmd("display.panels", { en: "Panels", fa: "پنل‌ها" }, "panels", ["display"], run("view.toggle-details"), { active: (context) => context.detailsVisible !== false }),
  cmd("display.gantt", { en: "Gantt Chart", fa: "نمودار گانت" }, "gantt", ["display"], run("view.toggle-gantt"), { windows: chartWindows, active: (context) => context.ganttVisible !== false }),
  cmd("display.expand-all", { en: "Expand All", fa: "بازکردن همه" }, "expand", ["display"], run("view.expand-all"), { windows: chartWindows, disabledReason: whenWindow(chartWindows, (context) => (context.capabilities.hasWbs && context.capabilities.groupByWbs ? null : R.wbsGroup)) }),
  cmd("display.collapse-all", { en: "Collapse All", fa: "بستن همه" }, "collapse", ["display"], run("view.collapse-all"), { windows: chartWindows, disabledReason: whenWindow(chartWindows, (context) => (context.capabilities.hasWbs && context.capabilities.groupByWbs ? null : R.wbsGroup)) }),
  cmd("display.collapse-to", { en: "Collapse To", fa: "بستن تا" }, "collapseTo", ["display", "critical-check"], run("view.collapse-to"), { windows: chartWindows, disabledReason: whenWindow(chartWindows, (context) => (context.capabilities.hasWbs && context.capabilities.groupByWbs ? null : R.wbsGroup)) }),
  cmd("display.fullscreen", { en: "Full Screen", fa: "تمام‌صفحه" }, "fullscreen", ["display"], { kind: "fullscreen" }),

  // Right rail — Find.
  cmd("find.find", { en: "Find", fa: "یافتن" }, "find", ["find"], run("edit.find"), { windows: scheduleOnly }),
  cmd("find.next", { en: "Find Next", fa: "یافتن مورد بعدی" }, "right", ["find"], run("edit.find"), { windows: scheduleOnly, disabledReason: always(R.findNext) }),

  // Right rail — Dictionaries.
  cmd("dict.activity-codes", { en: "Activity Codes", fa: "کدهای فعالیت" }, "columns", ["dictionaries"], run("admin.language"), { disabledReason: always(R.codes) }),
  cmd("dict.resource-codes", { en: "Resource Codes", fa: "کدهای منابع" }, "resource", ["dictionaries"], run("admin.language"), { disabledReason: always(R.codes) }),
  cmd("dict.project-codes", { en: "Project Codes", fa: "کدهای پروژه" }, "project", ["dictionaries"], run("admin.language"), { disabledReason: always(R.codes) }),

  // Right rail — Publish.
  cmd("publish.pdf", { en: "Publish to PDF", fa: "انتشار به PDF" }, "export", ["publish"], run("file.print"), { disabledReason: always(R.publish) }),
  cmd("publish.excel", { en: "Publish to Excel", fa: "انتشار به Excel" }, "excel", ["publish"], run("file.print"), { disabledReason: always(R.publish) }),
  cmd("publish.web", { en: "Publish to Web Site", fa: "انتشار به وب" }, "workspace", ["publish"], run("file.print"), { disabledReason: always(R.publish) }),

  // Right rail — Standard Reports.
  cmd("reports.open", { en: "Reports", fa: "گزارش‌ها" }, "reports", ["standard-reports"], win("reports")),
  cmd("reports.tracking", { en: "Tracking", fa: "رهگیری" }, "tracking", ["standard-reports"], win("tracking")),
  cmd("reports.wizard", { en: "Report Wizard", fa: "جادوگر گزارش" }, "file", ["standard-reports", "information"], run("admin.language"), { disabledReason: always(R.reports) }),

  // Right rail — Tools.
  cmd("tools.schedule", { en: "Schedule", fa: "زمان‌بندی" }, "calendar", ["tools", "critical-check", "schedule", "planning"], run("tools.run-schedule"), { tooltip: { en: "Run the schedule (F9)", fa: "اجرای زمان‌بندی (F9)" } }),
  cmd("tools.options", { en: "Schedule Options", fa: "تنظیمات زمان‌بندی" }, "settings", ["tools", "schedule"], run("project.schedule-options")),
  cmd("tools.formula", { en: "Formula Editor", fa: "ویرایشگر فرمول" }, "font", ["tools", "schedule"], run("tools.formula")),
  cmd("tools.reference", { en: "Scheduling Reference", fa: "مرجع زمان‌بندی" }, "book", ["tools", "schedule"], run("tools.reference")),

  // Right rail — Activity.
  cmd("activity.edit", { en: "Edit Activity", fa: "ویرایش فعالیت" }, "edit", ["activity"], run("project.edit-activity"), { windows: scheduleOnly, disabledReason: whenWindow(scheduleOnly, (context) => (context.capabilities.hasSelectedActivity ? null : R.selection)) }),
  cmd("activity.predecessors", { en: "Predecessors", fa: "پیش‌نیازها" }, "link", ["activity"], run("activity.predecessors"), { windows: scheduleOnly, disabledReason: whenWindow(scheduleOnly, (context) => (context.capabilities.hasSelectedActivity ? null : R.selection)) }),
  cmd("activity.successors", { en: "Successors", fa: "پس‌نیازها" }, "network", ["activity"], run("activity.successors"), { windows: scheduleOnly, disabledReason: whenWindow(scheduleOnly, (context) => (context.capabilities.hasSelectedActivity ? null : R.selection)) }),

  // Right rail — Critical Check.
  cmd("critical.expand-all", { en: "Expand All", fa: "بازکردن همه" }, "expand", ["critical-check"], run("view.expand-all"), { windows: chartWindows, disabledReason: whenWindow(chartWindows, (context) => (context.capabilities.hasWbs && context.capabilities.groupByWbs ? null : R.wbsGroup)) }),
  cmd("critical.collapse-all", { en: "Collapse All", fa: "بستن همه" }, "collapse", ["critical-check"], run("view.collapse-all"), { windows: chartWindows, disabledReason: whenWindow(chartWindows, (context) => (context.capabilities.hasWbs && context.capabilities.groupByWbs ? null : R.wbsGroup)) }),
];

export const TOOLBAR_COMMAND_IDS: readonly string[] = TOOLBAR_COMMANDS.map((command) => command.id);

export function toolbarCommand(id: string): ToolbarCommandDefinition | null {
  return TOOLBAR_COMMANDS.find((command) => command.id === id) ?? null;
}

export function toolbarCommandsForFamily(familyId: string): ToolbarCommandDefinition[] {
  return TOOLBAR_COMMANDS.filter((command) => command.families.includes(familyId));
}

/** Runtime permission gate: hidden admin commands are disabled, never silently executed. */
export function toolbarCommandDisabledReason(
  command: ToolbarCommandDefinition,
  context: ToolbarContext,
): LocalizedLabel | null {
  if (command.adminOnly && !context.capabilities.canAdminister) return R.admin;
  return command.disabledReason ? command.disabledReason(context) : null;
}

export function toolbarCommandActive(command: ToolbarCommandDefinition, context: ToolbarContext): boolean {
  try {
    return Boolean(command.active?.(context));
  } catch {
    return false;
  }
}
