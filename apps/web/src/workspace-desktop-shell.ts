import type { WorkspaceMenuKey } from "./workspace-model.js";
import { renderLayoutBar, renderTitleBar, type ChromeLayoutState, type ChromeProjectContext } from "./workspace-chrome.js";
import { defaultLayoutPatch, readLayoutPatch, renderLayoutDialogs, type DesktopLayoutPatch, type DesktopSortColumn } from "./workspace-dialogs.js";
import { workspaceIcon } from "./workspace-icons.js";
import { translateWorkspaceUiText } from "./workspace-localization.js";

/**
 * Desktop chrome for the professional workspace: the application menu bar, the
 * main command toolbar, window tabs and the shortcuts/about dialogs. Every
 * entry either opens a real workspace surface, runs a command the shell is
 * given, or states why it is unavailable. Nothing is rendered as decoration.
 */
export type LocalizedLabel = { en: string; fa: string };

export type DesktopCommand =
  | "forms.open"
  | "project.settings"
  | "project.close"
  | "project.interchange"
  | "file.print"
  | "edit.undo"
  | "edit.redo"
  | "edit.find"
  | "view.filters"
  | "edit.group-wbs"
  | "edit.sort-toggle"
  | "project.add-wbs"
  | "project.add-activity"
  | "project.edit-activity"
  | "project.schedule-options"
  | "activity.assign-resources"
  | "activity.predecessors"
  | "activity.successors"
  | "view.fields"
  | "view.wbs-chart-options"
  | "view.zoom-in"
  | "view.zoom-out"
  | "view.fit"
  | "view.toggle-wbs"
  | "view.toggle-gantt"
  | "view.toggle-details"
  | "tools.run-schedule"
  | "tools.formula"
  | "tools.reference"
  | "admin.language"
  | "admin.calendar"
  | "dialog.group-sort"
  | "dialog.timescale"
  | "dialog.bars"
  | "dialog.font-row"
  | "help.shortcuts"
  | "help.about"
  | "help.visual-demo";

export type DesktopShellCapabilities = {
  canUndoLayout: boolean;
  canRedoLayout: boolean;
  hasWbs: boolean;
  hasSelectedActivity: boolean;
  hasMultipleWindows: boolean;
  canOpenFieldChooser: boolean;
  groupByWbs: boolean;
};

export type DesktopMenuItem = {
  id: string;
  label: LocalizedLabel;
  shortcut?: string;
  window?: WorkspaceMenuKey;
  command?: DesktopCommand;
  disabledReason?: LocalizedLabel;
  checked?: boolean;
};

export type DesktopMenu = {
  id: DesktopMenuId;
  label: LocalizedLabel;
  items: DesktopMenuItem[];
};

export type DesktopMenuId =
  | "file"
  | "edit"
  | "view"
  | "project"
  | "enterprise"
  | "schedule"
  | "resources"
  | "tools"
  | "reports"
  | "window"
  | "help";

export type DesktopToolbarGroupId =
  | "file"
  | "edit"
  | "layout"
  | "view"
  | "project"
  | "activities"
  | "tools";

export type DesktopToolbarItem = {
  id: string;
  label: LocalizedLabel;
  title: LocalizedLabel;
  shortcut?: string;
  window?: WorkspaceMenuKey;
  command?: DesktopCommand;
  disabledReason?: LocalizedLabel;
  active?: boolean;
  icon?: string;
  group?: DesktopToolbarGroupId;
  fullscreen?: boolean;
};

export type DesktopShellState = {
  locale: string;
  activeWindow: WorkspaceMenuKey;
  openWindows: readonly WorkspaceMenuKey[];
  capabilities: DesktopShellCapabilities;
  project?: ChromeProjectContext;
  layout?: ChromeLayoutState;
  sortColumns?: readonly DesktopSortColumn[];
  sortColumnId?: string | null;
  sortDirection?: "asc" | "desc";
  barHeight?: number;
  barTone?: "crimson" | "vermilion" | "amber";
};

export type DesktopShellHandlers = {
  onWindowOpen: (window: WorkspaceMenuKey) => void;
  onWindowClose: (window: WorkspaceMenuKey) => void;
  onCommand: (command: DesktopCommand) => void;
  onLayoutOptions?: (patch: DesktopLayoutPatch) => void;
  onLocaleChange?: (locale: string) => void;
  onHome?: () => void;
};

export const WINDOW_TITLES: Record<WorkspaceMenuKey, LocalizedLabel> = {
  project: { en: "Projects", fa: "پروژه‌ها" },
  wbs: { en: "WBS", fa: "ساختار شکست" },
  schedule: { en: "Activities", fa: "فعالیت‌ها" },
  progress: { en: "Tracking", fa: "پیگیری" },
  resources: { en: "Resources", fa: "منابع" },
  assignments: { en: "Resource Assignments", fa: "تخصیص منابع" },
  roles: { en: "Roles", fa: "نقش‌ها" },
  calendars: { en: "Calendars", fa: "تقویم‌ها" },
  cost: { en: "Cost", fa: "هزینه" },
  expenses: { en: "Expenses", fa: "هزینه‌ها" },
  documents: { en: "Documents", fa: "اسناد" },
  reports: { en: "Reports", fa: "گزارش‌ها" },
  tracking: { en: "Tracking", fa: "رهگیری" },
  issues: { en: "Issues", fa: "مسائل" },
  risks: { en: "Risks", fa: "ریسک‌ها" },
  thresholds: { en: "Thresholds", fa: "آستانه‌ها" },
  control: { en: "Control", fa: "کنترل" },
  settings: { en: "Administration", fa: "مدیریت" },
};

const WINDOW_ORDER: readonly WorkspaceMenuKey[] = [
  "project",
  "wbs",
  "schedule",
  "progress",
  "resources",
  "assignments",
  "roles",
  "calendars",
  "cost",
  "expenses",
  "documents",
  "reports",
  "tracking",
  "issues",
  "risks",
  "thresholds",
  "control",
  "settings",
];

function language(locale: string): "en" | "fa" {
  return locale.split("-")[0] === "fa" ? "fa" : "en";
}

function pick(label: LocalizedLabel, locale: string): string {
  return translateWorkspaceUiText(locale, label.en, label.fa);
}

function unavailable(reason: LocalizedLabel, locale: string): LocalizedLabel {
  // The reason is already localized; this keeps the shape uniform for tests.
  return reason[language(locale)] ? reason : { en: reason.en, fa: reason.fa };
}

const REASONS = {
  undo: { en: "No earlier layout change is available", fa: "تغییر قبلی چیدمان در دسترس نیست" },
  redo: { en: "No layout change to reapply", fa: "تغییری برای اعمال دوباره وجود ندارد" },
  singleWindow: { en: "The last open window cannot be closed", fa: "آخرین پنجرهٔ باز را نمی‌توان بست" },
  noWbs: { en: "Create a WBS element before adding activities", fa: "پیش از افزودن فعالیت، یک عنصر WBS بسازید" },
  noSelection: { en: "Select an activity in the grid first", fa: "ابتدا یک فعالیت را در جدول انتخاب کنید" },
  noFields: { en: "No saved field layout is available for this project", fa: "چیدمان فیلد ذخیره‌شده‌ای برای این پروژه در دسترس نیست" },
  calendarAdmin: { en: "Calendar administration is not available in this workspace yet", fa: "مدیریت تقویم هنوز در این محیط کار در دسترس نیست" },
  roles: { en: "Role administration is not available in this workspace yet", fa: "مدیریت نقش‌ها هنوز در این محیط کار در دسترس نیست" },
  udfs: { en: "Enterprise user-defined fields are not available in this workspace yet", fa: "فیلدهای سفارشی سازمانی هنوز در این محیط کار در دسترس نیست" },
  baseline: { en: "Baseline management is not available in this workspace yet", fa: "مدیریت خط مبنا هنوز در این محیط کار در دسترس نیست" },
  compare: { en: "Baseline comparison is not available in this workspace yet", fa: "مقایسهٔ خط مبنا هنوز در این محیط کار در دسترس نیست" },
  progress: { en: "Progress update is not available in this workspace yet", fa: "به‌روزرسانی پیشرفت هنوز در این محیط کار در دسترس نیست" },
  leveling: { en: "Resource leveling is not available in this workspace yet", fa: "تسطیح منابع هنوز در این محیط کار در دسترس نیست" },
  reports: { en: "Report generation is not available in this workspace yet", fa: "ساخت گزارش هنوز در این محیط کار در دسترس نیست" },
} satisfies Record<string, LocalizedLabel>;

export function getDesktopMenus(state: DesktopShellState): DesktopMenu[] {
  const { capabilities: caps, locale } = state;
  const windowItem = (key: WorkspaceMenuKey, shortcut?: string): DesktopMenuItem => ({
    id: `window.${key}`,
    label: WINDOW_TITLES[key],
    shortcut,
    window: key,
  });
  return [
    {
      id: "file",
      label: { en: "File", fa: "فایل" },
      items: [
        { id: "file.new", label: { en: "New project…", fa: "پروژهٔ جدید…" }, window: "project" },
        { id: "file.open", label: { en: "Open project…", fa: "بازکردن پروژه…" }, window: "project" },
        { id: "file.settings", label: { en: "Project properties…", fa: "مشخصات پروژه…" }, command: "project.settings" },
        { id: "file.interchange", label: { en: "Import / Export…", fa: "ورود / خروجی…" }, command: "project.interchange" },
        { id: "file.print", label: { en: "Print…", fa: "چاپ…" }, command: "file.print", shortcut: "Ctrl+P" },
        {
          id: "workspace.close",
          label: { en: "Close window", fa: "بستن پنجره" },
          command: "project.close",
          shortcut: "Ctrl+W",
          disabledReason: caps.hasMultipleWindows ? undefined : unavailable(REASONS.singleWindow, locale),
        },
      ],
    },
    {
      id: "edit",
      label: { en: "Edit", fa: "ویرایش" },
      items: [
        {
          id: "edit.undo",
          label: { en: "Undo layout change", fa: "بازگردانی تغییر چیدمان" },
          command: "edit.undo",
          shortcut: "Ctrl+Z",
          disabledReason: caps.canUndoLayout ? undefined : unavailable(REASONS.undo, locale),
        },
        {
          id: "edit.redo",
          label: { en: "Redo layout change", fa: "اعمال دوبارهٔ تغییر چیدمان" },
          command: "edit.redo",
          shortcut: "Ctrl+Y",
          disabledReason: caps.canRedoLayout ? undefined : unavailable(REASONS.redo, locale),
        },
        { id: "edit.find", label: { en: "Find activities…", fa: "یافتن فعالیت‌ها…" }, command: "edit.find", shortcut: "Ctrl+F" },
        { id: "edit.group-wbs", label: { en: "Group by WBS", fa: "گروه‌بندی بر اساس WBS" }, command: "edit.group-wbs", checked: caps.groupByWbs },
        { id: "edit.sort-toggle", label: { en: "Reverse sort direction", fa: "معکوس کردن جهت ترتیب" }, command: "edit.sort-toggle" },
      ],
    },
    {
      id: "view",
      label: { en: "View", fa: "نما" },
      items: [
        {
          id: "view.fields",
          label: { en: "Columns…", fa: "ستون‌ها…" },
          command: "view.fields",
          disabledReason: caps.canOpenFieldChooser ? undefined : unavailable(REASONS.noFields, locale),
        },
        { id: "view.filters", label: { en: "Filters…", fa: "فیلترها…" }, command: "view.filters" },
        { id: "view.group-sort", label: { en: "Group and Sort…", fa: "گروه‌بندی و ترتیب…" }, command: "dialog.group-sort" },
        { id: "view.timescale", label: { en: "Timescale…", fa: "مقیاس زمانی…" }, command: "dialog.timescale" },
        { id: "view.bars", label: { en: "Bars…", fa: "میله‌ها…" }, command: "dialog.bars" },
        { id: "view.font-row", label: { en: "Table Font and Row…", fa: "قلم و ردیف جدول…" }, command: "dialog.font-row" },
        { id: "view.wbs-chart-template", label: { en: "Chart Box Template…", fa: "قالب کادر نمودار…" }, command: "view.wbs-chart-options", disabledReason: state.activeWindow === "wbs" ? undefined : unavailable({ en: "Available in the WBS Chart View", fa: "در نمای نمودار WBS در دسترس است" }, locale) },
        { id: "view.wbs-chart-colors", label: { en: "Chart Font and Colors…", fa: "قلم و رنگ‌های نمودار…" }, command: "view.wbs-chart-options", disabledReason: state.activeWindow === "wbs" ? undefined : unavailable({ en: "Available in the WBS Chart View", fa: "در نمای نمودار WBS در دسترس است" }, locale) },
        { id: "view.zoom-in", label: { en: "Zoom in", fa: "بزرگ‌نمایی" }, command: "view.zoom-in" },
        { id: "view.zoom-out", label: { en: "Zoom out", fa: "کوچک‌نمایی" }, command: "view.zoom-out" },
        { id: "view.fit", label: { en: "Fit to window", fa: "تناسب با پنجره" }, command: "view.fit" },
        { id: "view.toggle-wbs", label: { en: "Show project WBS", fa: "نمایش WBS پروژه" }, command: "view.toggle-wbs" },
        { id: "view.toggle-gantt", label: { en: "Show Gantt Chart", fa: "نمایش گانت" }, command: "view.toggle-gantt" },
        { id: "view.toggle-details", label: { en: "Show Details", fa: "نمایش جزئیات" }, command: "view.toggle-details" },
      ],
    },
    {
      id: "project",
      label: { en: "Project", fa: "پروژه" },
      items: [
        { id: "project.settings", label: { en: "Project properties…", fa: "مشخصات پروژه…" }, command: "project.settings" },
        { id: "project.add-wbs", label: { en: "Add WBS element", fa: "افزودن عنصر WBS" }, command: "project.add-wbs" },
        {
          id: "project.add-activity",
          label: { en: "Add activity", fa: "افزودن فعالیت" },
          command: "project.add-activity",
          disabledReason: caps.hasWbs ? undefined : unavailable(REASONS.noWbs, locale),
        },
        {
          id: "project.edit-activity",
          label: { en: "Edit selected activity", fa: "ویرایش فعالیت انتخاب‌شده" },
          command: "project.edit-activity",
          shortcut: "Enter",
          disabledReason: caps.hasSelectedActivity ? undefined : unavailable(REASONS.noSelection, locale),
        },
        { id: "project.relationships", label: { en: "Relationships", fa: "روابط" }, window: "schedule" },
        { id: "project.schedule", label: { en: "Schedule activities", fa: "زمان‌بندی فعالیت‌ها" }, command: "tools.run-schedule", shortcut: "F9" },
        { id: "project.baseline", label: { en: "Baselines…", fa: "خطوط مبنا…" }, disabledReason: unavailable(REASONS.baseline, locale) },
        { id: "project.compare", label: { en: "Compare baselines…", fa: "مقایسهٔ خطوط مبنا…" }, disabledReason: unavailable(REASONS.compare, locale) },
        { id: "project.progress", label: { en: "Update progress…", fa: "به‌روزرسانی پیشرفت…" }, disabledReason: unavailable(REASONS.progress, locale) },
      ],
    },
    {
      id: "enterprise",
      label: { en: "Enterprise", fa: "سازمان" },
      items: [
        { id: "enterprise.projects", label: WINDOW_TITLES.project, window: "project" },
        { id: "enterprise.resources", label: WINDOW_TITLES.resources, window: "resources" },
        { id: "enterprise.assignments", label: { en: "Resource assignments", fa: "تخصیص منابع" }, window: "resources" },
        { id: "enterprise.roles", label: { en: "Roles…", fa: "نقش‌ها…" }, disabledReason: unavailable(REASONS.roles, locale) },
        { id: "enterprise.calendars", label: { en: "Calendars…", fa: "تقویم‌ها…" }, disabledReason: unavailable(REASONS.calendarAdmin, locale) },
        { id: "enterprise.udfs", label: { en: "User defined fields…", fa: "فیلدهای سفارشی…" }, disabledReason: unavailable(REASONS.udfs, locale) },
      ],
    },
    {
      id: "schedule",
      label: { en: "Schedule", fa: "زمان‌بندی" },
      items: [
        { id: "schedule.run", label: { en: "Schedule activities", fa: "زمان‌بندی فعالیت‌ها" }, command: "tools.run-schedule", shortcut: "F9" },
        { id: "schedule.options", label: { en: "Schedule options", fa: "تنظیمات زمان‌بندی" }, command: "project.schedule-options" },
        { id: "schedule.formula", label: { en: "Formula editor", fa: "ویرایشگر فرمول" }, command: "tools.formula" },
        { id: "schedule.reference", label: { en: "Scheduling reference", fa: "مرجع زمان‌بندی" }, command: "tools.reference" },
        { id: "schedule.level", label: { en: "Level resources…", fa: "تسطیح منابع…" }, disabledReason: unavailable(REASONS.leveling, locale) },
      ],
    },
    {
      id: "resources",
      label: { en: "Resources", fa: "منابع" },
      items: [
        { id: "resources.capacity", label: { en: "Resource capacity", fa: "ظرفیت منابع" }, window: "resources" },
        { id: "resources.assignments", label: { en: "Resource assignments", fa: "تخصیص منابع" }, window: "resources" },
        { id: "resources.assign", label: { en: "Assign resources…", fa: "تخصیص منابع…" }, command: "activity.assign-resources" },
        { id: "resources.predecessors", label: { en: "Assign predecessors…", fa: "تخصیص پیش‌نیاز…" }, command: "activity.predecessors" },
        { id: "resources.successors", label: { en: "Assign successors…", fa: "تخصیص پس‌نیاز…" }, command: "activity.successors" },
      ],
    },
    {
      id: "tools",
      label: { en: "Tools", fa: "ابزارها" },
      items: [
        { id: "tools.forms", label: { en: "Forms & Workflows…", fa: "فرم‌ها و گردش‌کار…" }, command: "forms.open" },
        { id: "tools.search", label: { en: "Search activities", fa: "جست‌وجوی فعالیت‌ها" }, command: "edit.find", shortcut: "Ctrl+F" },
        { id: "tools.preferences", label: { en: "Preferences…", fa: "تنظیمات…" }, window: "settings" },
        { id: "tools.schedule", label: { en: "Schedule", fa: "زمان‌بندی" }, command: "tools.run-schedule" },
        { id: "tools.formula", label: { en: "Formula editor", fa: "ویرایشگر فرمول" }, command: "tools.formula" },
        { id: "tools.reference", label: { en: "Scheduling reference", fa: "مرجع زمان‌بندی" }, command: "tools.reference" },
        { id: "tools.help", label: { en: "Keyboard shortcuts", fa: "کلیدهای میانبر" }, command: "help.shortcuts" },
        { id: "tools.demo", label: { en: "Visual workspace demo", fa: "نمایش بصری محیط کار" }, command: "help.visual-demo" },
      ],
    },
    {
      id: "reports",
      label: { en: "Reports", fa: "گزارش‌ها" },
      items: [
        { id: "reports.open", label: WINDOW_TITLES.reports, window: "reports" },
        { id: "reports.print", label: { en: "Print preview", fa: "پیش‌نمایش چاپ" }, command: "file.print" },
        { id: "reports.generate", label: { en: "Report wizard…", fa: "جادوگر گزارش…" }, disabledReason: unavailable(REASONS.reports, locale) },
      ],
    },
    {
      id: "window",
      label: { en: "Window", fa: "پنجره" },
      items: [
        ...WINDOW_ORDER.map((key, index) => windowItem(key, `Alt+${index + 1}`)),
        {
          id: "window.close",
          label: { en: "Close current window", fa: "بستن پنجرهٔ جاری" },
          command: "project.close",
          disabledReason: caps.hasMultipleWindows ? undefined : unavailable(REASONS.singleWindow, locale),
        },
      ],
    },
    {
      id: "help",
      label: { en: "Help", fa: "راهنما" },
      items: [
        { id: "help.shortcuts", label: { en: "Keyboard shortcuts", fa: "کلیدهای میانبر" }, command: "help.shortcuts", shortcut: "F1" },
        { id: "help.visual-demo", label: { en: "Visual workspace demo", fa: "نمایش بصری محیط کار" }, command: "help.visual-demo" },
        { id: "help.about", label: { en: "About CUBI Workspace", fa: "دربارهٔ محیط کار CUBI" }, command: "help.about" },
      ],
    },
  ];
}

export function getDesktopToolbar(state: DesktopShellState): DesktopToolbarItem[] {
  const { capabilities: caps, locale } = state;
  const reasoning = (label: LocalizedLabel): LocalizedLabel => unavailable(label, locale);
  return [
    { id: "toolbar.new", label: { en: "New", fa: "جدید" }, title: { en: "New project", fa: "پروژهٔ جدید" }, window: "project", icon: "file", group: "file" },
    { id: "toolbar.open", label: { en: "Open", fa: "بازکردن" }, title: { en: "Open project", fa: "بازکردن پروژه" }, window: "project", icon: "book", group: "file" },
    { id: "toolbar.print", label: { en: "Print", fa: "چاپ" }, title: { en: "Print the current view", fa: "چاپ نمای جاری" }, command: "file.print", icon: "print", group: "file" },
    { id: "toolbar.import", label: { en: "Import", fa: "ورود" }, title: { en: "Import project data", fa: "ورود دادهٔ پروژه" }, command: "project.interchange", icon: "book", group: "file" },
    { id: "toolbar.export", label: { en: "Export", fa: "خروجی" }, title: { en: "Export project data", fa: "خروجی دادهٔ پروژه" }, command: "project.interchange", icon: "book", group: "file" },

    { id: "toolbar.undo", label: { en: "Undo", fa: "بازگردانی" }, title: { en: "Undo layout change", fa: "بازگردانی تغییر چیدمان" }, command: "edit.undo", disabledReason: caps.canUndoLayout ? undefined : reasoning(REASONS.undo), icon: "undo", group: "edit" },
    { id: "toolbar.redo", label: { en: "Redo", fa: "تکرار" }, title: { en: "Redo layout change", fa: "اعمال دوبارهٔ تغییر چیدمان" }, command: "edit.redo", disabledReason: caps.canRedoLayout ? undefined : reasoning(REASONS.redo), icon: "redo", group: "edit" },

    { id: "toolbar.fields", label: { en: "Columns", fa: "ستون‌ها" }, title: { en: "Activity field layout", fa: "چیدمان فیلدهای فعالیت" }, command: "view.fields", disabledReason: caps.canOpenFieldChooser ? undefined : reasoning(REASONS.noFields), icon: "columns", group: "layout" },
    { id: "toolbar.find", label: { en: "Filters", fa: "فیلترها" }, title: { en: "Open activity filters", fa: "بازکردن فیلترهای فعالیت" }, command: "view.filters", icon: "filter", group: "layout" },
    { id: "toolbar.group-sort", label: { en: "Group & Sort", fa: "گروه و ترتیب" }, title: { en: "Group and sort dialog", fa: "دیالوگ گروه‌بندی و ترتیب" }, command: "dialog.group-sort", icon: "sort", group: "layout" },
    { id: "toolbar.group-wbs", label: { en: "Group WBS", fa: "گروه WBS" }, title: { en: "Group activities by WBS", fa: "گروه‌بندی فعالیت‌ها بر اساس WBS" }, command: "edit.group-wbs", active: caps.groupByWbs, icon: "group", group: "layout" },

    { id: "toolbar.zoom-in", label: { en: "Zoom In", fa: "بزرگ‌نمایی" }, title: { en: "Zoom in on the timescale", fa: "بزرگ‌نمایی مقیاس زمانی" }, command: "view.zoom-in", icon: "plus", group: "view" },
    { id: "toolbar.zoom-out", label: { en: "Zoom Out", fa: "کوچک‌نمایی" }, title: { en: "Zoom out of the timescale", fa: "کوچک‌نمایی مقیاس زمانی" }, command: "view.zoom-out", icon: "left", group: "view" },
    { id: "toolbar.fit", label: { en: "Fit", fa: "تناسب" }, title: { en: "Fit the Gantt to the window", fa: "تناسب گانت با پنجره" }, command: "view.fit", icon: "bars", group: "view" },
    { id: "toolbar.timescale", label: { en: "Timescale", fa: "مقیاس زمانی" }, title: { en: "Timescale dialog", fa: "دیالوگ مقیاس زمانی" }, command: "dialog.timescale", icon: "clock", group: "view" },
    { id: "toolbar.panels", label: { en: "Panels", fa: "پنل‌ها" }, title: { en: "Show or hide the details panel", fa: "نمایش یا پنهان‌کردن پنل جزئیات" }, command: "view.toggle-details", icon: "table", group: "view" },
    { id: "toolbar.fullscreen", label: { en: "Full Screen", fa: "تمام‌صفحه" }, title: { en: "Enter full screen", fa: "ورود به تمام‌صفحه" }, fullscreen: true, icon: "fullscreen", group: "view" },

    { id: "toolbar.schedule", label: { en: "Schedule", fa: "زمان‌بندی" }, title: { en: "Schedule activities", fa: "زمان‌بندی فعالیت‌ها" }, command: "tools.run-schedule", shortcut: "F9", icon: "calendar", group: "project" },

    { id: "toolbar.add-wbs", label: { en: "WBS", fa: "WBS" }, title: { en: "Add WBS element", fa: "افزودن عنصر WBS" }, command: "project.add-wbs", icon: "tree", group: "activities" },
    { id: "toolbar.add-activity", label: { en: "Add", fa: "افزودن" }, title: { en: "Add activity", fa: "افزودن فعالیت" }, command: "project.add-activity", disabledReason: caps.hasWbs ? undefined : reasoning(REASONS.noWbs), icon: "plus", group: "activities" },
    { id: "toolbar.edit-activity", label: { en: "Edit", fa: "ویرایش" }, title: { en: "Edit selected activity", fa: "ویرایش فعالیت انتخاب‌شده" }, command: "project.edit-activity", disabledReason: caps.hasSelectedActivity ? undefined : reasoning(REASONS.noSelection), icon: "edit", group: "activities" },
    { id: "toolbar.assign", label: { en: "Resources", fa: "منابع" }, title: { en: "Assign resources", fa: "تخصیص منابع" }, command: "activity.assign-resources", icon: "resource", group: "activities" },
    { id: "toolbar.predecessors", label: { en: "Predecessors", fa: "پیش‌نیازها" }, title: { en: "Assign predecessors", fa: "تخصیص پیش‌نیاز" }, command: "activity.predecessors", icon: "link", group: "activities" },
    { id: "toolbar.successors", label: { en: "Successors", fa: "پس‌نیازها" }, title: { en: "Assign successors", fa: "تخصیص پس‌نیاز" }, command: "activity.successors", icon: "network", group: "activities" },

    { id: "toolbar.search", label: { en: "Search", fa: "جست‌وجو" }, title: { en: "Search activities", fa: "جست‌وجوی فعالیت‌ها" }, command: "edit.find", icon: "find", group: "tools" },
    { id: "toolbar.preferences", label: { en: "Preferences", fa: "تنظیمات" }, title: { en: "Workspace preferences", fa: "تنظیمات محیط کار" }, window: "settings", icon: "settings", group: "tools" },
    { id: "toolbar.help", label: { en: "Help", fa: "راهنما" }, title: { en: "Keyboard shortcuts", fa: "کلیدهای میانبر" }, command: "help.shortcuts", shortcut: "F1", icon: "help", group: "tools" },
  ];
}

export function getDesktopToolbarGroups(state: DesktopShellState): Array<{
  id: DesktopToolbarGroupId;
  label: LocalizedLabel;
  items: DesktopToolbarItem[];
}> {
  const groups: Array<{ id: DesktopToolbarGroupId; label: LocalizedLabel; items: DesktopToolbarItem[] }> = [
    { id: "file", label: { en: "File", fa: "فایل" }, items: [] },
    { id: "edit", label: { en: "Edit", fa: "ویرایش" }, items: [] },
    { id: "layout", label: { en: "Layout", fa: "چیدمان" }, items: [] },
    { id: "view", label: { en: "View", fa: "نما" }, items: [] },
    { id: "project", label: { en: "Project", fa: "پروژه" }, items: [] },
    { id: "activities", label: { en: "Activities", fa: "فعالیت‌ها" }, items: [] },
    { id: "tools", label: { en: "Tools", fa: "ابزارها" }, items: [] },
  ];
  for (const item of getDesktopToolbar(state)) {
    const group = groups.find((candidate) => candidate.id === (item.group ?? "file"));
    group?.items.push(item);
  }
  return groups.filter((group) => group.items.length > 0);
}

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function renderMenuItem(item: DesktopMenuItem, locale: string): string {
  const disabled = Boolean(item.disabledReason);
  const reason = item.disabledReason ? pick(item.disabledReason, locale) : "";
  const target = item.window
    ? ` data-desktop-window="${escapeHtml(item.window)}"`
    : item.command
      ? ` data-desktop-command="${escapeHtml(item.command)}"`
      : "";
  return `<button type="button" role="menuitem" class="cp-menubar-item${disabled ? " is-disabled" : ""}"${target}${disabled ? ' disabled aria-disabled="true"' : ""}${item.checked ? ' aria-checked="true"' : ""}${reason ? ` title="${escapeHtml(reason)}"` : ""}>
    <span class="cp-menubar-item-label">${escapeHtml(pick(item.label, locale))}</span>
    ${reason ? `<span class="cp-menubar-item-reason">${escapeHtml(reason)}</span>` : item.shortcut ? `<span class="cp-menubar-item-shortcut">${escapeHtml(item.shortcut)}</span>` : ""}
  </button>`;
}

function renderMenus(state: DesktopShellState): string {
  const locale = state.locale;
  const menus = getDesktopMenus(state);
  const menuAria = translateWorkspaceUiText(locale, "Application menu", "منوی برنامه");
  return `<div class="cp-menubar" role="menubar" aria-label="${escapeHtml(menuAria)}">
    ${menus.map((menu) => `<div class="cp-menubar-group">
      <button type="button" class="cp-menubar-trigger" role="menuitem" aria-haspopup="true" aria-expanded="false" data-desktop-menu="${escapeHtml(menu.id)}">${escapeHtml(pick(menu.label, locale))}</button>
      <div class="cp-menubar-popup" role="menu" data-desktop-popup="${escapeHtml(menu.id)}" aria-label="${escapeHtml(pick(menu.label, locale))}" hidden>
        ${menu.items.map((item) => renderMenuItem(item, locale)).join("")}
      </div>
    </div>`).join("")}
  </div>`;
}

function renderToolbarButton(item: DesktopToolbarItem, locale: string, compact: boolean): string {
  const disabled = Boolean(item.disabledReason);
  const title = item.disabledReason ? pick(item.disabledReason, locale) : pick(item.title, locale);
  const target = item.fullscreen
    ? ' data-fullscreen-toggle="true"'
    : item.window
      ? ` data-desktop-window="${escapeHtml(item.window)}"`
      : item.command
        ? ` data-desktop-command="${escapeHtml(item.command)}"`
        : "";
  return `<button type="button" class="cp-toolbar-button${compact ? " is-compact" : ""}${item.fullscreen ? " is-fullscreen" : ""}" data-toolbar-command="${escapeHtml(item.id)}"${target} title="${escapeHtml(title)}" aria-label="${escapeHtml(title)}"${item.active ? ' aria-pressed="true"' : ""}${disabled ? ' disabled aria-disabled="true"' : ""}>${workspaceIcon(item.icon ?? "activity")}<span class="cp-toolbar-label">${escapeHtml(pick(item.label, locale))}</span></button>`;
}

function renderToolbar(state: DesktopShellState): string {
  const locale = state.locale;
  const groups = getDesktopToolbarGroups(state);
  const all = groups.flatMap((group) => group.items);
  const toolbarAria = translateWorkspaceUiText(locale, "Main toolbar", "نوار ابزار اصلی");
  const moreTools = translateWorkspaceUiText(locale, "More tools", "ابزارهای بیشتر");
  const more = translateWorkspaceUiText(locale, "More", "بیشتر");
  return `<div class="cp-toolbar" role="toolbar" aria-label="${escapeHtml(toolbarAria)}">
    <div class="cp-toolbar-scroll">
      ${groups.map((group) => `<div class="cp-toolbar-group" role="group" aria-label="${escapeHtml(pick(group.label, locale))}" title="${escapeHtml(pick(group.label, locale))}">
        ${group.items.map((item) => renderToolbarButton(item, locale, false)).join("")}
      </div>`).join("")}
    </div>
    <button type="button" class="cp-toolbar-more" data-toolbar-overflow aria-haspopup="true" aria-expanded="false" title="${escapeHtml(moreTools)}">${workspaceIcon("right")}<span>${escapeHtml(more)}</span></button>
    <div class="cp-toolbar-overflow-popup" data-toolbar-overflow-popup hidden role="menu" aria-label="${escapeHtml(moreTools)}">
      ${all.map((item) => renderToolbarButton(item, locale, true)).join("")}
    </div>
  </div>`;
}

function renderTabs(state: DesktopShellState): string {
  const locale = state.locale;
  const closable = state.openWindows.length > 1;
  const openWindowsAria = translateWorkspaceUiText(locale, "Open windows", "پنجره‌های باز");
  const closeWord = translateWorkspaceUiText(locale, "Close", "بستن");
  return `<div class="cp-window-tabs" role="tablist" aria-label="${escapeHtml(openWindowsAria)}">
    ${state.openWindows.map((key) => {
      const selected = key === state.activeWindow;
      const title = pick(WINDOW_TITLES[key], locale);
      return `<span class="cp-window-tab${selected ? " is-active" : ""}" role="tab" aria-selected="${selected ? "true" : "false"}" data-window-tab="${escapeHtml(key)}" tabindex="${selected ? "0" : "-1"}">
        <button type="button" class="cp-window-tab-label" data-window-open="${escapeHtml(key)}">${escapeHtml(title)}</button>
        ${closable ? `<button type="button" class="cp-window-tab-close" data-window-close="${escapeHtml(key)}" aria-label="${escapeHtml(closeWord + " " + title)}" title="${escapeHtml(closeWord + " " + title)}">×</button>` : ""}
      </span>`;
    }).join("")}
  </div>`;
}

function renderShortcutsDialog(state: DesktopShellState): string {
  const locale = state.locale;
  const rows = getDesktopMenus(state).flatMap((menu) => menu.items.filter((item) => item.shortcut));
  const heading = translateWorkspaceUiText(locale, "Keyboard shortcuts", "کلیدهای میانبر");
  const command = translateWorkspaceUiText(locale, "Command", "فرمان");
  const shortcut = translateWorkspaceUiText(locale, "Shortcut", "میانبر");
  const close = translateWorkspaceUiText(locale, "Close", "بستن");
  return `<dialog class="cp-desktop-dialog" data-desktop-dialog="shortcuts" aria-labelledby="cp-shortcuts-heading">
    <h2 id="cp-shortcuts-heading">${escapeHtml(heading)}</h2>
    <table><thead><tr><th>${escapeHtml(command)}</th><th>${escapeHtml(shortcut)}</th></tr></thead>
    <tbody>${rows.map((item) => `<tr><td>${escapeHtml(pick(item.label, locale))}</td><td><kbd>${escapeHtml(item.shortcut ?? "")}</kbd></td></tr>`).join("")}</tbody></table>
    <form method="dialog"><button type="submit">${escapeHtml(close)}</button></form>
  </dialog>`;
}

function renderAboutDialog(state: DesktopShellState): string {
  const locale = state.locale;
  const close = translateWorkspaceUiText(locale, "Close", "بستن");
  const heading = translateWorkspaceUiText(locale, "About CUBI Workspace", "دربارهٔ محیط کار CUBI");
  const summary = translateWorkspaceUiText(
    locale,
    "The CUBI project controls workspace: project structure, work breakdown, activities, relationships, scheduling and graphical views.",
    "محیط کار کنترل پروژهٔ CUBI: ساختار پروژه، ساختار شکست کار، فعالیت‌ها، روابط، زمان‌بندی و نمایش گرافیکی.",
  );
  const sources = translateWorkspaceUiText(
    locale,
    "Data is read from this session's project server; the workspace never reports invented figures or states.",
    "داده‌ها از سرور پروژهٔ همین نشست خوانده می‌شوند؛ صفحهٔ راهنما هیچ عدد یا وضعیت ساختگی نمایش نمی‌دهد.",
  );
  return `<dialog class="cp-desktop-dialog" data-desktop-dialog="about" aria-labelledby="cp-about-heading">
    <h2 id="cp-about-heading">${escapeHtml(heading)}</h2>
    <p>${escapeHtml(summary)}</p>
    <p>${escapeHtml(sources)}</p>
    <form method="dialog"><button type="submit">${escapeHtml(close)}</button></form>
  </dialog>`;
}

export function renderDesktopShell(
  host: HTMLElement,
  state: DesktopShellState,
  handlers: DesktopShellHandlers,
): void {
  runtimeByHost.set(host, { state, handlers });
  const layout = state.layout ?? { groupBy: state.capabilities.groupByWbs ? "wbs" : "none", ganttScale: "day", showRelationships: true, density: "compact" };
  const chrome = {
    locale: state.locale,
    project: state.project,
    layout,
    activeWindowTitle: pick(WINDOW_TITLES[state.activeWindow], state.locale),
    openWindowCount: state.openWindows.length,
  };
  host.innerHTML = `<section class="cp-desktop" data-desktop-shell>
    ${renderTitleBar(chrome)}
    ${renderMenus(state)}
    ${renderToolbar(state)}
    ${renderLayoutBar(chrome)}
    ${renderTabs(state)}
  </section>
  ${renderLayoutDialogs({
    locale: state.locale,
    layout,
    sortColumns: [...(state.sortColumns ?? [])],
    sortColumnId: state.sortColumnId ?? null,
    sortDirection: state.sortDirection ?? "asc",
    barHeight: state.barHeight ?? 16,
    barTone: state.barTone ?? "crimson",
  })}
  ${renderShortcutsDialog(state)}
  ${renderAboutDialog(state)}`;
  bindHost(host);
  syncFullscreenControls();
}

type ShellRuntime = { state: DesktopShellState; handlers: DesktopShellHandlers };
const runtimeByHost = new WeakMap<HTMLElement, ShellRuntime>();
const boundHosts = new WeakSet<HTMLElement>();
let documentBound = false;

function popupFor(host: HTMLElement, menuId: string): HTMLElement | null {
  return host.querySelector<HTMLElement>(`[data-desktop-popup="${menuId}"]`);
}

function triggerFor(host: HTMLElement, menuId: string): HTMLElement | null {
  return host.querySelector<HTMLElement>(`[data-desktop-menu="${menuId}"]`);
}

function closeMenus(host: HTMLElement, restoreFocus = false): void {
  const overflowPopup = host.querySelector<HTMLElement>("[data-toolbar-overflow-popup]");
  if (overflowPopup) overflowPopup.hidden = true;
  host.querySelector<HTMLElement>("[data-toolbar-overflow]")?.setAttribute("aria-expanded", "false");
  let restored = false;
  host.querySelectorAll<HTMLElement>("[data-desktop-menu]").forEach((trigger) => {
    const wasOpen = trigger.getAttribute("aria-expanded") === "true";
    trigger.setAttribute("aria-expanded", "false");
    const menuId = trigger.dataset.desktopMenu;
    if (menuId) {
      const popup = popupFor(host, menuId);
      if (popup) popup.hidden = true;
    }
    if (restoreFocus && wasOpen && !restored) {
      trigger.focus();
      restored = true;
    }
  });
}

function openMenu(host: HTMLElement, menuId: string, focusFirst = false): void {
  closeMenus(host);
  const trigger = triggerFor(host, menuId);
  const popup = popupFor(host, menuId);
  if (!trigger || !popup) return;
  trigger.setAttribute("aria-expanded", "true");
  popup.hidden = false;
  if (focusFirst) {
    popup.querySelector<HTMLElement>("button:not([disabled])")?.focus();
  }
}

type DesktopDialogName = "shortcuts" | "about" | "group-sort" | "timescale" | "bars" | "font-row";

function openDialog(host: HTMLElement, name: DesktopDialogName): void {
  const dialog = host.querySelector<HTMLDialogElement>(`[data-desktop-dialog="${name}"]`);
  if (!dialog) return;
  closeMenus(host);
  if (typeof dialog.showModal === "function") dialog.showModal();
  else dialog.setAttribute("open", "");
}

function dialogNameForCommand(command: string): DesktopDialogName | null {
  switch (command) {
    case "dialog.group-sort": return "group-sort";
    case "dialog.timescale": return "timescale";
    case "dialog.bars": return "bars";
    case "dialog.font-row": return "font-row";
    default: return null;
  }
}

function commandForTarget(target: HTMLElement): { command?: string; window?: string } {
  const command = target.closest<HTMLElement>("[data-desktop-command]")?.dataset.desktopCommand;
  const windowKey = target.closest<HTMLElement>("[data-desktop-window]")?.dataset.desktopWindow;
  return { command, window: windowKey };
}

function isFullscreen(): boolean {
  return typeof document !== "undefined" && Boolean(document.fullscreenElement);
}

function activeLocale(): string {
  return typeof document !== "undefined" ? document.documentElement.lang || "en" : "en";
}

function localizedFullscreenLabel(fullscreen: boolean): string {
  const locale = activeLocale();
  return fullscreen
    ? translateWorkspaceUiText(locale, "Return to Main View", "بازگشت به نمای اصلی")
    : translateWorkspaceUiText(locale, "Full Screen", "تمام‌صفحه");
}

export function syncFullscreenControls(): void {
  if (typeof document === "undefined") return;
  const locale = activeLocale();
  const fullscreen = isFullscreen();
  const label = localizedFullscreenLabel(fullscreen);
  const title = fullscreen
    ? translateWorkspaceUiText(locale, "Return to the main workspace view", "بازگشت به نمای اصلی محیط کار")
    : translateWorkspaceUiText(locale, "Enter full screen", "ورود به تمام‌صفحه");
  document.querySelectorAll<HTMLElement>("[data-fullscreen-toggle]").forEach((button) => {
    button.setAttribute("title", title);
    button.setAttribute("aria-label", title);
    button.setAttribute("aria-pressed", fullscreen ? "true" : "false");
    const text = button.querySelector<HTMLElement>(".cp-toolbar-label");
    if (text) text.textContent = label;
    const icon = button.querySelector("svg");
    if (icon) icon.outerHTML = workspaceIcon(fullscreen ? "exitfullscreen" : "fullscreen");
  });
}

function toggleFullscreen(): void {
  if (typeof document === "undefined") return;
  if (isFullscreen()) {
    void document.exitFullscreen?.().catch(() => undefined);
    return;
  }
  const request = document.documentElement.requestFullscreen?.();
  if (request && typeof request.catch === "function") request.catch(() => undefined);
}

let fullscreenBound = false;
function bindFullscreen(): void {
  if (fullscreenBound || typeof document === "undefined") return;
  fullscreenBound = true;
  document.addEventListener("fullscreenchange", syncFullscreenControls);
}

function bindHost(host: HTMLElement): void {
  if (boundHosts.has(host)) return;
  boundHosts.add(host);
  bindFullscreen();
  host.addEventListener("click", (event) => {
    const target = event.target as HTMLElement | null;
    if (!target || typeof target.closest !== "function") return;
    const runtime = runtimeByHost.get(host);
    if (!runtime) return;

    const home = target.closest<HTMLElement>("[data-workspace-home]");
    if (home) {
      closeMenus(host);
      runtime.handlers.onHome?.();
      return;
    }

    const overflowToggle = target.closest<HTMLElement>("[data-toolbar-overflow]");
    if (overflowToggle) {
      const popup = host.querySelector<HTMLElement>("[data-toolbar-overflow-popup]");
      if (popup) {
        const open = popup.hidden;
        popup.hidden = !open;
        overflowToggle.setAttribute("aria-expanded", open ? "true" : "false");
      }
      return;
    }
    const fullscreen = target.closest<HTMLElement>("[data-fullscreen-toggle]");
    if (fullscreen) {
      toggleFullscreen();
      return;
    }

    const cancel = target.closest<HTMLElement>("[data-dialog-cancel]");
    if (cancel) {
      cancel.closest<HTMLDialogElement>("dialog")?.close();
      return;
    }
    const reset = target.closest<HTMLElement>("[data-dialog-default]");
    if (reset) {
      reset.closest<HTMLDialogElement>("dialog")?.close();
      runtime.handlers.onLayoutOptions?.(defaultLayoutPatch());
      return;
    }
    const help = target.closest<HTMLElement>("[data-dialog-help]");
    if (help) {
      help.closest<HTMLDialogElement>("dialog")?.close();
      openDialog(host, "shortcuts");
      return;
    }

    const closeWindow = target.closest<HTMLElement>("[data-window-close]");
    if (closeWindow?.dataset.windowClose) {
      event.stopPropagation();
      runtime.handlers.onWindowClose(closeWindow.dataset.windowClose as WorkspaceMenuKey);
      return;
    }
    const openTab = target.closest<HTMLElement>("[data-window-open]");
    if (openTab?.dataset.windowOpen) {
      runtime.handlers.onWindowOpen(openTab.dataset.windowOpen as WorkspaceMenuKey);
      return;
    }
    const tab = target.closest<HTMLElement>("[data-window-tab]");
    if (tab?.dataset.windowTab) {
      runtime.handlers.onWindowOpen(tab.dataset.windowTab as WorkspaceMenuKey);
      return;
    }
    const trigger = target.closest<HTMLElement>("[data-desktop-menu]");
    if (trigger?.dataset.desktopMenu) {
      event.stopPropagation();
      const expanded = trigger.getAttribute("aria-expanded") === "true";
      if (expanded) closeMenus(host);
      else openMenu(host, trigger.dataset.desktopMenu);
      return;
    }
    const commandTarget = target.closest<HTMLElement>("[data-desktop-command], [data-desktop-window]");
    if (commandTarget) {
      if (commandTarget.hasAttribute("disabled")) return;
      const { command, window: windowKey } = commandForTarget(target);
      closeMenus(host);
      if (command === "help.shortcuts") { openDialog(host, "shortcuts"); return; }
      if (command === "help.about") { openDialog(host, "about"); return; }
      const dialogName = command ? dialogNameForCommand(command) : null;
      if (dialogName) { openDialog(host, dialogName); return; }
      if (windowKey) { runtime.handlers.onWindowOpen(windowKey as WorkspaceMenuKey); return; }
      if (command) runtime.handlers.onCommand(command as DesktopCommand);
      return;
    }
    if (host.contains(target)) closeMenus(host);
  });

  host.addEventListener("change", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLSelectElement) || !target.matches("[data-workspace-language]")) return;
    const runtime = runtimeByHost.get(host);
    if (!runtime) return;
    runtime.handlers.onLocaleChange?.(target.value);
  });

  host.addEventListener("submit", (event) => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement) || !form.matches("[data-dialog-form]")) return;
    event.preventDefault();
    const runtime = runtimeByHost.get(host);
    runtime?.handlers.onLayoutOptions?.(readLayoutPatch(form));
    form.closest<HTMLDialogElement>("dialog")?.close();
  });

  host.addEventListener("keydown", (event) => {
    const target = event.target as HTMLElement | null;
    if (!target) return;
    if (event.key === "Escape") {
      closeMenus(host, true);
      return;
    }
    const trigger = target.closest<HTMLElement>("[data-desktop-menu]");
    if (!trigger) return;
    const triggers = Array.from(host.querySelectorAll<HTMLElement>("[data-desktop-menu]"));
    const index = triggers.indexOf(trigger);
    if (event.key === "ArrowDown") {
      event.preventDefault();
      openMenu(host, trigger.dataset.desktopMenu ?? "", true);
    } else if (event.key === "ArrowRight") {
      event.preventDefault();
      triggers[(index + 1) % triggers.length]?.focus();
    } else if (event.key === "ArrowLeft") {
      event.preventDefault();
      triggers[(index - 1 + triggers.length) % triggers.length]?.focus();
    }
  });

  host.addEventListener("keydown", (event) => {
    const runtime = runtimeByHost.get(host);
    if (!runtime) return;
    const target = event.target as HTMLElement | null;
    const typing = Boolean(target?.closest("input, textarea, select, [contenteditable=true]"));
    if (event.key === "F1") { event.preventDefault(); openDialog(host, "shortcuts"); return; }
    if (event.altKey && /^[1-9]$/.test(event.key)) {
      const key = WINDOW_ORDER[Number(event.key) - 1];
      if (key && runtime.state.openWindows.includes(key)) {
        event.preventDefault();
        runtime.handlers.onWindowOpen(key);
      }
      return;
    }
    if (!(event.ctrlKey || event.metaKey) || typing) return;
    const lower = event.key.toLowerCase();
    if (lower === "f") { event.preventDefault(); runtime.handlers.onCommand("edit.find"); return; }
    if (lower === "z") {
      if (runtime.state.capabilities.canUndoLayout) {
        event.preventDefault();
        runtime.handlers.onCommand("edit.undo");
      }
      return;
    }
    if (lower === "y") { event.preventDefault(); if (runtime.state.capabilities.canRedoLayout) runtime.handlers.onCommand("edit.redo"); return; }
    if (lower === "w") {
      if (runtime.state.capabilities.hasMultipleWindows) {
        event.preventDefault();
        runtime.handlers.onCommand("project.close");
      }
    }
  });
}

function bindDocument(): void {
  if (documentBound || typeof document === "undefined") return;
  documentBound = true;
  document.addEventListener("click", (event) => {
    const target = event.target as Node | null;
    document.querySelectorAll<HTMLElement>("[data-desktop-shell]").forEach((shell) => {
      const host = shell.parentElement;
      if (!host) return;
      if (!target || !host.contains(target)) closeMenus(host);
    });
  });
}

if (typeof document !== "undefined") bindDocument();
