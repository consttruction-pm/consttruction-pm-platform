import type { WorkspaceActivityRow, WorkspaceMenuKey, WorkspaceWbsNode } from "./workspace-model.js";
import type { WorkspaceTheme } from "./workspace-theme.js";
import { renderTitleBar, type ChromeLayoutState, type ChromeProjectContext } from "./workspace-chrome.js";
import { addFilterCriterion, defaultLayoutPatch, filterCriterionRows, formatFilterPreview, loadFilterEditor, moveFilterCriterion, readLayoutPatch, removeFilterCriterion, renderLayoutDialogs, renumberFilterRows, resetFilterEditor, setFilterCriterionRows, setFilterListEnabled, sortFilterList, syncFilterField, syncFilterOperator, type DesktopLayoutPatch, type DesktopSortColumn } from "./workspace-dialogs.js";
import { createActivityFilterDateContext, findActivityFilter, normalizeActivityFilter, optimizeActivityFilterCriteria, previewActivityFilter, type ActivityFilterCriterion, type ActivityFilterDefinition } from "./workspace-activity-filters.js";
import { DEFAULT_PRESENTATION, type WorkspacePresentation } from "./workspace-presentation.js";
import { workspaceIcon, type WorkspaceIconName } from "./workspace-icons.js";
import { desktopMenuIcon } from "./workspace-command-icons.js";
import {
  WORKSPACE_TOOLBAR_GROUPS,
  WORKSPACE_TOOLBAR_LABELS,
  type WorkspaceToolbarGroup,
} from "./workspace-toolbars.js";
import { translateWorkspaceUiText } from "./workspace-localization.js";
import { moveWorkspaceWindow, reorderWorkspaceWindows } from "./workspace-windows.js";

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
  | "edit.group-wbs"
  | "edit.sort-toggle"
  | "edit.select-all"
  | "edit.link"
  | "edit.unlink"
  | "project.add-wbs"
  | "project.add-activity"
  | "project.edit-activity"
  | "project.schedule-options"
  | "activity.assign-resources"
  | "activity.predecessors"
  | "activity.successors"
  | "layout.open"
  | "layout.save"
  | "layout.save-as"
  | "view.fields"
  | "view.line-numbers"
  | "view.expand-all"
  | "view.collapse-all"
  | "view.collapse-to"
  | "view.zoom-in"
  | "view.zoom-out"
  | "view.fit"
  | "view.toggle-wbs"
  | "view.toggle-gantt"
  | "view.toggle-details"
  | "view.top-table"
  | "view.top-table-gantt"
  | "view.top-network"
  | "view.bottom-details"
  | "view.bottom-trace"
  | "view.bottom-usage-spreadsheet"
  | "view.bottom-usage-profile"
  | "view.bottom-none"
  | "view.theme-classic"
  | "view.theme-modern"
  | "view.theme-graphite"
  | "view.theme-arctic"
  | "view.theme-copper"
  | "view.theme-midnight"
  | "tools.run-schedule"
  | "tools.formula"
  | "tools.reference"
  | "admin.language"
  | "admin.calendar"
  | "workspace.refresh"
  | "dialog.group-sort"
  | "dialog.filters"
  | "dialog.timescale"
  | "dialog.bars"
  | "dialog.font-row"
  | "dialog.user-preferences"
  | "help.shortcuts"
  | "help.about"
  | `view.toolbar-${WorkspaceToolbarGroup}`;

export type DesktopShellCapabilities = {
  canUndoLayout: boolean;
  canRedoLayout: boolean;
  hasWbs: boolean;
  hasSelectedActivity: boolean;
  /** Two or more activity rows are selected, so a link can address a pair. */
  hasMultiSelection: boolean;
  /** At least one activity is loaded, so whole-table selection is possible. */
  hasActivities: boolean;
  /** At least one persisted relationship is loaded, so logic views can draw. */
  hasRelationships: boolean;
  /** At least one stored assignment period exists, so usage views can project. */
  hasAssignmentPeriods: boolean;
  hasMultipleWindows: boolean;
  canOpenFieldChooser: boolean;
  hasLayout: boolean;
  groupByWbs: boolean;
  /** Derived from the authenticated session's roles, never from a client guess. */
  canAdminister: boolean;
};

export type DesktopMenuItem = {
  id: string;
  label: LocalizedLabel;
  shortcut?: string;
  window?: WorkspaceMenuKey;
  command?: DesktopCommand;
  disabledReason?: LocalizedLabel;
  checked?: boolean;
  separator?: boolean;
};

export type DesktopMenu = {
  id: DesktopMenuId;
  label: LocalizedLabel;
  /** Alt+letter mnemonic used by the menu bar's hot-key navigation. */
  accessKey: string;
  items: DesktopMenuItem[];
};

export type DesktopMenuId =
  | "workspace"
  | "edit"
  | "view"
  | "project"
  | "organization"
  | "tools"
  | "administration"
  | "help";

export type DesktopToolbarItem = {
  id: string;
  label: LocalizedLabel;
  title: LocalizedLabel;
  shortcut?: string;
  window?: WorkspaceMenuKey;
  command?: DesktopCommand;
  disabledReason?: LocalizedLabel;
  active?: boolean;
  icon: WorkspaceIconName;
  group: WorkspaceToolbarGroup;
  /** Windows on which this toolbar command is meaningful. */
  windows?: readonly WorkspaceMenuKey[];
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
  sortLevels?: readonly { columnId: string; direction: "asc" | "desc" }[];
  /** Ordered group plan the Group and Sort dialog edits. */
  groupLevels?: readonly { fieldId: string; direction: "asc" | "desc" }[];
  presentation?: WorkspacePresentation;
  /** Bottom Details pane visibility; drives the View command label and state. */
  detailsVisible?: boolean;
  /** Activities window: which view owns the top half. */
  activityTopLayout?: "table-only" | "table-gantt" | "activity-network";
  /** Activities window: which view owns the bottom half. */
  activityBottomLayout?: "details" | "trace-logic" | "usage-profile" | "usage-spreadsheet" | "none";
  /** Active workspace skin token set. */
  theme?: WorkspaceTheme;
  dataAvailability?: { actual: boolean; baseline: boolean };
  /** Authoritative project Data Date; null when the read model exposes none. */
  dataDate?: string | null;
  /** Toolbar families the user hid; the commands stay in the menus. */
  hiddenToolbarGroups?: readonly WorkspaceToolbarGroup[];
  /** Gantt pane visibility, used for the toolbar's pressed state. */
  ganttVisible?: boolean;
  /** Windows carrying unsaved edits, used for the tab indicator and close guard. */
  dirtyWindows?: readonly WorkspaceMenuKey[];
  /** Persisted activity rows and WBS nodes, used by the live filter preview. */
  activities?: readonly WorkspaceActivityRow[];
  wbsNodes?: readonly WorkspaceWbsNode[];
};

export type DesktopShellHandlers = {
  onWindowOpen: (window: WorkspaceMenuKey) => void;
  onWindowClose: (window: WorkspaceMenuKey) => void;
  onWindowReorder?: (open: readonly WorkspaceMenuKey[]) => void;
  onCommand: (command: DesktopCommand) => void;
  onLayoutOptions?: (patch: DesktopLayoutPatch) => void;
  onLocaleChange?: (locale: string) => void;
  onHome?: () => void;
};

export const WINDOW_TITLES: Record<WorkspaceMenuKey, LocalizedLabel> = {
  project: { en: "Projects", fa: "پروژه‌ها" },
  wbs: { en: "WBS", fa: "ساختار شکست" },
  schedule: { en: "Activities", fa: "فعالیت‌ها" },
  progress: { en: "Progress", fa: "پیشرفت" },
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
  settings: { en: "Settings", fa: "تنظیمات" },
  administration: { en: "Administration", fa: "مدیریت" },
  exchange: { en: "Import / Export", fa: "ورود / خروجی" },
  backup: { en: "Backup / Recovery", fa: "پشتیبان‌گیری / بازیابی" },
};

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
  noWbsGroup: { en: "Group the activity table by WBS to use hierarchy commands", fa: "برای فرمان‌های سلسله‌مراتب، جدول فعالیت را بر اساس WBS گروه‌بندی کنید" },
  noSelection: { en: "Select an activity in the grid first", fa: "ابتدا یک فعالیت را در جدول انتخاب کنید" },
  noActivities: { en: "Load activities in the Activities window first", fa: "ابتدا فعالیت‌ها را در پنجرهٔ فعالیت‌ها بارگذاری کنید" },
  noMultiSelection: { en: "Select at least two activities to unlink", fa: "برای قطع پیوند، دست‌کم دو فعالیت را انتخاب کنید" },
  noRelationships: { en: "This project has no persisted relationships to draw", fa: "این پروژه رابطهٔ ذخیره‌شده‌ای برای ترسیم ندارد" },
  noAssignmentPeriods: { en: "This project stores no assignment periods to show", fa: "این پروژه دورهٔ تخصیصی برای نمایش ذخیره نکرده است" },
  activitiesWindow: { en: "Switch to the Activities window to change its layout", fa: "برای تغییر چیدمان، به پنجرهٔ فعالیت‌ها بروید" },
  noFields: { en: "No saved field layout is available for this project", fa: "چیدمان فیلد ذخیره‌شده‌ای برای این پروژه در دسترس نیست" },
  noLayout: { en: "This project has no saved layout to write", fa: "این پروژه چیدمان ذخیره‌شده‌ای برای نوشتن ندارد" },
  clipboard: { en: "The activity clipboard is not connected to this workspace yet", fa: "کلیپ‌بورد فعالیت هنوز به این محیط کار متصل نشده است" },
  deleteActivity: { en: "Deleting activities is not available in this workspace yet", fa: "حذف فعالیت هنوز در این محیط کار در دسترس نیست" },
  findNext: { en: "Find Next needs a result set from the current filter", fa: "یافتن مورد بعدی به نتیجهٔ فیلتر جاری نیاز دارد" },
  commit: { en: "There is no staged edit to commit", fa: "ویرایش آماده‌ای برای ثبت وجود ندارد" },
  replace: { en: "Replace is not available in this workspace yet", fa: "جایگزینی هنوز در این محیط کار در دسترس نیست" },
  leveling: { en: "Resource leveling is not available in this workspace yet", fa: "تسطیح منابع هنوز در این محیط کار در دسترس نیست" },
  autoReorg: { en: "Automatic WBS reorganization is not available in this workspace yet", fa: "بازآرایی خودکار ساختار شکست هنوز در این محیط کار در دسترس نیست" },
  fillDown: { en: "Fill Down needs editable table cells; CUBI edits each activity in Activity Details", fa: "پرکردن به پایین به سلول‌های ویرایش‌پذیر نیاز دارد؛ CUBI هر فعالیت را در جزئیات فعالیت ویرایش می‌کند" },
  dissolve: { en: "Dissolving a WBS band while keeping its activities has no server contract; move its activities and delete the band instead", fa: "انحلال یک باند WBS با نگه‌داشتن فعالیت‌های آن قرارداد سمت سرور ندارد؛ فعالیت‌ها را منتقل و باند را حذف کنید" },
  additionalActivities: { en: "CUBI keeps one canonical Activities window per project; use the window tabs instead of a second synchronized table", fa: "CUBI برای هر پروژه یک پنجرهٔ فعالیت متعارف نگه می‌دارد؛ به‌جای جدول همگام دوم از زبانه‌های پنجره استفاده کنید" },
  udfs: { en: "Enterprise user-defined fields are not available in this workspace yet", fa: "فیلدهای سفارشی سازمانی هنوز در این محیط کار در دسترس نیست" },
  baseline: { en: "Baseline management is not available in this workspace yet", fa: "مدیریت خط مبنا هنوز در این محیط کار در دسترس نیست" },
  compare: { en: "Baseline comparison is not available in this workspace yet", fa: "مقایسهٔ خط مبنا هنوز در این محیط کار در دسترس نیست" },
  progress: { en: "Progress update is not available in this workspace yet", fa: "به‌روزرسانی پیشرفت هنوز در این محیط کار در دسترس نیست" },
  reports: { en: "Report generation is not available in this workspace yet", fa: "ساخت گزارش هنوز در این محیط کار در دسترس نیست" },
  users: { en: "User administration is not available in this workspace yet", fa: "مدیریت کاربران هنوز در این محیط کار در دسترس نیست" },
  security: { en: "Security profiles are not available in this workspace yet", fa: "پروفایل‌های امنیتی هنوز در این محیط کار در دسترس نیستند" },
  categories: { en: "Administration categories are not available in this workspace yet", fa: "دسته‌های مدیریتی هنوز در این محیط کار در دسترس نیستند" },
  currencies: { en: "Currency administration is not available in this workspace yet", fa: "مدیریت ارزها هنوز در این محیط کار در دسترس نیست" },
  periods: { en: "Financial periods are not available in this workspace yet", fa: "دوره‌های مالی هنوز در این محیط کار در دسترس نیستند" },
  audit: { en: "The audit history is not available in this workspace yet", fa: "تاریخچهٔ ممیزی هنوز در این محیط کار در دسترس نیست" },
  recovery: { en: "Recovery administration is not available in this workspace yet", fa: "مدیریت بازیابی هنوز در این محیط کار در دسترس نیست" },
} satisfies Record<string, LocalizedLabel>;

export function getDesktopMenus(state: DesktopShellState): DesktopMenu[] {
  const { capabilities: caps, locale } = state;
  const presentation = state.presentation ?? DEFAULT_PRESENTATION;
  // Show on Top / Show on Bottom only address the Activities window layout.
  const layoutScopeOk = state.activeWindow === "schedule";
  const layoutScopeReason = layoutScopeOk ? undefined : unavailable(REASONS.activitiesWindow, locale);
  const windowItem = (key: WorkspaceMenuKey, shortcut?: string): DesktopMenuItem => ({
    id: `window.${key}`,
    label: WINDOW_TITLES[key],
    shortcut,
    window: key,
  });
  const layoutReason = caps.hasLayout ? undefined : unavailable(REASONS.noLayout, locale);
  const hidden = new Set(state.hiddenToolbarGroups ?? []);
  const separator = (id: string): DesktopMenuItem => ({ id, label: { en: "—", fa: "—" }, separator: true });
  const toolbarLabel = (group: WorkspaceToolbarGroup): string => {
    const pack = WORKSPACE_TOOLBAR_LABELS[locale as keyof typeof WORKSPACE_TOOLBAR_LABELS]
      ?? WORKSPACE_TOOLBAR_LABELS.en;
    return pack[group];
  };
  const menus: DesktopMenu[] = [
    {
      id: "workspace",
      accessKey: "f",
      label: { en: "File", fa: "فایل" },
      items: [
        { id: "file.new", label: { en: "New project…", fa: "پروژهٔ جدید…" }, window: "project", shortcut: "Ctrl+N" },
        { id: "file.open", label: { en: "Open project…", fa: "بازکردن پروژه…" }, window: "project", shortcut: "Ctrl+O" },
        separator("workspace.sep1"),
        { id: "file.open-layout", label: { en: "Open Layout…", fa: "بازکردن چیدمان…" }, command: "layout.open", disabledReason: caps.canOpenFieldChooser ? undefined : unavailable(REASONS.noFields, locale) },
        { id: "file.save-layout", label: { en: "Save Layout", fa: "ذخیرهٔ چیدمان" }, command: "layout.save", shortcut: "Ctrl+S", disabledReason: layoutReason },
        { id: "file.save-layout-as", label: { en: "Save Layout As…", fa: "ذخیرهٔ چیدمان با نام…" }, command: "layout.save-as", disabledReason: layoutReason },
        separator("workspace.sep2"),
        { id: "file.settings", label: { en: "Project properties…", fa: "مشخصات پروژه…" }, command: "project.settings" },
        { id: "file.interchange", label: { en: "Import / Export…", fa: "ورود / خروجی…" }, command: "project.interchange" },
        separator("workspace.sep3"),
        { id: "file.print", label: { en: "Print…", fa: "چاپ…" }, command: "file.print", shortcut: "Ctrl+P" },
        { id: "file.refresh", label: { en: "Refresh data", fa: "به‌روزرسانی داده" }, command: "workspace.refresh", shortcut: "F5" },
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
      accessKey: "e",
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
        separator("edit.sep1"),
        { id: "edit.cut", label: { en: "Cut", fa: "برش" }, shortcut: "Ctrl+X", disabledReason: unavailable(REASONS.clipboard, locale) },
        { id: "edit.copy", label: { en: "Copy", fa: "کپی" }, shortcut: "Ctrl+C", disabledReason: unavailable(REASONS.clipboard, locale) },
        { id: "edit.paste", label: { en: "Paste", fa: "چسباندن" }, shortcut: "Ctrl+V", disabledReason: unavailable(REASONS.clipboard, locale) },
        { id: "edit.delete", label: { en: "Delete", fa: "حذف" }, shortcut: "Del", disabledReason: unavailable(REASONS.deleteActivity, locale) },
        separator("edit.sep2"),
        { id: "edit.find", label: { en: "Find activities…", fa: "یافتن فعالیت‌ها…" }, command: "edit.find", shortcut: "Ctrl+F" },
        { id: "edit.group-wbs", label: { en: "Group by WBS", fa: "گروه‌بندی بر اساس WBS" }, command: "edit.group-wbs", checked: caps.groupByWbs },
        { id: "edit.sort-toggle", label: { en: "Reverse sort direction", fa: "معکوس کردن جهت ترتیب" }, command: "edit.sort-toggle" },
        separator("edit.sep3"),
        {
          id: "edit.select-all",
          label: { en: "Select All Activities", fa: "انتخاب همهٔ فعالیت‌ها" },
          command: "edit.select-all",
          shortcut: "Ctrl+A",
          disabledReason: caps.hasActivities ? undefined : unavailable(REASONS.noActivities, locale),
        },
        {
          id: "edit.link",
          label: { en: "Link Activities…", fa: "پیوند فعالیت‌ها…" },
          command: "edit.link",
          disabledReason: caps.hasSelectedActivity ? undefined : unavailable(REASONS.noSelection, locale),
        },
        {
          id: "edit.unlink",
          label: { en: "Unlink Activities…", fa: "قطع پیوند فعالیت‌ها…" },
          command: "edit.unlink",
          disabledReason: !caps.hasMultiSelection
            ? unavailable(REASONS.noMultiSelection, locale)
            : caps.hasRelationships ? undefined : unavailable(REASONS.noRelationships, locale),
        },
        { id: "edit.fill-down", label: { en: "Fill Down", fa: "پرکردن به پایین" }, shortcut: "Ctrl+E", disabledReason: unavailable(REASONS.fillDown, locale) },
        { id: "edit.dissolve", label: { en: "Dissolve", fa: "انحلال" }, disabledReason: unavailable(REASONS.dissolve, locale) },
      ],
    },
    {
      id: "view",
      accessKey: "v",
      label: { en: "View", fa: "نما" },
      items: [
        {
          id: "view.fields",
          label: { en: "Columns…", fa: "ستون‌ها…" },
          command: "view.fields",
          disabledReason: caps.canOpenFieldChooser ? undefined : unavailable(REASONS.noFields, locale),
        },
        { id: "view.filters", label: { en: "Filters…", fa: "فیلترها…" }, command: "dialog.filters" },
        { id: "view.group-sort", label: { en: "Group and Sort…", fa: "گروه‌بندی و ترتیب…" }, command: "dialog.group-sort" },
        { id: "view.timescale", label: { en: "Timescale…", fa: "مقیاس زمانی…" }, command: "dialog.timescale" },
        { id: "view.bars", label: { en: "Bar Styles…", fa: "سبک میله‌ها…" }, command: "dialog.bars" },
        { id: "view.font-row", label: { en: "Table Font and Row…", fa: "قلم و ردیف جدول…" }, command: "dialog.font-row" },
        { id: "view.preferences", label: { en: "User Preferences…", fa: "ترجیحات کاربر…" }, command: "dialog.user-preferences" },
        { id: "view.line-numbers", label: { en: "Line Numbers", fa: "شمارهٔ ردیف" }, command: "view.line-numbers", checked: presentation.table.lineNumbers },
        separator("view.sep1"),
        {
          id: "view.expand-all",
          label: { en: "Expand All", fa: "بازکردن همه" },
          command: "view.expand-all",
          shortcut: "Ctrl+Num +",
          disabledReason: caps.hasWbs && caps.groupByWbs ? undefined : unavailable(REASONS.noWbsGroup, locale),
        },
        {
          id: "view.collapse-all",
          label: { en: "Collapse All", fa: "بستن همه" },
          command: "view.collapse-all",
          shortcut: "Ctrl+Num -",
          disabledReason: caps.hasWbs && caps.groupByWbs ? undefined : unavailable(REASONS.noWbsGroup, locale),
        },
        {
          id: "view.collapse-to",
          label: { en: "Collapse To…", fa: "بستن تا…" },
          command: "view.collapse-to",
          disabledReason: caps.hasWbs && caps.groupByWbs ? undefined : unavailable(REASONS.noWbsGroup, locale),
        },
        { id: "view.zoom-in", label: { en: "Zoom in", fa: "بزرگ‌نمایی" }, command: "view.zoom-in" },
        { id: "view.zoom-out", label: { en: "Zoom out", fa: "کوچک‌نمایی" }, command: "view.zoom-out" },
        { id: "view.fit", label: { en: "Fit to window", fa: "تناسب با پنجره" }, command: "view.fit" },
        { id: "view.toggle-wbs", label: { en: "Show project WBS", fa: "نمایش WBS پروژه" }, command: "view.toggle-wbs" },
        { id: "view.toggle-gantt", label: { en: "Show Gantt Chart", fa: "نمایش گانت" }, command: "view.toggle-gantt" },
        {
          id: "view.toggle-details",
          label: state.detailsVisible === false
            ? { en: "Show Details", fa: "نمایش جزئیات" }
            : { en: "Hide Details", fa: "پنهان کردن جزئیات" },
          command: "view.toggle-details",
          checked: state.detailsVisible !== false,
        },
        separator("view.sep-layouts"),
        {
          id: "view.top-table",
          label: { en: "Show on Top: Activity Table", fa: "نمایش در بالا: جدول فعالیت‌ها" },
          command: "view.top-table",
          checked: state.activityTopLayout === "table-only",
          disabledReason: layoutScopeOk ? undefined : layoutScopeReason,
        },
        {
          id: "view.top-table-gantt",
          label: { en: "Show on Top: Table + Gantt Chart", fa: "نمایش در بالا: جدول + نمودار گانت" },
          command: "view.top-table-gantt",
          checked: (state.activityTopLayout ?? "table-gantt") === "table-gantt",
          disabledReason: layoutScopeOk ? undefined : layoutScopeReason,
        },
        {
          id: "view.top-network",
          label: { en: "Show on Top: Activity Network", fa: "نمایش در بالا: شبکهٔ فعالیت‌ها" },
          command: "view.top-network",
          checked: state.activityTopLayout === "activity-network",
          disabledReason: !layoutScopeOk ? layoutScopeReason : caps.hasRelationships ? undefined : unavailable(REASONS.noRelationships, locale),
        },
        {
          id: "view.bottom-details",
          label: { en: "Show on Bottom: Activity Details", fa: "نمایش در پایین: جزئیات فعالیت" },
          command: "view.bottom-details",
          checked: (state.activityBottomLayout ?? "details") === "details",
          disabledReason: layoutScopeOk ? undefined : layoutScopeReason,
        },
        {
          id: "view.bottom-trace",
          label: { en: "Show on Bottom: Trace Logic", fa: "نمایش در پایین: ردیابی منطق" },
          command: "view.bottom-trace",
          checked: state.activityBottomLayout === "trace-logic",
          disabledReason: !layoutScopeOk
            ? layoutScopeReason
            : caps.hasSelectedActivity && caps.hasRelationships ? undefined : unavailable(caps.hasSelectedActivity ? REASONS.noRelationships : REASONS.noSelection, locale),
        },
        {
          id: "view.bottom-usage-spreadsheet",
          label: { en: "Show on Bottom: Activity Usage Spreadsheet", fa: "نمایش در پایین: صفحه‌گستردهٔ مصرف فعالیت" },
          command: "view.bottom-usage-spreadsheet",
          checked: state.activityBottomLayout === "usage-spreadsheet",
          disabledReason: !layoutScopeOk
            ? layoutScopeReason
            : caps.hasAssignmentPeriods ? undefined : unavailable(REASONS.noAssignmentPeriods, locale),
        },
        {
          id: "view.bottom-usage-profile",
          label: { en: "Show on Bottom: Activity Usage Profile", fa: "نمایش در پایین: نیم‌رخ مصرف فعالیت" },
          command: "view.bottom-usage-profile",
          checked: state.activityBottomLayout === "usage-profile",
          disabledReason: !layoutScopeOk
            ? layoutScopeReason
            : caps.hasAssignmentPeriods ? undefined : unavailable(REASONS.noAssignmentPeriods, locale),
        },
        {
          id: "view.bottom-none",
          label: { en: "Show on Bottom: None", fa: "نمایش در پایین: بدون نما" },
          command: "view.bottom-none",
          checked: state.activityBottomLayout === "none",
          disabledReason: layoutScopeOk ? undefined : layoutScopeReason,
        },
        separator("view.sep2"),
        { id: "view.calendar", label: { en: "Switch calendar display", fa: "تغییر تقویم نمایش" }, command: "admin.calendar" },
        ...WORKSPACE_TOOLBAR_GROUPS.map((group) => ({
          id: `view.toolbar-${group}`,
          label: { en: `Toolbar: ${toolbarLabel(group)}`, fa: `نوار ابزار: ${toolbarLabel(group)}` },
          command: `view.toolbar-${group}` as DesktopCommand,
          checked: !hidden.has(group),
        })),
        separator("view.sep3"),
        { id: "view.theme-classic", label: { en: "CUBI Classic — Version 26 Reference", fa: "CUBI کلاسیک — مرجع نسخه ۲۶" }, command: "view.theme-classic", checked: (state.theme ?? "classic") === "classic" },
        { id: "view.theme-modern", label: { en: "CUBI Modern 3D", fa: "CUBI مدرن سه‌بعدی" }, command: "view.theme-modern", checked: state.theme === "modern" },
        { id: "view.theme-graphite", label: { en: "CUBI Graphite", fa: "CUBI گرافیت" }, command: "view.theme-graphite", checked: state.theme === "graphite" },
        { id: "view.theme-arctic", label: { en: "CUBI Arctic", fa: "CUBI قطبی" }, command: "view.theme-arctic", checked: state.theme === "arctic" },
        { id: "view.theme-copper", label: { en: "CUBI Copper", fa: "CUBI مس" }, command: "view.theme-copper", checked: state.theme === "copper" },
        { id: "view.theme-midnight", label: { en: "CUBI Midnight", fa: "CUBI نیمه‌شب" }, command: "view.theme-midnight", checked: state.theme === "midnight" },
        separator("view.sep4"),
        ...state.openWindows.map((key, index) => windowItem(key, index < 9 ? `Alt+${index + 1}` : undefined)),
        {
          id: "view.close-window",
          label: { en: "Close current window", fa: "بستن پنجرهٔ جاری" },
          command: "project.close",
          disabledReason: caps.hasMultipleWindows ? undefined : unavailable(REASONS.singleWindow, locale),
        },
      ],
    },
    {
      id: "project",
      accessKey: "p",
      label: { en: "Project", fa: "پروژه" },
      items: [
        { id: "project.settings", label: { en: "Project properties…", fa: "مشخصات پروژه…" }, command: "project.settings" },
        { id: "project.add-wbs", label: { en: "Add WBS element", fa: "افزودن عنصر WBS" }, command: "project.add-wbs" },
        {
          id: "project.add-activity",
          label: { en: "Add activity", fa: "افزودن فعالیت" },
          command: "project.add-activity",
          shortcut: "Insert",
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
        {
          id: "project.additional-activities",
          label: { en: "Additional Activities View", fa: "نمای فعالیت‌های تکمیلی" },
          disabledReason: unavailable(REASONS.additionalActivities, locale),
        },
        { id: "project.schedule", label: { en: "Schedule activities", fa: "زمان‌بندی فعالیت‌ها" }, command: "tools.run-schedule", shortcut: "F9" },
        { id: "project.schedule-options", label: { en: "Schedule options", fa: "تنظیمات زمان‌بندی" }, command: "project.schedule-options" },
        { id: "project.formula", label: { en: "Formula editor", fa: "ویرایشگر فرمول" }, command: "tools.formula" },
        { id: "project.reference", label: { en: "Scheduling reference", fa: "مرجع زمان‌بندی" }, command: "tools.reference" },
        separator("project.sep1"),
        { id: "project.assign-resources", label: { en: "Assign resources…", fa: "تخصیص منابع…" }, command: "activity.assign-resources" },
        { id: "project.predecessors", label: { en: "Assign predecessors…", fa: "تخصیص پیش‌نیاز…" }, command: "activity.predecessors" },
        { id: "project.successors", label: { en: "Assign successors…", fa: "تخصیص پس‌نیاز…" }, command: "activity.successors" },
        { id: "project.level", label: { en: "Level resources…", fa: "تسطیح منابع…" }, disabledReason: unavailable(REASONS.leveling, locale) },
        { id: "project.baseline", label: { en: "Baselines…", fa: "خطوط مبنا…" }, disabledReason: unavailable(REASONS.baseline, locale) },
        { id: "project.compare", label: { en: "Compare baselines…", fa: "مقایسهٔ خطوط مبنا…" }, disabledReason: unavailable(REASONS.compare, locale) },
        { id: "project.progress", label: { en: "Update progress…", fa: "به‌روزرسانی پیشرفت…" }, disabledReason: unavailable(REASONS.progress, locale) },
      ],
    },
    {
      id: "organization",
      accessKey: "n",
      label: { en: "Enterprise", fa: "سازمان" },
      items: [
        { id: "enterprise.projects", label: WINDOW_TITLES.project, window: "project" },
        { id: "enterprise.resources", label: WINDOW_TITLES.resources, window: "resources" },
        { id: "enterprise.assignments", label: { en: "Resource assignments", fa: "تخصیص منابع" }, window: "assignments" },
        { id: "enterprise.roles", label: { en: "Roles…", fa: "نقش‌ها…" }, window: "roles" },
        { id: "enterprise.calendars", label: { en: "Calendars…", fa: "تقویم‌ها…" }, window: "calendars" },
        { id: "enterprise.udfs", label: { en: "User defined fields…", fa: "فیلدهای سفارشی…" }, disabledReason: unavailable(REASONS.udfs, locale) },
        { id: "enterprise.forms", label: { en: "Forms & Workflows…", fa: "فرم‌ها و گردش‌کار…" }, command: "forms.open" },
      ],
    },
    {
      id: "tools",
      accessKey: "t",
      label: { en: "Tools", fa: "ابزارها" },
      items: [
        { id: "tools.forms", label: { en: "Forms & Workflows…", fa: "فرم‌ها و گردش‌کار…" }, command: "forms.open" },
        { id: "tools.search", label: { en: "Search activities", fa: "جست‌وجوی فعالیت‌ها" }, command: "edit.find", shortcut: "Ctrl+F" },
        { id: "tools.preferences", label: { en: "User Preferences…", fa: "ترجیحات کاربر…" }, command: "dialog.user-preferences" },
        { id: "tools.reports", label: WINDOW_TITLES.reports, window: "reports" },
        { id: "tools.import-export", label: { en: "Project CSV Import / Export…", fa: "ورود / خروجی CSV پروژه…" }, window: "exchange" },
        { id: "tools.backup", label: { en: "Project Backup / Recovery…", fa: "پشتیبان‌گیری / بازیابی پروژه…" }, window: "backup" },
        { id: "tools.print-preview", label: { en: "Print preview", fa: "پیش‌نمایش چاپ" }, command: "file.print" },
        { id: "tools.generate-report", label: { en: "Report wizard…", fa: "جادوگر گزارش…" }, disabledReason: unavailable(REASONS.reports, locale) },
        { id: "tools.language", label: { en: "Switch language", fa: "تغییر زبان" }, command: "admin.language" },
        { id: "tools.help", label: { en: "Keyboard shortcuts", fa: "کلیدهای میانبر" }, command: "help.shortcuts", shortcut: "F1" },
      ],
    },
  ];
  // Administration is a first-class, role-gated menu. Non-administrators keep
  // the same workspace; they simply do not see administration commands.
  if (caps.canAdminister !== false) {
    menus.push({
      id: "administration",
      accessKey: "a",
      label: { en: "Admin", fa: "مدیریت" },
      items: [
        { id: "admin.window", label: WINDOW_TITLES.settings, window: "settings" },
        { id: "admin.preferences", label: { en: "User Preferences…", fa: "ترجیحات کاربر…" }, command: "dialog.user-preferences" },
        { id: "admin.language", label: { en: "Language", fa: "زبان" }, command: "admin.language" },
        { id: "admin.calendar", label: { en: "Calendar display", fa: "نمایش تقویم" }, command: "admin.calendar" },
        separator("admin.sep1"),
        { id: "admin.users", label: { en: "Users…", fa: "کاربران…" }, disabledReason: unavailable(REASONS.users, locale) },
        { id: "admin.security", label: { en: "Security profiles…", fa: "پروفایل‌های امنیتی…" }, disabledReason: unavailable(REASONS.security, locale) },
        { id: "admin.permissions", label: { en: "Permission matrix…", fa: "ماتریس دسترسی…" }, window: "administration" },
        { id: "admin.categories", label: { en: "Categories…", fa: "دسته‌ها…" }, window: "administration" },
        { id: "admin.currencies", label: { en: "Currencies…", fa: "ارزها…" }, disabledReason: unavailable(REASONS.currencies, locale) },
        { id: "admin.periods", label: { en: "Financial period calendars…", fa: "تقویم دوره‌های مالی…" }, window: "administration" },
        { id: "admin.audit", label: { en: "Audit history…", fa: "تاریخچهٔ ممیزی…" }, disabledReason: unavailable(REASONS.audit, locale) },
        { id: "admin.recovery", label: { en: "Recovery…", fa: "بازیابی…" }, window: "backup" },
      ],
    });
  }
  menus.push({
    id: "help",
    accessKey: "h",
    label: { en: "Help", fa: "راهنما" },
    items: [
      { id: "help.shortcuts", label: { en: "Keyboard shortcuts", fa: "کلیدهای میانبر" }, command: "help.shortcuts", shortcut: "F1" },
      { id: "help.about", label: { en: "About CUBI Workspace", fa: "دربارهٔ محیط کار CUBI" }, command: "help.about" },
    ],
  });
  return menus;
}

export function toolbarGroupLabel(group: WorkspaceToolbarGroup, locale: string): string {
  const pack = WORKSPACE_TOOLBAR_LABELS[locale as keyof typeof WORKSPACE_TOOLBAR_LABELS]
    ?? WORKSPACE_TOOLBAR_LABELS.en;
  return pack[group];
}

/**
 * The toolbar is organised into the same families the View menu lists. A family
 * only appears when the active window can use it, so every visible button runs
 * a command in the current context instead of showing unrelated chrome.
 */
export function getDesktopToolbar(state: DesktopShellState): DesktopToolbarItem[] {
  const { capabilities: caps, locale } = state;
  const presentation = state.presentation ?? DEFAULT_PRESENTATION;
  const why = (label: LocalizedLabel): LocalizedLabel => unavailable(label, locale);
  const items: DesktopToolbarItem[] = [
    // Standard: file and session commands that apply to the whole workspace.
    { id: "toolbar.new", label: { en: "New", fa: "جدید" }, title: { en: "New project", fa: "پروژهٔ جدید" }, window: "project", shortcut: "Ctrl+N", icon: "plus", group: "workspace" },
    { id: "toolbar.open", label: { en: "Open", fa: "بازکردن" }, title: { en: "Open project", fa: "بازکردن پروژه" }, window: "project", shortcut: "Ctrl+O", icon: "open", group: "workspace" },
    { id: "toolbar.close-window", label: { en: "Close Window", fa: "بستن پنجره" }, title: { en: "Close the current window", fa: "بستن پنجرهٔ جاری" }, command: "project.close", shortcut: "Ctrl+W", disabledReason: caps.hasMultipleWindows ? undefined : why(REASONS.singleWindow), icon: "close", group: "workspace" },
    { id: "toolbar.refresh", label: { en: "Refresh", fa: "به‌روزرسانی" }, title: { en: "Refresh project data", fa: "به‌روزرسانی داده‌های پروژه" }, command: "workspace.refresh", shortcut: "F5", icon: "refresh", group: "workspace" },

    // Edit: direct manipulation of the selected activity rows.
    { id: "toolbar.undo", label: { en: "Undo", fa: "بازگردانی" }, title: { en: "Undo layout change", fa: "بازگردانی تغییر چیدمان" }, command: "edit.undo", shortcut: "Ctrl+Z", disabledReason: caps.canUndoLayout ? undefined : why(REASONS.undo), icon: "undo", group: "edit" },
    { id: "toolbar.redo", label: { en: "Redo", fa: "تکرار" }, title: { en: "Redo layout change", fa: "اعمال دوبارهٔ تغییر چیدمان" }, command: "edit.redo", shortcut: "Ctrl+Y", disabledReason: caps.canRedoLayout ? undefined : why(REASONS.redo), icon: "redo", group: "edit" },
    { id: "toolbar.cut", label: { en: "Cut", fa: "برش" }, title: { en: "Cut", fa: "برش" }, shortcut: "Ctrl+X", disabledReason: why(REASONS.clipboard), icon: "cut", group: "edit" },
    { id: "toolbar.copy", label: { en: "Copy", fa: "کپی" }, title: { en: "Copy", fa: "کپی" }, shortcut: "Ctrl+C", disabledReason: why(REASONS.clipboard), icon: "copy", group: "edit" },
    { id: "toolbar.paste", label: { en: "Paste", fa: "چسباندن" }, title: { en: "Paste", fa: "چسباندن" }, shortcut: "Ctrl+V", disabledReason: why(REASONS.clipboard), icon: "paste", group: "edit" },
    { id: "toolbar.delete", label: { en: "Delete", fa: "حذف" }, title: { en: "Delete the selected activity", fa: "حذف فعالیت انتخاب‌شده" }, shortcut: "Del", disabledReason: why(REASONS.deleteActivity), icon: "delete", group: "edit" },
    { id: "toolbar.find", label: { en: "Find", fa: "یافتن" }, title: { en: "Find activities", fa: "یافتن فعالیت‌ها" }, command: "edit.find", shortcut: "Ctrl+F", icon: "find", group: "edit" },
    { id: "toolbar.select-all", label: { en: "Select All", fa: "انتخاب همه" }, title: { en: "Select every visible activity row", fa: "انتخاب همهٔ ردیف‌های نمایان فعالیت" }, command: "edit.select-all", shortcut: "Ctrl+A", disabledReason: caps.hasActivities ? undefined : why(REASONS.noActivities), icon: "check", group: "edit", windows: ["schedule"] },
    { id: "toolbar.link", label: { en: "Link", fa: "پیوند" }, title: { en: "Link the selected activities", fa: "پیوند فعالیت‌های انتخاب‌شده" }, command: "edit.link", disabledReason: caps.hasSelectedActivity ? undefined : why(REASONS.noSelection), icon: "link", group: "edit", windows: ["schedule"] },
    { id: "toolbar.unlink", label: { en: "Unlink", fa: "قطع پیوند" }, title: { en: "Remove relationships between the selected activities", fa: "حذف روابط میان فعالیت‌های انتخاب‌شده" }, command: "edit.unlink", disabledReason: !caps.hasMultiSelection ? why(REASONS.noMultiSelection) : caps.hasRelationships ? undefined : why(REASONS.noRelationships), icon: "unlink", group: "edit", windows: ["schedule"] },
    { id: "toolbar.fill-down", label: { en: "Fill Down", fa: "پرکردن به پایین" }, title: { en: "Copy the first selected value down the column", fa: "کپی مقدار ردیف اول در ستون" }, shortcut: "Ctrl+E", disabledReason: why(REASONS.fillDown), icon: "fill", group: "edit", windows: ["schedule"] },
    { id: "toolbar.dissolve", label: { en: "Dissolve", fa: "انحلال" }, title: { en: "Dissolve the selected WBS band", fa: "انحلال باند WBS انتخاب‌شده" }, disabledReason: why(REASONS.dissolve), icon: "dissolve", group: "edit", windows: ["schedule", "wbs"] },

    // Layout: the Version 26 Layout toolbar owns every presentation command.
    { id: "toolbar.open-layout", label: { en: "Open Layout", fa: "بازکردن چیدمان" }, title: { en: "Open a saved activity layout", fa: "بازکردن چیدمان ذخیره‌شدهٔ فعالیت‌ها" }, command: "layout.open", disabledReason: caps.canOpenFieldChooser ? undefined : why(REASONS.noFields), icon: "folder", group: "layout", windows: ["schedule"] },
    { id: "toolbar.save-layout", label: { en: "Save", fa: "ذخیره" }, title: { en: "Save layout", fa: "ذخیرهٔ چیدمان" }, command: "layout.save", shortcut: "Ctrl+S", disabledReason: caps.hasLayout ? undefined : why(REASONS.noLayout), icon: "save", group: "layout", windows: ["schedule"] },
    { id: "toolbar.save-as", label: { en: "Save As", fa: "ذخیره با نام" }, title: { en: "Save the layout under a new name", fa: "ذخیرهٔ چیدمان با نام جدید" }, command: "layout.save-as", disabledReason: caps.hasLayout ? undefined : why(REASONS.noLayout), icon: "saveAs", group: "layout", windows: ["schedule"] },
    { id: "toolbar.bars", label: { en: "Bars", fa: "میله‌ها" }, title: { en: "Bar styles", fa: "سبک میله‌ها" }, command: "dialog.bars", icon: "bars", group: "layout", windows: ["schedule", "wbs"] },
    { id: "toolbar.columns", label: { en: "Columns", fa: "ستون‌ها" }, title: { en: "Activity field layout", fa: "چیدمان فیلدهای فعالیت" }, command: "view.fields", disabledReason: caps.canOpenFieldChooser ? undefined : why(REASONS.noFields), icon: "columns", group: "layout", windows: ["schedule"] },
    { id: "toolbar.timescale", label: { en: "Timescale", fa: "مقیاس زمانی" }, title: { en: "Timescale dialog", fa: "دیالوگ مقیاس زمانی" }, command: "dialog.timescale", icon: "clock", group: "layout", windows: ["schedule", "wbs"] },
    { id: "toolbar.filters", label: { en: "Filters", fa: "فیلترها" }, title: { en: "Filter activities", fa: "پالایش فعالیت‌ها" }, command: "dialog.filters", icon: "filter", group: "layout", windows: ["schedule"] },
    { id: "toolbar.group-sort", label: { en: "Group & Sort", fa: "گروه و ترتیب" }, title: { en: "Group and sort dialog", fa: "دیالوگ گروه‌بندی و ترتیب" }, command: "dialog.group-sort", icon: "sort", group: "layout", windows: ["schedule"] },
    { id: "toolbar.group-wbs", label: { en: "Group WBS", fa: "گروه WBS" }, title: { en: "Group activities by WBS", fa: "گروه‌بندی فعالیت‌ها بر اساس WBS" }, command: "edit.group-wbs", active: caps.groupByWbs, icon: "group", group: "layout", windows: ["schedule"] },
    { id: "toolbar.line-numbers", label: { en: "Line Numbers", fa: "شمارهٔ ردیف" }, title: { en: "Show or hide row numbers in the activity table", fa: "نمایش یا پنهان‌کردن شمارهٔ ردیف در جدول فعالیت‌ها" }, command: "view.line-numbers", active: presentation.table.lineNumbers, icon: "lineNumbers", group: "layout", windows: ["schedule"] },
    { id: "toolbar.font-row", label: { en: "Table Font", fa: "قلم جدول" }, title: { en: "Table font, colours and row height", fa: "قلم، رنگ و ارتفاع ردیف جدول" }, command: "dialog.font-row", icon: "rowHeight", group: "layout", windows: ["schedule"] },
    { id: "toolbar.preferences", label: { en: "User Preferences", fa: "ترجیحات کاربر" }, title: { en: "User preferences for the table and bars", fa: "ترجیحات کاربر برای جدول و میله‌ها" }, command: "dialog.user-preferences", icon: "settings", group: "layout" },

    // Display: view-only adjustments that never change stored data.
    { id: "toolbar.zoom-in", label: { en: "Zoom In", fa: "بزرگ‌نمایی" }, title: { en: "Zoom in on the timescale", fa: "بزرگ‌نمایی مقیاس زمانی" }, command: "view.zoom-in", icon: "zoomIn", group: "view" },
    { id: "toolbar.zoom-out", label: { en: "Zoom Out", fa: "کوچک‌نمایی" }, title: { en: "Zoom out of the timescale", fa: "کوچک‌نمایی مقیاس زمانی" }, command: "view.zoom-out", icon: "zoomOut", group: "view" },
    { id: "toolbar.fit", label: { en: "Fit", fa: "تناسب" }, title: { en: "Fit the Gantt to the window", fa: "تناسب گانت با پنجره" }, command: "view.fit", icon: "fit", group: "view" },
    { id: "toolbar.expand-all", label: { en: "Expand All", fa: "بازکردن همه" }, title: { en: "Expand every WBS band", fa: "بازکردن همهٔ باندهای WBS" }, command: "view.expand-all", shortcut: "Ctrl+Num +", disabledReason: caps.hasWbs && caps.groupByWbs ? undefined : why(REASONS.noWbsGroup), icon: "expand", group: "view", windows: ["schedule", "wbs"] },
    { id: "toolbar.collapse-all", label: { en: "Collapse All", fa: "بستن همه" }, title: { en: "Collapse every WBS band", fa: "بستن همهٔ باندهای WBS" }, command: "view.collapse-all", shortcut: "Ctrl+Num -", disabledReason: caps.hasWbs && caps.groupByWbs ? undefined : why(REASONS.noWbsGroup), icon: "collapse", group: "view", windows: ["schedule", "wbs"] },
    { id: "toolbar.collapse-to", label: { en: "Collapse To", fa: "بستن تا" }, title: { en: "Pick the WBS branch that stays open", fa: "انتخاب شاخهٔ WBS که باز می‌ماند" }, command: "view.collapse-to", disabledReason: caps.hasWbs && caps.groupByWbs ? undefined : why(REASONS.noWbsGroup), icon: "collapseTo", group: "view", windows: ["schedule", "wbs"] },
    { id: "toolbar.panels", label: { en: "Panels", fa: "پنل‌ها" }, title: { en: "Show or hide the details panel", fa: "نمایش یا پنهان‌کردن پنل جزئیات" }, command: "view.toggle-details", active: state.detailsVisible !== false, icon: "panels", group: "view" },
    { id: "toolbar.fullscreen", label: { en: "Full Screen", fa: "تمام‌صفحه" }, title: { en: "Enter full screen", fa: "ورود به تمام‌صفحه" }, fullscreen: true, icon: "fullscreen", group: "view" },
    { id: "toolbar.help", label: { en: "Help", fa: "راهنما" }, title: { en: "Keyboard shortcuts", fa: "کلیدهای میانبر" }, command: "help.shortcuts", shortcut: "F1", icon: "help", group: "view" },

    // Project: the Version 26 project toolbar opens the project windows.
    { id: "toolbar.properties", label: { en: "Properties", fa: "مشخصات" }, title: { en: "Project properties", fa: "مشخصات پروژه" }, command: "project.settings", icon: "project", group: "project" },
    { id: "toolbar.activities-window", label: { en: "Activities", fa: "فعالیت‌ها" }, title: { en: "Open the Activities window", fa: "بازکردن پنجرهٔ فعالیت‌ها" }, window: "schedule", icon: "activity", group: "project" },
    { id: "toolbar.wbs-window", label: { en: "WBS", fa: "ساختار شکست" }, title: { en: "Open the WBS window", fa: "بازکردن پنجرهٔ WBS" }, window: "wbs", icon: "wbs", group: "project" },
    { id: "toolbar.assignments-window", label: { en: "Resource Assignments", fa: "تخصیص منابع" }, title: { en: "Open Resource Assignments", fa: "بازکردن تخصیص منابع" }, window: "assignments", icon: "assignment", group: "project" },
    { id: "toolbar.documents-window", label: { en: "Work Products & Docs", fa: "محصولات کار و اسناد" }, title: { en: "Open the Documents window", fa: "بازکردن پنجرهٔ اسناد" }, window: "documents", icon: "documents", group: "project" },
    { id: "toolbar.expenses-window", label: { en: "Expenses", fa: "هزینه‌ها" }, title: { en: "Open the Expenses window", fa: "بازکردن پنجرهٔ هزینه‌ها" }, window: "expenses", icon: "money", group: "project" },
    { id: "toolbar.thresholds-window", label: { en: "Thresholds", fa: "آستانه‌ها" }, title: { en: "Open the Thresholds window", fa: "بازکردن پنجرهٔ آستانه‌ها" }, window: "thresholds", icon: "thresholds", group: "project" },
    { id: "toolbar.issues-window", label: { en: "Issues", fa: "مسائل" }, title: { en: "Open the Issues window", fa: "بازکردن پنجرهٔ مسائل" }, window: "issues", icon: "issues", group: "project" },
    { id: "toolbar.risks-window", label: { en: "Risks", fa: "ریسک‌ها" }, title: { en: "Open the Risks window", fa: "بازکردن پنجرهٔ ریسک‌ها" }, window: "risks", icon: "risks", group: "project" },
    { id: "toolbar.baseline", label: { en: "Baselines", fa: "خطوط مبنا" }, title: { en: "Baselines", fa: "خطوط مبنا" }, disabledReason: why(REASONS.baseline), icon: "baseline", group: "project" },

    // Activities: the row-level commands for the selected activity.
    { id: "toolbar.add-activity", label: { en: "Add Activity", fa: "افزودن فعالیت" }, title: { en: "Add activity", fa: "افزودن فعالیت" }, command: "project.add-activity", disabledReason: caps.hasWbs ? undefined : why(REASONS.noWbs), icon: "activity", group: "activities", windows: ["schedule"] },
    { id: "toolbar.edit-activity", label: { en: "Edit", fa: "ویرایش" }, title: { en: "Edit selected activity", fa: "ویرایش فعالیت انتخاب‌شده" }, command: "project.edit-activity", disabledReason: caps.hasSelectedActivity ? undefined : why(REASONS.noSelection), icon: "edit", group: "activities", windows: ["schedule"] },
    { id: "toolbar.schedule", label: { en: "Schedule", fa: "زمان‌بندی" }, title: { en: "Schedule activities", fa: "زمان‌بندی فعالیت‌ها" }, command: "tools.run-schedule", shortcut: "F9", icon: "calendar", group: "activities", windows: ["schedule"] },
    { id: "toolbar.schedule-options", label: { en: "Options", fa: "تنظیمات" }, title: { en: "Schedule options", fa: "تنظیمات زمان‌بندی" }, command: "project.schedule-options", icon: "settings", group: "activities", windows: ["schedule"] },
    { id: "toolbar.predecessors", label: { en: "Predecessors", fa: "پیش‌نیازها" }, title: { en: "Assign predecessors", fa: "تخصیص پیش‌نیاز" }, command: "activity.predecessors", icon: "link", group: "activities", windows: ["schedule"] },
    { id: "toolbar.successors", label: { en: "Successors", fa: "پس‌نیازها" }, title: { en: "Assign successors", fa: "تخصیص پس‌نیاز" }, command: "activity.successors", icon: "network", group: "activities", windows: ["schedule"] },

    { id: "toolbar.add-wbs", label: { en: "Add WBS", fa: "افزودن WBS" }, title: { en: "Add WBS element", fa: "افزودن عنصر WBS" }, command: "project.add-wbs", icon: "tree", group: "wbs", windows: ["schedule", "wbs", "project"] },
    // Chart: chart-local presentation that is not stored in the layout.
    { id: "toolbar.gantt", label: { en: "Gantt", fa: "گانت" }, title: { en: "Show or hide the Gantt chart", fa: "نمایش یا پنهان‌کردن نمودار گانت" }, command: "view.toggle-gantt", active: state.ganttVisible !== false, icon: "gantt", group: "gantt", windows: ["schedule", "wbs"] },

    { id: "toolbar.resources", label: { en: "Resources", fa: "منابع" }, title: { en: "Open the Resources window", fa: "بازکردن پنجرهٔ منابع" }, window: "resources", icon: "resource", group: "resources", windows: ["resources", "assignments", "roles"] },
    { id: "toolbar.assign", label: { en: "Assign", fa: "تخصیص" }, title: { en: "Assign resources to the selected activity", fa: "تخصیص منابع به فعالیت انتخاب‌شده" }, command: "activity.assign-resources", icon: "link", group: "resources", windows: ["resources", "assignments", "schedule"] },

    { id: "toolbar.reports", label: { en: "Reports", fa: "گزارش‌ها" }, title: { en: "Open the Reports window", fa: "بازکردن پنجرهٔ گزارش‌ها" }, window: "reports", icon: "reports", group: "reports", windows: ["reports", "documents", "tracking"] },
    { id: "toolbar.tracking", label: { en: "Tracking", fa: "رهگیری" }, title: { en: "Open the Tracking window", fa: "بازکردن پنجرهٔ رهگیری" }, window: "tracking", icon: "tracking", group: "reports", windows: ["reports", "documents", "tracking"] },
    { id: "toolbar.print-preview", label: { en: "Print Preview", fa: "پیش‌نمایش چاپ" }, title: { en: "Print the current view", fa: "چاپ نمای جاری" }, command: "file.print", icon: "print", group: "reports", windows: ["reports", "documents", "tracking"] },

    { id: "toolbar.language", label: { en: "Language", fa: "زبان" }, title: { en: "Switch language", fa: "تغییر زبان" }, command: "admin.language", icon: "language", group: "tools" },
  ];
  return items.filter((item) => !item.windows || item.windows.includes(state.activeWindow));
}

export function getDesktopToolbarGroups(state: DesktopShellState): Array<{
  id: WorkspaceToolbarGroup;
  label: LocalizedLabel;
  items: DesktopToolbarItem[];
}> {
  const hidden = new Set(state.hiddenToolbarGroups ?? []);
  const groups = WORKSPACE_TOOLBAR_GROUPS
    .filter((group) => !hidden.has(group))
    .map((group) => ({
      id: group,
      label: { en: toolbarGroupLabel(group, state.locale), fa: toolbarGroupLabel(group, state.locale) },
      items: [] as DesktopToolbarItem[],
    }));
  for (const item of getDesktopToolbar(state)) {
    const group = groups.find((candidate) => candidate.id === item.group);
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
  if (item.separator) return `<div class="cp-menubar-separator" role="separator"></div>`;
  const disabled = Boolean(item.disabledReason);
  const reason = item.disabledReason ? pick(item.disabledReason, locale) : "";
  const target = item.window
    ? ` data-desktop-window="${escapeHtml(item.window)}"`
    : item.command
      ? ` data-desktop-command="${escapeHtml(item.command)}"`
      : "";
  const icon = desktopMenuIcon(item.id);
  return `<button type="button" role="menuitem" class="cp-menubar-item${disabled ? " is-disabled" : ""}${item.checked ? " is-checked" : ""}" data-desktop-item="${escapeHtml(item.id)}"${target}${disabled ? ' disabled aria-disabled="true"' : ""}${item.checked ? ' aria-checked="true"' : ""}${reason ? ` title="${escapeHtml(reason)}"` : ""}>
    <span class="cp-menubar-item-check" aria-hidden="true">${item.checked ? "✓" : ""}</span>
    <span class="cp-menubar-item-icon" aria-hidden="true">${icon ? workspaceIcon(icon) : ""}</span>
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
      <button type="button" class="cp-menubar-trigger" role="menuitem" aria-haspopup="true" aria-expanded="false" aria-keyshortcuts="Alt+${escapeHtml(menu.accessKey.toUpperCase())}" title="${escapeHtml(`Alt+${menu.accessKey.toUpperCase()}`)}" data-desktop-menu="${escapeHtml(menu.id)}" data-desktop-access="${escapeHtml(menu.accessKey)}">${escapeHtml(pick(menu.label, locale))}</button>
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
      ${groups.map((group) => `<div class="cp-toolbar-group" data-toolbar-group="${escapeHtml(group.id)}" role="group" aria-label="${escapeHtml(pick(group.label, locale))}" title="${escapeHtml(pick(group.label, locale))}">
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
  const reorderable = state.openWindows.length > 1;
  const dirty = new Set(state.dirtyWindows ?? []);
  const openWindowsAria = translateWorkspaceUiText(locale, "Open windows", "پنجره‌های باز");
  const closeWord = translateWorkspaceUiText(locale, "Close", "بستن");
  const unsaved = translateWorkspaceUiText(locale, "Unsaved changes", "تغییرات ذخیره‌نشده");
  return `<div class="cp-window-tabs" role="tablist" aria-label="${escapeHtml(openWindowsAria)}">
    ${state.openWindows.map((key) => {
      const selected = key === state.activeWindow;
      const title = pick(WINDOW_TITLES[key], locale);
      const isDirty = dirty.has(key);
      return `<span class="cp-window-tab${selected ? " is-active" : ""}${isDirty ? " is-dirty" : ""}" role="tab" aria-selected="${selected ? "true" : "false"}"${isDirty ? ' data-window-dirty="true"' : ""} data-window-tab="${escapeHtml(key)}" tabindex="${selected ? "0" : "-1"}"${reorderable ? ' draggable="true"' : ""}>
        <button type="button" class="cp-window-tab-label" data-window-open="${escapeHtml(key)}"${isDirty ? ` title="${escapeHtml(unsaved)}"` : ""}>${escapeHtml(title)}${isDirty ? `<span class="cp-window-tab-dirty" aria-label="${escapeHtml(unsaved)}"></span>` : ""}</button>
        ${closable ? `<button type="button" class="cp-window-tab-close" data-window-close="${escapeHtml(key)}" aria-label="${escapeHtml(closeWord + " " + title)}" title="${escapeHtml(closeWord + " " + title)}">×</button>` : ""}
      </span>`;
    }).join("")}
  </div>`;
}

/**
 * Shortcuts are a closed catalog independent of the menus: a key is either
 * executed here or listed as unavailable with the reason its service is
 * missing. Menus can therefore be reorganised without changing any binding.
 */
export type DesktopShortcutChord = {
  key?: string;
  code?: string;
  ctrlOrMeta?: boolean;
  alt?: boolean;
  shift?: boolean;
};

export type DesktopShortcut = {
  id: string;
  label: LocalizedLabel;
  keys: string;
  chord: DesktopShortcutChord;
  command?: DesktopCommand;
  window?: WorkspaceMenuKey;
  requires?: { test: (caps: DesktopShellCapabilities) => boolean; reason: LocalizedLabel };
  unavailable?: LocalizedLabel;
};

const DESKTOP_SHORTCUTS: readonly DesktopShortcut[] = [
  { id: "shortcut.new", label: { en: "New project", fa: "پروژهٔ جدید" }, keys: "Ctrl+N", chord: { key: "n", ctrlOrMeta: true }, window: "project" },
  { id: "shortcut.open", label: { en: "Open project", fa: "بازکردن پروژه" }, keys: "Ctrl+O", chord: { key: "o", ctrlOrMeta: true }, window: "project" },
  { id: "shortcut.close-window", label: { en: "Close window", fa: "بستن پنجره" }, keys: "Ctrl+W", chord: { key: "w", ctrlOrMeta: true }, command: "project.close", requires: { test: (caps) => caps.hasMultipleWindows, reason: REASONS.singleWindow } },
  { id: "shortcut.print", label: { en: "Print", fa: "چاپ" }, keys: "Ctrl+P", chord: { key: "p", ctrlOrMeta: true }, command: "file.print" },
  { id: "shortcut.save-layout", label: { en: "Save layout", fa: "ذخیرهٔ چیدمان" }, keys: "Ctrl+S", chord: { key: "s", ctrlOrMeta: true }, command: "layout.save", requires: { test: (caps) => caps.hasLayout, reason: REASONS.noLayout } },
  { id: "shortcut.undo", label: { en: "Undo layout change", fa: "بازگردانی تغییر چیدمان" }, keys: "Ctrl+Z", chord: { key: "z", ctrlOrMeta: true }, command: "edit.undo", requires: { test: (caps) => caps.canUndoLayout, reason: REASONS.undo } },
  { id: "shortcut.redo", label: { en: "Redo layout change", fa: "اعمال دوبارهٔ تغییر چیدمان" }, keys: "Ctrl+Y", chord: { key: "y", ctrlOrMeta: true }, command: "edit.redo", requires: { test: (caps) => caps.canRedoLayout, reason: REASONS.redo } },
  { id: "shortcut.cut", label: { en: "Cut", fa: "برش" }, keys: "Ctrl+X", chord: { key: "x", ctrlOrMeta: true }, unavailable: REASONS.clipboard },
  { id: "shortcut.copy", label: { en: "Copy", fa: "کپی" }, keys: "Ctrl+C", chord: { key: "c", ctrlOrMeta: true }, unavailable: REASONS.clipboard },
  { id: "shortcut.paste", label: { en: "Paste", fa: "چسباندن" }, keys: "Ctrl+V", chord: { key: "v", ctrlOrMeta: true }, unavailable: REASONS.clipboard },
  { id: "shortcut.delete", label: { en: "Delete activity", fa: "حذف فعالیت" }, keys: "Del", chord: { key: "Delete" }, unavailable: REASONS.deleteActivity },
  { id: "shortcut.insert", label: { en: "Insert activity", fa: "درج فعالیت" }, keys: "Ins", chord: { key: "Insert" }, command: "project.add-activity", requires: { test: (caps) => caps.hasWbs, reason: REASONS.noWbs } },
  { id: "shortcut.find", label: { en: "Find activities", fa: "یافتن فعالیت‌ها" }, keys: "Ctrl+F", chord: { key: "f", ctrlOrMeta: true }, command: "edit.find" },
  { id: "shortcut.select-all", label: { en: "Select all visible activities", fa: "انتخاب همهٔ فعالیت‌های نمایان" }, keys: "Ctrl+A", chord: { key: "a", ctrlOrMeta: true }, command: "edit.select-all", requires: { test: (caps) => caps.hasActivities, reason: REASONS.noActivities } },
  { id: "shortcut.find-next", label: { en: "Find next", fa: "یافتن مورد بعدی" }, keys: "F3", chord: { key: "F3" }, unavailable: REASONS.findNext },
  { id: "shortcut.refresh", label: { en: "Refresh project data", fa: "به‌روزرسانی داده‌های پروژه" }, keys: "F5", chord: { key: "F5" }, command: "workspace.refresh" },
  { id: "shortcut.schedule", label: { en: "Schedule activities", fa: "زمان‌بندی فعالیت‌ها" }, keys: "F9", chord: { key: "F9" }, command: "tools.run-schedule" },
  { id: "shortcut.schedule-options", label: { en: "Schedule options", fa: "تنظیمات زمان‌بندی" }, keys: "Shift+F9", chord: { key: "F9", shift: true }, command: "project.schedule-options" },
  { id: "shortcut.leveling", label: { en: "Level resources", fa: "تسطیح منابع" }, keys: "F7", chord: { key: "F7" }, unavailable: REASONS.leveling },
  { id: "shortcut.commit", label: { en: "Commit changes", fa: "ثبت تغییرات" }, keys: "F10", chord: { key: "F10" }, unavailable: REASONS.commit },
  { id: "shortcut.expand-all", label: { en: "Expand all WBS bands", fa: "بازکردن همهٔ باندهای WBS" }, keys: "Ctrl+Num +", chord: { code: "NumpadAdd", ctrlOrMeta: true }, command: "view.expand-all", requires: { test: (caps) => caps.hasWbs && caps.groupByWbs, reason: REASONS.noWbsGroup } },
  { id: "shortcut.collapse-all", label: { en: "Collapse all WBS bands", fa: "بستن همهٔ باندهای WBS" }, keys: "Ctrl+Num -", chord: { code: "NumpadSubtract", ctrlOrMeta: true }, command: "view.collapse-all", requires: { test: (caps) => caps.hasWbs && caps.groupByWbs, reason: REASONS.noWbsGroup } },
  { id: "shortcut.help", label: { en: "Keyboard shortcuts", fa: "کلیدهای میانبر" }, keys: "F1", chord: { key: "F1" }, command: "help.shortcuts" },
  { id: "shortcut.about", label: { en: "About CUBI Workspace", fa: "دربارهٔ محیط کار CUBI" }, keys: "Shift+F12", chord: { key: "F12", shift: true }, command: "help.about" },
];

/** Catalog plus the live Alt+1…9 window bindings for the open tabs. */
export function getDesktopShortcuts(openWindows: readonly WorkspaceMenuKey[] = []): DesktopShortcut[] {
  const windowShortcuts = openWindows.slice(0, 9).map((key, index) => ({
    id: `shortcut.window.${key}`,
    label: WINDOW_TITLES[key],
    keys: `Alt+${index + 1}`,
    chord: { key: String(index + 1), alt: true } satisfies DesktopShortcutChord,
    window: key,
  }));
  return [...DESKTOP_SHORTCUTS, ...windowShortcuts];
}

/** Null when the shortcut is executable in this state, otherwise the reason. */
export function shortcutUnavailableReason(
  shortcut: DesktopShortcut,
  caps: DesktopShellCapabilities,
): LocalizedLabel | null {
  if (shortcut.unavailable) return shortcut.unavailable;
  if (shortcut.requires && !shortcut.requires.test(caps)) return shortcut.requires.reason;
  return null;
}

export type DesktopKeyEvent = {
  key: string;
  code?: string;
  ctrlKey?: boolean;
  metaKey?: boolean;
  altKey?: boolean;
  shiftKey?: boolean;
};

function chordMatches(chord: DesktopShortcutChord, event: DesktopKeyEvent): boolean {
  const ctrlOrMeta = Boolean(event.ctrlKey || event.metaKey);
  if (Boolean(chord.ctrlOrMeta) !== ctrlOrMeta) return false;
  if (Boolean(chord.alt) !== Boolean(event.altKey)) return false;
  if (Boolean(chord.shift) !== Boolean(event.shiftKey)) return false;
  if (chord.code) return event.code === chord.code;
  return Boolean(chord.key) && event.key.toLowerCase() === chord.key?.toLowerCase();
}

/** First catalog entry whose chord matches; later entries never shadow earlier ones. */
export function matchDesktopShortcut(
  event: DesktopKeyEvent,
  shortcuts: readonly DesktopShortcut[],
): DesktopShortcut | null {
  return shortcuts.find((shortcut) => chordMatches(shortcut.chord, event)) ?? null;
}

function renderShortcutsDialog(state: DesktopShellState): string {
  const locale = state.locale;
  const caps = state.capabilities;
  const groups: Array<{ title: string; rows: DesktopShortcut[] }> = [
    { title: translateWorkspaceUiText(locale, "Workspace", "محیط کار"), rows: [] },
    { title: translateWorkspaceUiText(locale, "Editing", "ویرایش"), rows: [] },
    { title: translateWorkspaceUiText(locale, "View and schedule", "نما و زمان‌بندی"), rows: [] },
  ];
  const bucket = (shortcut: DesktopShortcut): number => {
    if (shortcut.id.startsWith("shortcut.window.")) return 0;
    if (/^shortcut\.(new|open|close-window|print|save-layout|help|about|refresh)$/.test(shortcut.id)) return 0;
    if (/^shortcut\.(undo|redo|cut|copy|paste|delete|insert|find|select-all)$/.test(shortcut.id)) return 1;
    return 2;
  };
  for (const shortcut of getDesktopShortcuts(state.openWindows)) {
    groups[bucket(shortcut)].rows.push(shortcut);
  }
  const heading = translateWorkspaceUiText(locale, "Keyboard shortcuts", "کلیدهای میانبر");
  const command = translateWorkspaceUiText(locale, "Command", "فرمان");
  const shortcutWord = translateWorkspaceUiText(locale, "Shortcut", "میانبر");
  const close = translateWorkspaceUiText(locale, "Close", "بستن");
  const unavailableWord = translateWorkspaceUiText(locale, "Unavailable", "در دسترس نیست");
  const sections = groups
    .filter((group) => group.rows.length > 0)
    .map((group) => `<h3>${escapeHtml(group.title)}</h3>
      <table><thead><tr><th>${escapeHtml(command)}</th><th>${escapeHtml(shortcutWord)}</th></tr></thead>
      <tbody>${group.rows.map((shortcut) => {
        const reason = shortcutUnavailableReason(shortcut, caps);
        return `<tr${reason ? ' class="is-unavailable"' : ""}><td>${escapeHtml(pick(shortcut.label, locale))}</td><td><kbd>${escapeHtml(shortcut.keys)}</kbd>${reason ? ` <span class="cp-shortcut-reason">${escapeHtml(unavailableWord)} — ${escapeHtml(pick(reason, locale))}</span>` : ""}</td></tr>`;
      }).join("")}</tbody></table>`)
    .join("");
  return `<dialog class="cp-desktop-dialog" data-desktop-dialog="shortcuts" aria-labelledby="cp-shortcuts-heading">
    <h2 id="cp-shortcuts-heading">${escapeHtml(heading)}</h2>
    ${sections}
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
  const openFilter = host.querySelector<HTMLDialogElement>('dialog[data-desktop-dialog="filters"]');
  const filterSnapshot = openFilter?.open ? captureFilterDialog(openFilter) : null;
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
    ${renderTabs(state)}
  </section>
  ${renderLayoutDialogs({
    locale: state.locale,
    layout,
    sortColumns: [...(state.sortColumns ?? [])],
    sortColumnId: state.sortColumnId ?? null,
    sortDirection: state.sortDirection ?? "asc",
    sortLevels: state.sortLevels ?? [],
    groupLevels: state.groupLevels ?? [],
    rowHeight: (state.presentation ?? DEFAULT_PRESENTATION).table.rowHeight,
    fontSize: (state.presentation ?? DEFAULT_PRESENTATION).table.fontSize,
    barHeight: (state.presentation ?? DEFAULT_PRESENTATION).bars.task.height,
    barTone: "crimson",
    presentation: state.presentation ?? DEFAULT_PRESENTATION,
    dataAvailability: state.dataAvailability ?? { actual: false, baseline: false },
    dataDate: state.dataDate ?? null,
  })}
  ${renderShortcutsDialog(state)}
  ${renderAboutDialog(state)}`;
  bindHost(host);
  if (filterSnapshot) {
    const dialog = host.querySelector<HTMLDialogElement>('dialog[data-desktop-dialog="filters"]');
    if (dialog) {
      restoreFilterDialog(dialog, filterSnapshot);
      if (!dialog.open) dialog.showModal();
    }
  }
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

export type DesktopDialogName = "shortcuts" | "about" | "filters" | "group-sort" | "timescale" | "bars" | "font-row" | "user-preferences";

type FilterDialogSnapshot = {
  builder: {
    name: string;
    editingId: string;
    scope: string;
    match: string;
    rows: { field: string; operator: string; value: string; high: string }[];
  };
  list: {
    selected: string[];
    allActivities: boolean;
    combine: string;
    applyMode: string;
    currentRow: string | null;
  } | null;
};

function fieldValue(dialog: HTMLDialogElement, selector: string): string {
  const element = dialog.querySelector<HTMLInputElement | HTMLSelectElement>(selector);
  return element?.value ?? "";
}

/** Deleting the filter loaded in the builder must also clear that builder. */
let clearFilterBuilderAfterRender = false;

/**
 * A submit applies the visible selection, so the re-rendered list already shows
 * the fresh state. Restoring the pre-submit checkboxes would undo the result of
 * actions such as Paste or Copy as Layout.
 */
let filterListFromState = false;

/**
 * A layout commit answers asynchronously and re-renders the shell. The Filters
 * dialog is modal, so its in-progress criteria and checked rows must survive that
 * render instead of being wiped under the user's hands.
 */
function captureFilterDialog(dialog: HTMLDialogElement): FilterDialogSnapshot {
  const clearBuilder = clearFilterBuilderAfterRender;
  clearFilterBuilderAfterRender = false;
  const listFromState = filterListFromState;
  filterListFromState = false;
  return {
    builder: clearBuilder
      ? {
        name: "",
        editingId: "",
        scope: "layout",
        match: "all",
        rows: [{ field: "activity_name", operator: "contains", value: "", high: "" }],
      }
      : {
        name: fieldValue(dialog, 'input[name="filterName"]'),
        editingId: fieldValue(dialog, 'input[name="filterEditingId"]'),
        scope: fieldValue(dialog, 'select[name="filterScope"]'),
        match: fieldValue(dialog, 'select[name="filterMatch"]'),
        rows: filterCriterionRows(dialog).map((criterion) => ({
          field: criterion.fieldId,
          operator: criterion.operator,
          value: criterion.value,
          high: criterion.highValue ?? "",
        })),
      },
    list: listFromState
      ? null
      : {
        selected: Array.from(dialog.querySelectorAll<HTMLInputElement>('input[name="filterSelected"]'))
          .filter((input) => input.checked)
          .map((input) => input.value),
        allActivities: dialog.querySelector<HTMLInputElement>('input[name="filterAllActivities"]')?.checked ?? false,
        combine: dialog.querySelector<HTMLInputElement>('input[name="filterCombine"]:checked')?.value ?? "all",
        applyMode: dialog.querySelector<HTMLInputElement>('input[name="filterApplyMode"]:checked')?.value ?? "replace",
        currentRow: dialog.querySelector<HTMLElement>("tr.is-current")?.dataset.filterId ?? null,
      },
  };
}

/**
 * Validates the builder and counts matching rows without applying anything.
 * Incomplete or inverted criteria are reported instead of silently matching.
 */
function updateFilterPreview(host: HTMLElement, dialog: HTMLDialogElement): void {
  const preview = dialog.querySelector<HTMLElement>("[data-filter-preview]");
  const state = runtimeByHost.get(host)?.state;
  if (!preview || !state) return;
  const criteria = filterCriterionRows(dialog);
  // A blank row is simply not part of the filter yet; it must not turn the
  // preview into a validation error while the user is still filling it in.
  const active = criteria.filter((criterion) => criterion.value.trim() !== ""
    || criterion.highValue?.trim()
    || criterion.operator === "is-empty" || criterion.operator === "is-not-empty");
  if (active.length === 0) {
    preview.textContent = translateWorkspaceUiText(
      state.locale,
      "Preview: choose a parameter and a value to see how many activities match.",
      "پیش‌نمایش: پارامتر و مقدار را انتخاب کنید تا شمار فعالیت‌های مطابق دیده شود.",
    );
    preview.classList.remove("is-invalid");
    return;
  }
  const match = fieldValue(dialog, 'select[name="filterMatch"]') === "any" ? "any" : "all";
  const draft: ActivityFilterDefinition = { id: "preview", name: "preview", match, criteria: active };
  const result = previewActivityFilter(
    state.activities ?? [],
    draft,
    state.wbsNodes ?? [],
    createActivityFilterDateContext(state.activities ?? [], state.dataDate ?? null),
  );
  preview.textContent = formatFilterPreview(result, state.locale);
  preview.classList.toggle("is-invalid", !result.valid);
  preview.dataset.filterPreviewMatched = String(result.matched);
  preview.dataset.filterPreviewValid = result.valid ? "true" : "false";
}

function restoreFilterDialog(dialog: HTMLDialogElement, snapshot: FilterDialogSnapshot): void {
  const set = (selector: string, value: string): void => {
    const element = dialog.querySelector<HTMLInputElement | HTMLSelectElement>(selector);
    if (element && value) element.value = value;
  };
  set('input[name="filterName"]', snapshot.builder.name);
  set('input[name="filterEditingId"]', snapshot.builder.editingId);
  set('select[name="filterScope"]', snapshot.builder.scope);
  set('select[name="filterMatch"]', snapshot.builder.match);
  setFilterCriterionRows(dialog, snapshot.builder.rows.map((row) => ({
    fieldId: row.field as ActivityFilterCriterion["fieldId"],
    operator: row.operator as ActivityFilterCriterion["operator"],
    value: row.value,
    ...(row.operator === "within-range" ? { highValue: row.high } : {}),
  })));
  if (snapshot.list) {
    const all = dialog.querySelector<HTMLInputElement>('input[name="filterAllActivities"]');
    if (all) all.checked = snapshot.list.allActivities;
    const combine = dialog.querySelector<HTMLInputElement>(`input[name="filterCombine"][value="${snapshot.list.combine}"]`);
    if (combine) combine.checked = true;
    const mode = dialog.querySelector<HTMLInputElement>(`input[name="filterApplyMode"][value="${snapshot.list.applyMode}"]`);
    if (mode) mode.checked = true;
    const wanted = new Set(snapshot.list.selected);
    for (const input of dialog.querySelectorAll<HTMLInputElement>('input[name="filterSelected"]')) {
      input.checked = wanted.has(input.value);
    }
    setFilterListEnabled(dialog, !snapshot.list.allActivities);
  }
  const current = snapshot.list
    ? snapshot.list.currentRow
    : dialog.querySelector<HTMLInputElement>('input[name="filterSelected"]:checked')?.value ?? null;
  const row = current
    ? dialog.querySelector<HTMLElement>(`tr[data-filter-id="${current}"]`)
    : null;
  if (row) {
    markCurrentFilterRow(dialog, row);
  } else {
    const hidden = dialog.querySelector<HTMLInputElement>('input[name="filterRowId"]');
    if (hidden) hidden.value = "";
  }
}

function markCurrentFilterRow(dialog: HTMLDialogElement, row: HTMLElement): void {
  for (const other of dialog.querySelectorAll("tr.is-current")) other.classList.remove("is-current");
  row.classList.add("is-current");
  for (const button of dialog.querySelectorAll<HTMLElement>("[data-filter-row-select]")) {
    const selected = button.closest("tr") === row;
    button.setAttribute("aria-pressed", String(selected));
  }
  const hidden = dialog.querySelector<HTMLInputElement>('input[name="filterRowId"]');
  if (hidden) hidden.value = row.dataset.filterId ?? "";
}

function openDialog(host: HTMLElement, name: DesktopDialogName): void {
  const dialog = host.querySelector<HTMLDialogElement>(`[data-desktop-dialog="${name}"]`);
  if (!dialog) return;
  closeMenus(host);
  if (typeof dialog.showModal === "function") dialog.showModal();
  else dialog.setAttribute("open", "");
}

/** Opens a layout dialog from another region (for example the Gantt command bar). */
export function openDesktopDialog(host: HTMLElement, name: DesktopDialogName): void {
  openDialog(host, name);
}

function dialogNameForCommand(command: string): DesktopDialogName | null {
  switch (command) {
    case "dialog.filters": return "filters";
    case "dialog.group-sort": return "group-sort";
    case "dialog.timescale": return "timescale";
    case "dialog.bars": return "bars";
    case "dialog.font-row": return "font-row";
    case "dialog.user-preferences": return "user-preferences";
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

/**
 * Shell keyboard handling is registered on `document`, not on the host element.
 * A click on a non-focusable row or the workspace background leaves focus on
 * `document.body`, so host-scoped listeners silently dropped Alt+mnemonic,
 * function keys and command chords until the user tabbed into a control.
 */
function bindShellKeydown(host: HTMLElement, listener: (event: KeyboardEvent) => void): void {
  host.addEventListener("keydown", listener);
  if (typeof document === "undefined") return;
  document.addEventListener("keydown", (event) => {
    if (!host.isConnected || !runtimeByHost.has(host)) return;
    // Keys that bubble through the shell were already handled by the host
    // listener; only a target outside it (body, page chrome) needs this path.
    const target = event.target as Node | null;
    if (target && typeof target === "object" && host.contains(target as Node)) return;
    listener(event);
  });
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

    // Layout commands kept for the legacy command ribbon and keyboard paths:
    // they must open their owning dialog instead of leaving the workspace.
    const shellCommand = target.closest<HTMLElement>("[data-shell-command]");
    if (shellCommand) {
      if (shellCommand.hasAttribute("disabled")) return;
      const commands: Record<string, DesktopCommand> = {
        Columns: "view.fields",
        "Filter By": "dialog.filters",
        "Group and Sort By": "dialog.group-sort",
        Timescale: "dialog.timescale",
        Bars: "dialog.bars",
        "Bar Chart Options": "dialog.bars",
        "Table Font and Row": "dialog.font-row",
        "User Preferences": "dialog.user-preferences",
        "Line Numbers": "view.line-numbers",
      };
      const command = commands[shellCommand.dataset.shellCommand ?? ""];
      host.querySelectorAll<HTMLDetailsElement>(".cubi-command-menubar details[open]").forEach((item) => item.removeAttribute("open"));
      const dialogName = command ? dialogNameForCommand(command) : null;
      if (dialogName) openDialog(host, dialogName);
      else if (command) runtime.handlers.onCommand(command);
      return;
    }

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

    const filterDialog = target.closest<HTMLDialogElement>('dialog[data-desktop-dialog="filters"]');
    const filterNew = target.closest<HTMLElement>("[data-filter-new]");
    if (filterNew && filterDialog) {
      // Version 26: New starts a global filter; the list selection is unchanged.
      resetFilterEditor(filterDialog, "global");
      filterDialog.querySelector<HTMLInputElement>('input[name="filterName"]')?.focus();
      return;
    }
    const filterRowAdd = target.closest<HTMLElement>("[data-filter-row-add]");
    if (filterRowAdd && filterDialog) {
      const row = addFilterCriterion(filterDialog);
      row?.querySelector<HTMLSelectElement>('select[name^="filter.field."]')?.focus();
      updateFilterPreview(host, filterDialog);
      return;
    }
    const filterRowRemove = target.closest<HTMLElement>("[data-filter-row-remove]");
    if (filterRowRemove && filterDialog) {
      const row = filterRowRemove.closest<HTMLElement>(".cp-filter-row");
      if (row) removeFilterCriterion(row);
      updateFilterPreview(host, filterDialog);
      return;
    }
    const filterRowMove = target.closest<HTMLElement>("[data-filter-row-move]");
    if (filterRowMove && filterDialog) {
      const row = filterRowMove.closest<HTMLElement>(".cp-filter-row");
      if (row) moveFilterCriterion(row, filterRowMove.dataset.filterRowMove === "down" ? "down" : "up");
      updateFilterPreview(host, filterDialog);
      return;
    }
    const filterRowSelect = target.closest<HTMLElement>("[data-filter-row-select]");
    if (filterRowSelect && filterDialog) {
      const row = filterRowSelect.closest<HTMLElement>("tr[data-filter-id]");
      if (row) markCurrentFilterRow(filterDialog, row);
      return;
    }
    const filterOptimize = target.closest<HTMLElement>("[data-filter-optimize]");
    if (filterOptimize && filterDialog) {
      const match = filterDialog.querySelector<HTMLSelectElement>('select[name="filterMatch"]')?.value === "any" ? "any" : "all";
      const result = optimizeActivityFilterCriteria(filterCriterionRows(filterDialog), match);
      const status = filterDialog.querySelector<HTMLElement>("[data-filter-optimize-status]");
      if (result.removed > 0) {
        setFilterCriterionRows(filterDialog, result.criteria);
        renumberFilterRows(filterDialog);
      }
      if (status) {
        status.textContent = result.removed > 0
          ? translateWorkspaceUiText(runtime.state.locale, `Removed ${result.removed} redundant criteria.`, `${result.removed} معیار تکراری حذف شد.`)
          : translateWorkspaceUiText(runtime.state.locale, "No redundant criteria found.", "معیار تکراری پیدا نشد.");
      }
      updateFilterPreview(host, filterDialog);
      return;
    }
    const filterModify = target.closest<HTMLElement>("[data-filter-modify]");
    if (filterModify && filterDialog) {
      const currentRow = filterDialog.querySelector<HTMLElement>("tr.is-current");
      const checked = filterDialog.querySelector<HTMLInputElement>('input[name="filterSelected"]:checked');
      const filters = (runtime.state.presentation ?? DEFAULT_PRESENTATION).filters;
      const filter = findActivityFilter(filters, currentRow?.dataset.filterId ?? checked?.value);
      // Default filters ship read-only, exactly as the Help says.
      if (filter && !filter.builtin) {
        loadFilterEditor(filterDialog, filter);
        filterDialog.querySelector<HTMLInputElement>('input[name="filterName"]')?.focus();
      } else {
        filterModify.setAttribute("title", translateWorkspaceUiText(runtime.state.locale, "Select a saved global or layout filter to modify.", "برای ویرایش، یک فیلتر سراسری یا چیدمان ذخیره‌شده را انتخاب کنید."));
      }
      return;
    }
    const filterSort = target.closest<HTMLElement>("[data-filter-sort]");
    if (filterSort && filterDialog) {
      const column = filterSort.dataset.filterSort === "select" ? "select" : "name";
      const descending = filterSort.dataset.filterSortDirection === "desc";
      filterSort.dataset.filterSortDirection = descending ? "asc" : "desc";
      sortFilterList(filterDialog, column, descending);
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
    if (!(target instanceof HTMLSelectElement) && !(target instanceof HTMLInputElement)) return;
    const dialog = target.closest<HTMLDialogElement>('dialog[data-desktop-dialog="filters"]');
    if (dialog) {
      if (target instanceof HTMLInputElement && target.name === "filterAllActivities") {
        setFilterListEnabled(dialog, !target.checked);
        return;
      }
      if (target instanceof HTMLSelectElement && target.name.startsWith("filter.field.")) {
        syncFilterField(target);
        updateFilterPreview(host, dialog);
        return;
      }
      if (target instanceof HTMLSelectElement && target.name.startsWith("filter.operator.")) {
        syncFilterOperator(target);
        updateFilterPreview(host, dialog);
        return;
      }
      if (target instanceof HTMLSelectElement && target.name.startsWith("filter.value.")) {
        updateFilterPreview(host, dialog);
        return;
      }
      if (target instanceof HTMLSelectElement && target.name === "filterMatch") {
        renumberFilterRows(dialog);
        updateFilterPreview(host, dialog);
        return;
      }
      if (target instanceof HTMLInputElement && /^filter\.(value|high)\./.test(target.name)) {
        updateFilterPreview(host, dialog);
        return;
      }
    }
    if (!(target instanceof HTMLSelectElement)) return;
    if (!target.matches("[data-workspace-language]")) return;
    const runtime = runtimeByHost.get(host);
    if (!runtime) return;
    runtime.handlers.onLocaleChange?.(target.value);
  });

  host.addEventListener("submit", (event) => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement) || !form.matches("[data-dialog-form]")) return;
    event.preventDefault();
    const runtime = runtimeByHost.get(host);
    const dialog = form.closest<HTMLDialogElement>("dialog");
    const dialogName = dialog?.dataset.desktopDialog;
    // Apply and the filter actions keep the dialog open (Version 26 behaviour);
    // the patch re-renders the shell, so reopen the freshly rendered dialog.
    const submitter = event instanceof SubmitEvent ? event.submitter : null;
    const keepOpen = Boolean(submitter?.closest("[data-dialog-apply]"));
    const data = new FormData(form);
    if (submitter instanceof HTMLButtonElement && submitter.name) data.append(submitter.name, submitter.value);
    if (dialogName === "filters") filterListFromState = true;
    if (data.get("filterAction") === "delete") {
      const editingId = String(data.get("filterEditingId") ?? "");
      const targetId = String(data.get("filterRowId") ?? "") || editingId;
      // The render happens inside onLayoutOptions, so flag the builder reset first.
      if (editingId && editingId === targetId) clearFilterBuilderAfterRender = true;
    }
    // Closing before the patch matters: renderDesktopShell re-opens a filters
    // dialog that was open when it rendered, so a dialog left open here would
    // be snapshotted and shown again after OK, making OK look ineffective.
    if (!keepOpen) dialog?.close();
    runtime?.handlers.onLayoutOptions?.(readLayoutPatch(data, runtime.state.presentation ?? DEFAULT_PRESENTATION));
    filterListFromState = false;
    clearFilterBuilderAfterRender = false;
    if (keepOpen && dialogName) {
      // The patch re-rendered the shell, so the original dialog is detached.
      const fresh = host.querySelector<HTMLDialogElement>(`[data-desktop-dialog="${dialogName}"]`);
      if (fresh && !fresh.open) openDialog(host, dialogName as DesktopDialogName);
    }
  });

  bindShellKeydown(host, (event) => {
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

  bindShellKeydown(host, (event) => {
    const runtime = runtimeByHost.get(host);
    if (!runtime) return;
    // A control that already consumed the chord (grid navigation, splitter,
    // context menu) keeps precedence over the shell binding.
    if (event.defaultPrevented) return;
    const target = event.target as HTMLElement | null;
    const typing = Boolean(target?.closest("input, textarea, select, [contenteditable=true]"));

    // Keyboard tab reordering: Ctrl+Shift+Left/Right while a window tab has focus.
    const tab = target?.closest<HTMLElement>("[data-window-tab]");
    if (
      !typing && tab?.dataset.windowTab && event.ctrlKey && event.shiftKey
      && (event.key === "ArrowLeft" || event.key === "ArrowRight")
    ) {
      event.preventDefault();
      const next = moveWorkspaceWindow(
        runtime.state.openWindows,
        tab.dataset.windowTab as WorkspaceMenuKey,
        event.key === "ArrowRight" ? 1 : -1,
      );
      runtime.handlers.onWindowReorder?.(next);
      return;
    }

    if (event.key === "Escape") return;
    if (typing) return;
    // A modal dialog owns the keyboard while it is open; application commands
    // must not fire behind it.
    if (host.querySelector("dialog[open]")) return;

    // Alt+mnemonic opens a top-level menu. The access key lives on the menu
    // model, so the bar and this handler cannot drift apart.
    if (event.altKey && !event.ctrlKey && !event.metaKey && !event.shiftKey) {
      const menu = getDesktopMenus(runtime.state).find(
        (candidate) => candidate.accessKey === event.key.toLowerCase(),
      );
      if (menu) {
        event.preventDefault();
        openMenu(host, menu.id, true);
        return;
      }
    }

    const shortcut = matchDesktopShortcut(event, getDesktopShortcuts(runtime.state.openWindows));
    if (!shortcut) return;
    if (shortcutUnavailableReason(shortcut, runtime.state.capabilities)) {
      // Documented but unserviced: the binding is reported in the dialog and
      // never silently performs a different action.
      return;
    }
    event.preventDefault();
    if (shortcut.window) {
      runtime.handlers.onWindowOpen(shortcut.window);
      return;
    }
    if (!shortcut.command) return;
    if (shortcut.command === "help.shortcuts") { openDialog(host, "shortcuts"); return; }
    if (shortcut.command === "help.about") { openDialog(host, "about"); return; }
    const dialogName = dialogNameForCommand(shortcut.command);
    if (dialogName) { openDialog(host, dialogName); return; }
    runtime.handlers.onCommand(shortcut.command);
  });

  // Inside an open menu: arrows, Home/End and first-letter navigation.
  bindShellKeydown(host, (event) => {
    const target = event.target as HTMLElement | null;
    const popup = target?.closest<HTMLElement>("[data-desktop-popup]");
    if (!popup || popup.hidden) return;
    const items = Array.from(popup.querySelectorAll<HTMLElement>("button:not([disabled])"));
    if (!items.length) return;
    const current = items.indexOf(target?.closest<HTMLElement>("button") ?? items[0]);
    const focusItem = (index: number): void => {
      const next = items[(index + items.length) % items.length];
      next?.focus();
    };
    if (event.key === "ArrowDown") { event.preventDefault(); focusItem(current + 1); return; }
    if (event.key === "ArrowUp") { event.preventDefault(); focusItem(current - 1); return; }
    if (event.key === "Home") { event.preventDefault(); focusItem(0); return; }
    if (event.key === "End") { event.preventDefault(); focusItem(items.length - 1); return; }
    if (event.key === "ArrowRight" || event.key === "ArrowLeft") {
      event.preventDefault();
      const triggers = Array.from(host.querySelectorAll<HTMLElement>("[data-desktop-menu]"));
      const activeTrigger = popup.closest(".cp-menubar-group")?.querySelector<HTMLElement>("[data-desktop-menu]");
      const index = triggers.indexOf(activeTrigger ?? triggers[0]);
      const next = triggers[(index + (event.key === "ArrowRight" ? 1 : -1) + triggers.length) % triggers.length];
      if (next?.dataset.desktopMenu) {
        next.focus();
        openMenu(host, next.dataset.desktopMenu, true);
      }
      return;
    }
    if (event.key.length === 1 && /\S/.test(event.key)) {
      const letter = event.key.toLowerCase();
      const match = items.find((item) =>
        (item.querySelector(".cp-menubar-item-label")?.textContent ?? "").trim().toLowerCase().startsWith(letter),
      );
      if (match) { event.preventDefault(); match.focus(); }
    }
  });

  // Pointer reordering of window tabs (drag a tab onto another tab).
  let draggedTab: WorkspaceMenuKey | null = null;
  host.addEventListener("dragstart", (event) => {
    const tab = (event.target as HTMLElement | null)?.closest<HTMLElement>("[data-window-tab]");
    if (!tab?.dataset.windowTab) return;
    draggedTab = tab.dataset.windowTab as WorkspaceMenuKey;
    event.dataTransfer?.setData("text/plain", draggedTab);
    if (event.dataTransfer) event.dataTransfer.effectAllowed = "move";
  });
  host.addEventListener("dragover", (event) => {
    const tab = (event.target as HTMLElement | null)?.closest<HTMLElement>("[data-window-tab]");
    if (!draggedTab || !tab || tab.dataset.windowTab === draggedTab) return;
    event.preventDefault();
    if (event.dataTransfer) event.dataTransfer.dropEffect = "move";
  });
  host.addEventListener("drop", (event) => {
    const tab = (event.target as HTMLElement | null)?.closest<HTMLElement>("[data-window-tab]");
    const runtime = runtimeByHost.get(host);
    if (!draggedTab || !tab?.dataset.windowTab || !runtime) return;
    event.preventDefault();
    const targetKey = tab.dataset.windowTab as WorkspaceMenuKey;
    if (targetKey !== draggedTab) {
      runtime.handlers.onWindowReorder?.(reorderWorkspaceWindows(runtime.state.openWindows, draggedTab, targetKey));
    }
    draggedTab = null;
  });
  host.addEventListener("dragend", () => { draggedTab = null; });
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
