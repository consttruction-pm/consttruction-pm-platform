/**
 * Visual workspace demo (CUBI-DEMO-001).
 *
 * Scope: visual shell only. The rows below are fixed demonstration data used to
 * show table, Gantt, tab and dialog layouts. Nothing here is saved, scheduled or
 * calculated, and the surface is permanently labelled as preview data. Real
 * project data continues to live in the normal workspace. The shared preview
 * project routes here by default; use the explicit live view to open API-backed data.
 */
import { workspaceIcon } from "./workspace-icons.js";
import { getAvailableWorkspaceLocales, getWorkspaceLocaleDirection, getWorkspaceLocaleDisplayName, translateWorkspaceUiText } from "./workspace-localization.js";
import { LANDING_LOCALE_STORAGE_KEY, rememberWorkspaceLocale, writeStoredValue } from "./workspace-preferences.js";

export type DemoWindowId =
  | "projects" | "wbs" | "activities" | "assignments" | "resources" | "roles" | "calendars" | "reports"
  | "tracking" | "documents" | "expenses" | "thresholds" | "issues" | "risks" | "administration"
  | "network" | "trace" | "timeline" | "activity-profile" | "resource-profile" | "activity-sheet" | "resource-sheet" | "cost-control" | "progress-control" | "procurement" | "changes-claims" | "form-builder" | "organization" | "smart-guide" | "assistant" | "search" | "comments";

type Label = { en: string; fa: string };
type Row = Record<string, string | number>;

const WINDOWS: Array<{ id: DemoWindowId; en: string; fa: string }> = [
  { id: "projects", en: "Projects", fa: "پروژه‌ها" },
  { id: "wbs", en: "WBS", fa: "WBS" },
  { id: "activities", en: "Activities", fa: "فعالیت‌ها" },
  { id: "assignments", en: "Resource Assignments", fa: "تخصیص منابع" },
  { id: "resources", en: "Resources", fa: "منابع" },
  { id: "roles", en: "Roles", fa: "نقش‌ها" },
  { id: "calendars", en: "Calendars", fa: "تقویم‌ها" },
  { id: "reports", en: "Reports", fa: "گزارش‌ها" },
  { id: "tracking", en: "Tracking", fa: "پیگیری" },
  { id: "documents", en: "Documents", fa: "اسناد" },
  { id: "expenses", en: "Expenses", fa: "هزینه‌ها" },
  { id: "thresholds", en: "Thresholds", fa: "آستانه‌ها" },
  { id: "issues", en: "Issues", fa: "مسائل" },
  { id: "risks", en: "Risks", fa: "ریسک‌ها" },
  { id: "administration", label: { en: "Administration", fa: "مدیریت" }, items: [
    { label: { en: "Users…", fa: "کاربران…" }, action: { window: "administration", adminSection: "users" } },
    { label: { en: "Security Profiles…", fa: "پروفایل‌های امنیتی…" }, action: { window: "administration", adminSection: "security" } },
    { label: { en: "Administrative Preferences…", fa: "تنظیمات مدیریتی…" }, action: { window: "administration", adminSection: "preferences" } },
    { label: { en: "Administrative Categories…", fa: "دسته‌بندی‌های مدیریتی…" }, action: { window: "administration", adminSection: "categories" } },
    { label: { en: "Currencies…", fa: "ارزها…" }, action: { window: "administration", adminSection: "currencies" } },
    { label: { en: "Financial Periods…", fa: "دوره‌های مالی…" }, action: { window: "administration", adminSection: "financial-periods" } },
    { label: { en: "Resource Security", fa: "امنیت منابع" }, action: { window: "administration", adminSection: "security" } },
    { label: { en: "Activity Code Security", fa: "امنیت کدهای فعالیت" }, action: { window: "administration", adminSection: "security" } },
    { label: { en: "Code Dictionaries…", fa: "واژه‌نامه کدها…" }, action: { window: "administration", adminSection: "codes" } },
    { label: { en: "Custom Fields…", fa: "فیلدهای سفارشی…" }, action: { window: "administration", adminSection: "custom-fields" } },
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
    case "module-actions":
      return `<div class="cp-vd-form">
        <div class="cp-vd-hintbox">${esc(t(state.locale, "These controls demonstrate the page-specific command surface. Changes are preview-only and are not saved.", "این کنترل‌ها نوار فرمان صفحه را نمایش می‌دهند. تغییرات صرفاً نمایشی هستند و ذخیره نمی‌شوند."))}</div>
        <label>${esc(t(state.locale, "Object type", "نوع آیتم"))}<select name="objectType"><option>Activity</option><option>WBS</option><option>Relationship</option><option>Resource assignment</option><option>Document</option><option>Issue</option><option>Risk</option><option>Form</option><option>Comment</option></select></label>
        <label>${esc(t(state.locale, "Name / description", "نام / شرح"))}<input name="objectName" placeholder="${esc(t(state.locale, "Enter a descriptive name", "نام یا شرح را وارد کنید"))}"></label>
        <label>${esc(t(state.locale, "Code / ID", "کد / شناسه"))}<input name="objectCode" placeholder="CUBI-NEW-001"></label>
        <label>${esc(t(state.locale, "Status", "وضعیت"))}<select name="status"><option>Draft</option><option>For review</option><option>Approved</option><option>On hold</option></select></label>
        <p class="cp-vd-note">${esc(t(state.locale, "Visual preview only — no project record will be created or modified.", "صرفاً پیش‌نمایش بصری — هیچ رکوردی در پروژه ایجاد یا تغییر نمی‌کند."))}</p>
      </div>`;
    case "columns": {
      const availableColumns = state.window === "activities"
        ? ACTIVITY_COLUMNS.filter((column) => !state.columns.includes(column.id))
        : state.moduleAvailableColumns.filter((column) => !state.moduleColumns.includes(column));
      const selectedColumns = state.window === "activities"
        ? ACTIVITY_COLUMNS.filter((column) => state.columns.includes(column.id))
        : state.moduleAvailableColumns.filter((column) => state.moduleColumns.includes(column));
      const firstSelectedColumn = selectedColumns[0];
      const availableRows = availableColumns.map((column) => {
        const id = typeof column === "string" ? column : column.id;
        const title = typeof column === "string" ? column : label(column, state.locale);
        return `<li><label><input type="checkbox" name="available-${esc(id)}"> ${esc(title)}</label></li>`;
      }).join("");
      const selectedRows = selectedColumns.map((column) => {
        const id = typeof column === "string" ? column : column.id;
        const title = typeof column === "string" ? column : label(column, state.locale);
        const width = typeof column === "string" ? 120 : column.width;
        return `<li data-vd-selected-column="${esc(id)}"><label><input type="checkbox" name="selected-${esc(id)}" checked> ${esc(title)}</label><span class="cp-vd-column-width">${width}px</span></li>`;
      }).join("");
      return `<div class="cp-vd-columns-editor">
        <div class="cp-vd-columns-toolbar">
          <label>${esc(t(state.locale, "Available Columns Options", "گزینه‌های ستون‌های موجود"))}<input type="search" placeholder="${esc(t(state.locale, "Find a column…", "یافتن ستون…"))}"></label>
          <label>${esc(t(state.locale, "Group available columns", "گروه‌بندی ستون‌های موجود"))}<select><option>By category</option><option>Alphabetically</option><option>By data type</option></select></label>
          <button type="button" disabled>Expand All</button><button type="button" disabled>Collapse All</button>
        </div>
        <div class="cp-vd-columns-transfer">
          <section class="cp-vd-columns-list"><strong>${esc(t(state.locale, "Available Columns", "ستون‌های موجود"))}</strong><ul>${availableRows || `<li class="cp-vd-note">${esc(t(state.locale, "All available columns are selected.", "همه ستون‌های موجود انتخاب شده‌اند."))}</li>`}</ul></section>
          <div class="cp-vd-columns-transfer-actions"><button type="button" disabled title="Preview only">▶</button><button type="button" disabled title="Preview only">▶▶</button><button type="button" disabled title="Preview only">◀</button><button type="button" disabled title="Preview only">◀◀</button></div>
          <section class="cp-vd-columns-list"><strong>${esc(t(state.locale, "Selected Options", "گزینه‌های انتخاب‌شده"))}</strong><ul>${selectedRows || `<li class="cp-vd-note">${esc(t(state.locale, "Select at least one column.", "حداقل یک ستون را انتخاب کنید."))}</li>`}</ul><div class="cp-vd-inline-actions"><button type="button" disabled>▲</button><button type="button" disabled>▼</button></div></section>
        </div>
        <section class="cp-vd-column-properties"><h4>${esc(t(state.locale, "Edit Column", "ویرایش ستون"))}</h4><div class="cp-vd-form">
          <label>${esc(t(state.locale, "Column title", "عنوان ستون"))}<input value="${esc(firstSelectedColumn ? (typeof firstSelectedColumn === "string" ? firstSelectedColumn : label(firstSelectedColumn, state.locale)) : "")}" readonly></label>
          <label>${esc(t(state.locale, "Width", "عرض"))}<input type="number" value="${firstSelectedColumn && typeof firstSelectedColumn !== "string" ? firstSelectedColumn.width : 120}" min="24" max="1200"></label>
          <label>${esc(t(state.locale, "Alignment", "تراز"))}<select><option>Default</option><option>Left</option><option>Center</option><option>Right</option></select></label>
          <label class="cp-vd-check"><input type="checkbox" checked> ${esc(t(state.locale, "Visible", "نمایان"))}</label>
        </div></section>
        <div class="cp-vd-columns-footer"><label>${esc(t(state.locale, "Copy From", "کپی از"))}<select><option>CUBI Classic Schedule Layout</option><option>Cost and Resource Layout</option><option>Commissioning Look-ahead</option></select></label><button type="button" disabled>Open</button><button type="button" disabled>Default</button></div>
        <p class="cp-vd-note">${esc(t(state.locale, "A layout must retain at least one visible column. Transfer, reorder, copy and edit controls are visual-only in this preview.", "هر چیدمان باید دست‌کم یک ستون نمایان داشته باشد. انتقال، مرتب‌سازی، کپی و ویرایش ستون‌ها در این پیش‌نمایش صرفاً نمایشی است."))}</p>
      </div>`;
    }
    case "filters":
      return `<div class="cp-vd-filter-manager">
        <div class="cp-vd-filter-library">
          <div class="cp-vd-filter-library-head"><strong>${esc(t(state.locale, "Available filters", "فیلترهای موجود"))}</strong><button type="button" disabled title="Preview only">＋</button></div>
          <div class="cp-vd-filter-category"><strong>${esc(t(state.locale, "Default", "پیش‌فرض"))}</strong><ul><li><label><input type="checkbox"> Critical</label></li><li><label><input type="checkbox"> Completed</label></li><li><label><input type="checkbox" checked> In Progress</label></li><li><label><input type="checkbox"> Not Started</label></li><li><label><input type="checkbox"> Milestone</label></li><li><label><input type="checkbox"> Negative Float</label></li></ul></div>
          <div class="cp-vd-filter-category"><strong>${esc(t(state.locale, "Global", "سراسری"))}</strong><p class="cp-vd-note">${esc(t(state.locale, "No global filters in this preview.", "در این پیش‌نمایش فیلتر سراسری وجود ندارد."))}</p></div>
          <div class="cp-vd-filter-category"><strong>${esc(t(state.locale, "Layout", "چیدمان"))}</strong><p class="cp-vd-note">${esc(t(state.locale, "No layout filters in this preview.", "در این پیش‌نمایش فیلتر چیدمان وجود ندارد."))}</p></div>
          <div class="cp-vd-filter-category"><strong>${esc(t(state.locale, "User-defined", "تعریف‌شده توسط کاربر"))}</strong><p class="cp-vd-note">${esc(t(state.locale, "No user filters in this preview.", "در این پیش‌نمایش فیلتر کاربر وجود ندارد."))}</p></div>
        </div>
        <div class="cp-vd-filter-definition">
          <div class="cp-vd-form">
            <label>${esc(t(state.locale, "Filter name", "نام فیلتر"))}<input name="filterName" value="${esc(state.filter || "Six-week lookahead")}" readonly></label>
            <label>${esc(t(state.locale, "Filter scope", "دامنه فیلتر"))}<select disabled><option>Project layout</option><option>User</option><option>All Users</option><option>Another User</option><option>Current User</option><option>Project</option></select></label>
          </div>
          <fieldset><legend>${esc(t(state.locale, "Show activities that match", "نمایش فعالیت‌های منطبق با"))}</legend>
            <label><input type="radio" name="filterMatch" checked> ${esc(t(state.locale, "All selected filters", "همه فیلترهای انتخاب‌شده"))}</label>
            <label><input type="radio" name="filterMatch"> ${esc(t(state.locale, "Any selected filter", "هر یک از فیلترهای انتخاب‌شده"))}</label>
          </fieldset>
          <div class="cp-vd-filter-rules-head"><strong>${esc(t(state.locale, "Filter definition", "تعریف فیلتر"))}</strong><span>${esc(t(state.locale, "Match all / any criteria", "انطباق با همه / هر معیار"))}</span></div>
          <div class="cp-vd-filter-logic"><label><input type="radio" name="criteriaLogic" checked> ${esc(t(state.locale, "All of the following", "همه موارد زیر"))}</label><label><input type="radio" name="criteriaLogic"> ${esc(t(state.locale, "Any of the following", "هر یک از موارد زیر"))}</label></div>
          <div class="cp-vd-tablewrap"><table class="cp-vd-mini cp-vd-filter-table"><thead><tr><th>${esc(t(state.locale, "Parameter", "پارامتر"))}</th><th>${esc(t(state.locale, "Is", "شرط"))}</th><th>${esc(t(state.locale, "Value", "مقدار"))}</th></tr></thead><tbody>
            <tr><td><select aria-label="Parameter"><option>Activity Status</option><option>Activity ID</option><option>Activity Name</option><option>Activity Type</option><option>Start</option><option>Finish</option><option>Total Float</option><option>% Complete</option><option>WBS</option><option>Calendar</option><option>Primary Constraint</option><option>Resource</option></select></td><td><select aria-label="Operator"><option>Equals</option><option>Is not equal to</option><option>Is less than</option><option>Is less than or equal to</option><option>Is greater than</option><option>Is greater than or equal to</option><option>Is within range of</option><option>Is not within range of</option><option>Contains</option><option>Does not contain</option><option>Is empty</option><option>Is not empty</option></select></td><td><select aria-label="Value"><option>In Progress</option><option>Completed</option><option>Not Started</option></select></td></tr>
            <tr><td><select aria-label="Parameter"><option>Total Float</option><option>Activity Status</option><option>Activity ID</option><option>Start</option><option>Finish</option><option>% Complete</option></select></td><td><select aria-label="Operator"><option>Is less than</option><option>Equals</option><option>Is greater than</option><option>Is within range of</option></select></td><td><input aria-label="Value" value="0d" readonly></td></tr>
            <tr><td><select aria-label="Parameter"><option>Start</option><option>Finish</option><option>Activity Status</option></select></td><td><select aria-label="Operator"><option>Is within range of</option><option>Is greater than</option><option>Is less than</option></select></td><td><input aria-label="Value" value="Current Date + 6w" readonly></td></tr>
          </tbody></table></div>
          <div class="cp-vd-inline-actions"><button type="button" disabled>Add</button><button type="button" disabled>Delete</button><button type="button" disabled>▲</button><button type="button" disabled>▼</button><button type="button" disabled>Optimize</button><button type="button" disabled>Make Global</button></div>
          <p class="cp-vd-note">${esc(t(state.locale, "Criteria, operators, All/Any logic, filter categories and row controls are shown for visual review only. Nothing is applied or saved.", "معیارها، عملگرها، منطق همه/هرکدام، گروه‌های فیلتر و کنترل ردیف‌ها صرفاً برای بازبینی بصری هستند؛ هیچ موردی اعمال یا ذخیره نمی‌شود."))}</p>
        </div>
      </div>`;
    case "group-sort":
      return `<div class="cp-vd-group-sort">
        <div class="cp-vd-group-sort-section">
          <div class="cp-vd-filter-rules-head"><strong>${esc(t(state.locale, "Group By", "گروه‌بندی بر اساس"))}</strong><span>${esc(t(state.locale, "Up to 20 grouping levels", "تا ۲۰ سطح گروه‌بندی"))}</span></div>
          <div class="cp-vd-tablewrap"><table class="cp-vd-mini cp-vd-group-table"><thead><tr><th>#</th><th>${esc(t(state.locale, "Field", "فیلد"))}</th><th>${esc(t(state.locale, "Sort order", "ترتیب"))}</th><th>${esc(t(state.locale, "To level", "تا سطح"))}</th><th>${esc(t(state.locale, "Font & Color", "قلم و رنگ"))}</th></tr></thead><tbody>
            <tr><td>1</td><td><select aria-label="Group field"><option>WBS</option><option>WBS Path</option><option>Activity Type</option><option>Activity Status</option><option>Responsible Manager</option><option>Calendar</option><option>Activity Code</option><option>Resource</option><option>Role</option><option>Total Float</option><option>Start</option><option>Finish</option><option>Project</option><option>Custom Field</option></select></td><td><select aria-label="Group sort order"><option>Ascending</option><option>Descending</option><option>Hierarchical</option></select></td><td><select aria-label="Hierarchy level"><option>All levels</option><option>Level 1</option><option>Level 2</option><option>Level 3</option><option>Level 4</option><option>Level 5</option></select></td><td><button type="button" disabled>Font…</button><button type="button" disabled>Color…</button></td></tr>
            <tr><td>2</td><td><select aria-label="Group field"><option>Activity Type</option><option>WBS</option><option>Activity Status</option><option>Responsible Manager</option><option>Calendar</option><option>Activity Code</option><option>Total Float</option><option>Start</option><option>Finish</option></select></td><td><select aria-label="Group sort order"><option>Ascending</option><option>Descending</option><option>Hierarchical</option></select></td><td><select aria-label="Hierarchy level"><option>All levels</option><option>Level 1</option><option>Level 2</option><option>Level 3</option></select></td><td><button type="button" disabled>Font…</button><button type="button" disabled>Color…</button></td></tr>
            <tr><td>3</td><td><select aria-label="Group field"><option>Activity Status</option><option>Activity Type</option><option>WBS</option><option>Start</option><option>Finish</option><option>Total Float</option></select></td><td><select aria-label="Group sort order"><option>Ascending</option><option>Descending</option></select></td><td>—</td><td><button type="button" disabled>Font…</button><button type="button" disabled>Color…</button></td></tr>
          </tbody></table></div>
          <div class="cp-vd-inline-actions"><button type="button" disabled>Add group</button><button type="button" disabled>Delete</button><button type="button" disabled>▲</button><button type="button" disabled>▼</button></div>
          <div class="cp-vd-group-band-options">
            <label><input type="checkbox" checked> Indent hierarchical groups</label>
            <label><input type="checkbox"> Sort grouping bands alphabetically</label>
            <label><input type="checkbox" checked> Show field title</label>
            <label><input type="checkbox" checked> Show ID / Code</label>
            <label><input type="checkbox" checked> Show Name / Description</label>
            <label><input type="checkbox"> Show empty title bands</label>
            <label><input type="checkbox"> Page break after group band</label>
            <label><input type="checkbox" checked> Show group totals</label>
            <label><input type="checkbox"> Show grand total</label>
          </div>
        </div>
        <div class="cp-vd-group-sort-section">
          <div class="cp-vd-filter-rules-head"><strong>${esc(t(state.locale, "Sort", "مرتب‌سازی"))}</strong><span>${esc(t(state.locale, "Multiple sort criteria", "چند معیار مرتب‌سازی"))}</span></div>
          <div class="cp-vd-tablewrap"><table class="cp-vd-mini cp-vd-sort-table"><thead><tr><th>#</th><th>${esc(t(state.locale, "Field name", "نام فیلد"))}</th><th>${esc(t(state.locale, "Sort order", "ترتیب"))}</th></tr></thead><tbody>
            <tr><td>1</td><td><select aria-label="Sort field"><option>Activity ID</option><option>Activity Name</option><option>WBS</option><option>Early Start</option><option>Early Finish</option><option>Total Float</option><option>Activity Status</option><option>Activity Type</option><option>Finish</option></select></td><td><select aria-label="Sort direction"><option>Ascending</option><option>Descending</option><option>Hierarchical</option></select></td></tr>
            <tr><td>2</td><td><select aria-label="Sort field"><option>Early Start</option><option>Activity ID</option><option>Activity Name</option><option>Total Float</option><option>Finish</option></select></td><td><select aria-label="Sort direction"><option>Ascending</option><option>Descending</option><option>Hierarchical</option></select></td></tr>
          </tbody></table></div>
          <div class="cp-vd-inline-actions"><button type="button" disabled>Add sort</button><button type="button" disabled>Delete</button><button type="button" disabled>▲</button><button type="button" disabled>▼</button></div>
          <p class="cp-vd-note">${esc(t(state.locale, "Grouping is applied before sorting. Hierarchical order is available only for hierarchical fields. WBS is the default grouping in the activity layout.", "گروه‌بندی پیش از مرتب‌سازی اعمال می‌شود. ترتیب سلسله‌مراتبی فقط برای فیلدهای سلسله‌مراتبی در دسترس است. گروه‌بندی پیش‌فرض فعالیت‌ها بر اساس ساختار شکست کار است."))}</p>
        </div>
        <p class="cp-vd-note">${esc(t(state.locale, "Group levels, sort criteria, band formatting and print options are visual examples only; this dialog does not save layout settings.", "سطوح گروه‌بندی، معیارهای مرتب‌سازی، قالب نوارها و گزینه‌های چاپ صرفاً نمونه بصری هستند؛ این پنجره تنظیمات چیدمان را ذخیره نمی‌کند."))}</p>
      </div>`;
    case "timescale":
      return `<div class="cp-vd-timescale-editor">
        <div class="cp-vd-form cp-vd-timescale-top">
          <label>${esc(t(state.locale, "Timescale lines", "ردیف‌های مقیاس زمانی"))}<select><option>Two Lines</option><option>Three Lines</option></select></label>
          <label>${esc(t(state.locale, "Timescale start", "شروع مقیاس زمانی"))}<input type="date" value="2026-11-02"></label>
          <label>${esc(t(state.locale, "Date interval", "بازه تاریخ"))}<select><option>Week / Day</option><option>Month / Week</option><option>Quarter / Month</option><option>Year / Month</option><option>Day / Shift</option><option>Year / Financial Period</option><option>Quarter / Financial Period</option><option>Month / Financial Period</option><option>Week / Financial Period</option></select></label>
          <label>${esc(t(state.locale, "Type", "نوع"))}<select><option>Calendar</option><option>Fiscal</option></select></label>
        </div>
        <section class="cp-vd-timescale-section">
          <h4>${esc(t(state.locale, "Date Format", "قالب تاریخ"))}</h4>
          <div class="cp-vd-timescale-options">
            <label><input type="radio" name="dateFormat" checked> ${esc(t(state.locale, "Show Primary Dates", "نمایش تاریخ‌های اصلی"))}</label>
            <label><input type="radio" name="dateFormat"> ${esc(t(state.locale, "Show Ordinal Dates", "نمایش تاریخ‌های ترتیبی"))}</label>
          </div>
          <div class="cp-vd-form cp-vd-timescale-grid">
            <label>${esc(t(state.locale, "Primary date format", "قالب تاریخ اصلی"))}<select><option>Month / Day</option><option>Day / Month</option><option>Month / Year</option><option>Quarter / Year</option><option>Week / Year</option><option>Year</option></select></label>
            <label>${esc(t(state.locale, "Ordinal start", "شروع ترتیبی"))}<input type="date" value="2026-11-02"></label>
            <label>${esc(t(state.locale, "Ordinal interval", "بازه ترتیبی"))}<select><option>Day</option><option>Week</option><option>Month</option><option>Quarter</option></select></label>
            <label>${esc(t(state.locale, "Shift calendar", "تقویم شیفت"))}<select><option>Project default</option><option>Day shift</option><option>Night shift</option></select></label>
            <label>${esc(t(state.locale, "Financial period calendar", "تقویم دوره مالی"))}<select><option>Project financial periods</option><option>Corporate fiscal periods</option></select></label>
          </div>
        </section>
        <section class="cp-vd-timescale-section">
          <h4>${esc(t(state.locale, "Font & Color", "قلم و رنگ"))}</h4>
          <div class="cp-vd-form cp-vd-timescale-grid">
            <label>${esc(t(state.locale, "Font", "قلم"))}<select><option>Workspace default</option><option>Inter 9</option><option>Inter 10</option><option>Inter 11</option><option>Vazirmatn 10</option><option>Vazirmatn 11</option></select></label>
            <label>${esc(t(state.locale, "Text color", "رنگ متن"))}<input type="color" value="#294765"></label>
            <label>${esc(t(state.locale, "Column heading color", "رنگ عنوان ستون"))}<input type="color" value="#526579"></label>
          </div>
          <div class="cp-vd-inline-actions"><button type="button" disabled>Font & Color…</button><button type="button" disabled>Default Font</button></div>
        </section>
        <div class="cp-vd-timescale-preview"><strong>${esc(t(state.locale, "Preview", "پیش‌نمایش"))}</strong><div class="cp-vd-timescale-ruler"><span>Nov 2026</span><span>Dec 2026</span><span>Jan 2027</span><span>Feb 2027</span><span>Mar 2027</span></div><div class="cp-vd-timescale-ruler is-minor"><span>W45</span><span>W49</span><span>W01</span><span>W05</span><span>W09</span></div></div>
        <p class="cp-vd-note">${esc(t(state.locale, "Timescale applies to the visible Gantt/profile/spreadsheet layout. Font, date format and interval controls are preview-only and do not change project dates or calendar rules.", "مقیاس زمانی بر چیدمان قابل مشاهده گانت/پروفایل/صفحه مصرف اعمال می‌شود. کنترل‌های قلم، قالب تاریخ و بازه صرفاً پیش‌نمایش هستند و تاریخ پروژه یا قوانین تقویم را تغییر نمی‌دهند."))}</p>
      </div>`;
    case "bars":
      return `<div class="cp-vd-form cp-vd-bar-editor">
        <p class="cp-vd-note">${esc(t(state.locale, "Configure each Gantt bar as an independent display rule: visibility, name, timescale, filter, style, settings and labels.", "هر میله گانت یک قاعده نمایشی مستقل است: نمایش، نام، مقیاس زمانی، فیلتر، سبک، تنظیمات و برچسب‌ها."))}</p>
        ${rows(["Display", "Bar name", "Timescale", "Activity filter", "Preview"], `<tr><td><input type="checkbox" checked aria-label="Display Remaining Work"></td><td>Remaining Work</td><td>Current</td><td>Incomplete activities</td><td><span class="cp-vd-bar-preview" style="background:#2f5fa8"></span></td></tr><tr><td><input type="checkbox" checked aria-label="Display Actual Work"></td><td>Actual Work</td><td>Current</td><td>Actual start is not empty</td><td><span class="cp-vd-bar-preview" style="background:#4f9a3c"></span></td></tr><tr><td><input type="checkbox" checked aria-label="Display Critical Remaining"></td><td>Critical Remaining</td><td>Current</td><td>Total float ≤ 0</td><td><span class="cp-vd-bar-preview" style="background:#c0392b"></span></td></tr><tr><td><input type="checkbox" checked aria-label="Display Primary Baseline"></td><td>Primary Baseline</td><td>Baseline</td><td>All activities</td><td><span class="cp-vd-bar-preview is-outline"></span></td></tr><tr><td><input type="checkbox" aria-label="Display Target"></td><td>Target</td><td>Target</td><td>Target dates available</td><td><span class="cp-vd-bar-preview" style="background:#8b6bb1"></span></td></tr><tr><td><input type="checkbox" checked aria-label="Display Summary"></td><td>Summary</td><td>Current</td><td>WBS summary</td><td><span class="cp-vd-bar-preview is-bracket"></span></td></tr><tr><td><input type="checkbox" checked aria-label="Display Level of Effort"></td><td>Level of Effort</td><td>Current</td><td>Activity type = LOE</td><td><span class="cp-vd-bar-preview" style="background:#6c8c9e"></span></td></tr><tr><td><input type="checkbox" checked aria-label="Display Milestone"></td><td>Milestone</td><td>Current</td><td>Activity type = milestone</td><td><span class="cp-vd-bar-preview is-diamond"></span></td></tr>`)}
        <div class="cp-vd-inline-actions"><button type="button">Add</button><button type="button">Remove</button><button type="button">Copy From…</button><button type="button">Move Up</button><button type="button">Move Down</button></div>
        <div class="cp-vd-subtabs" role="tablist" aria-label="Bar definition properties"><button type="button" role="tab" aria-selected="true">Bar Style</button><button type="button" role="tab" aria-selected="false">Bar Settings</button><button type="button" role="tab" aria-selected="false">Bar Labels</button></div>
        <section class="cp-vd-bar-editor-section"><h4>Bar Style</h4><div class="cp-vd-two"><label>Shape<select><option>Bar</option><option>Line</option><option>Start milestone</option><option>Finish milestone</option><option>Start and finish milestone</option><option>Bracket</option></select></label><label>Pattern<select><option>Solid</option><option>Hatched</option><option>Dashed</option><option>Dotted</option><option>Outline</option></select></label><label>Color<input type="color" value="#2f5fa8"></label><label>Border color<input type="color" value="#244b85"></label><label>Start point<select><option>Activity Start</option><option>Early Start</option><option>Actual Start</option><option>Baseline Start</option><option>Remaining Start</option></select></label><label>End point<select><option>Activity Finish</option><option>Early Finish</option><option>Actual Finish</option><option>Baseline Finish</option><option>Remaining Finish</option></select></label></div><div class="cp-vd-bar-preview-large"><span></span><small>Live style preview</small></div></section>
        <section class="cp-vd-bar-editor-section"><h4>Bar Settings</h4><div class="cp-vd-two"><label>Grouping<select><option>By activity</option><option>By bar definition</option></select></label><label>Necking<select><option>Show non-work periods as necking</option><option>Do not neck bars</option></select></label><label>Position<select><option>Top</option><option>Middle</option><option>Bottom</option></select></label><label>Height<select><option>16 px</option><option>12 px</option><option>14 px</option><option>18 px</option><option>20 px</option></select></label></div><label class="cp-vd-check"><input type="checkbox" checked> Show bar when activity is in progress</label><label class="cp-vd-check"><input type="checkbox"> Collapse overlapping bars</label></section>
        <section class="cp-vd-bar-editor-section"><h4>Bar Labels</h4><div class="cp-vd-two"><label>Left label<select><option>None</option><option>Activity ID</option><option>Activity Name</option><option>Start</option><option>Finish</option></select></label><label>Right label<select><option>Activity Name</option><option>Activity ID</option><option>Finish</option><option>Remaining Duration</option><option>Total Float</option><option>% Complete</option></select></label><label>Top label<select><option>None</option><option>Activity ID</option><option>Activity Name</option><option>Start</option></select></label><label>Bottom label<select><option>None</option><option>Activity Name</option><option>Original Duration</option><option>Remaining Duration</option><option>Total Float</option></select></label><label>Label font<select><option>Workspace default</option><option>Inter 10</option><option>Inter 11</option><option>Vazirmatn 11</option></select></label><label>Label color<input type="color" value="#344256"></label></div></section>
        <p class="cp-vd-note">Preview only — these bar definitions and controls do not persist layout settings.</p>
      </div>`;
    case "bar-options":
      return `<div class="cp-vd-form"><div class="cp-vd-two"><label>Activity row height<select><option>24 px</option><option>20 px</option><option>28 px</option><option>32 px</option></select></label><label>Bar height<select><option>16 px</option><option>12 px</option><option>14 px</option><option>18 px</option><option>20 px</option></select></label><label>Bar label position<select><option>Right of bar</option><option>Left of bar</option><option>Inside bar</option><option>Above bar</option><option>Below bar</option></select></label><label>Bar label field<select><option>Activity Name</option><option>Activity ID</option><option>Start</option><option>Finish</option><option>Remaining Duration</option><option>Total Float</option><option>% Complete</option></select></label><label>Bar time position<select><option>Current schedule dates</option><option>Baseline dates</option><option>Target dates</option></select></label><label>Summary bar position<select><option>Top</option><option>Middle</option><option>Bottom</option></select></label></div><div class="cp-vd-two"><label class="cp-vd-check"><input type="checkbox" checked> Show relationship lines</label><label class="cp-vd-check"><input type="checkbox" checked> Show bar labels</label><label class="cp-vd-check"><input type="checkbox" checked> Show critical path styling</label><label class="cp-vd-check"><input type="checkbox"> Collapse summary bars</label><label class="cp-vd-check"><input type="checkbox" checked> Show baseline bars</label><label class="cp-vd-check"><input type="checkbox"> Show float bars</label><label class="cp-vd-check"><input type="checkbox" checked> Show milestone symbols</label><label class="cp-vd-check"><input type="checkbox"> Show bar borders</label><label class="cp-vd-check"><input type="checkbox" checked> Show nonworking time</label></div><p class="cp-vd-note">Display controls only; no activity dates, durations or schedule calculations are changed.</p></div>`;
    case "font-row":
      return `<div class="cp-vd-form"><div class="cp-vd-two"><section><h4>Activity table appearance</h4><label>Table font<select><option>Inter 10</option><option>Inter 11</option><option>Inter 12</option><option>Vazirmatn 11</option><option>Vazirmatn 12</option></select></label><label>Text color<input type="color" value="#26384d"></label><label>Row height<select><option>24 px</option><option>20 px</option><option>28 px</option><option>32 px</option><option>Auto fit</option></select></label><label>Row background<select><option>White</option><option>Alternate shading</option><option>Selected row emphasis</option></select></label><label>Grid lines<select><option>Horizontal and vertical</option><option>Horizontal only</option><option>None</option></select></label></section><section><h4>Group row appearance</h4><label>Group font<select><option>Inter 11 Semibold</option><option>Inter 10</option><option>Vazirmatn 11 Semibold</option></select></label><label>Group text color<input type="color" value="#244463"></label><label>Group background<input type="color" value="#edf2f7"></label><label>Group row height<select><option>28 px</option><option>24 px</option><option>32 px</option></select></label><label>Group band format<select><option>WBS code and name</option><option>Field title and value</option><option>Value only</option></select></label></section></div><div class="cp-vd-two"><label class="cp-vd-check"><input type="checkbox" checked> Bold group rows</label><label class="cp-vd-check"><input type="checkbox" checked> Show group totals</label><label class="cp-vd-check"><input type="checkbox"> Show empty title bands</label><label class="cp-vd-check"><input type="checkbox"> Page break after each group</label></div><p class="cp-vd-note">Typography and row formatting are preview-only and are not saved to a layout.</p></div>`;
    case "layout-manager": {
      const layouts = [
        { name: "CUBI Classic Schedule", scope: "Project", owner: "Current project", status: "Current", modified: "03-Nov-2026", description: "Activity table with Gantt bars, critical path and baseline comparison." },
        { name: "Cost and Resource Control", scope: "Project", owner: "Current project", status: "Available", modified: "28-Oct-2026", description: "Budgeted, actual and remaining units and costs with resource assignments." },
        { name: "Commissioning Look-ahead", scope: "User", owner: "Current user", status: "Available", modified: "24-Oct-2026", description: "Near-term activities grouped by WBS and responsible discipline." },
        { name: "Executive Milestones", scope: "All Users", owner: "Shared library", status: "Available", modified: "18-Oct-2026", description: "Milestones, key dates, project codes and summary progress." },
        { name: "Field Engineer Daily View", scope: "Another User", owner: "Assigned user", status: "Available", modified: "12-Oct-2026", description: "Activity status and daily field reporting columns." },
      ];
      return `<section class="cp-vd-layout-manager">
        <div class="cp-vd-layout-toolbar" role="toolbar" aria-label="${esc(t(state.locale, "Layout actions", "فرمان‌های چیدمان"))}">
          <button type="button" disabled>＋ ${esc(t(state.locale, "New", "جدید"))}</button>
          <button type="button" disabled>${esc(t(state.locale, "Apply", "اعمال"))}</button>
          <button type="button" disabled>▣ ${esc(t(state.locale, "Open", "بازکردن"))}</button>
          <button type="button" disabled>↥ ${esc(t(state.locale, "Save", "ذخیره"))}</button>
          <button type="button" disabled>${esc(t(state.locale, "Save As…", "ذخیره با نام…"))}</button>
          <button type="button" disabled>${esc(t(state.locale, "Delete", "حذف"))}</button>
          <button type="button" disabled>${esc(t(state.locale, "Import .PLF…", "ورود فایل .PLF…"))}</button>
          <button type="button" disabled>${esc(t(state.locale, "Export .PLF…", "خروجی فایل .PLF…"))}</button>
          <span class="cp-vd-note">${esc(t(state.locale, "Preview only — layout storage is not connected.", "پیش‌نمایش — ذخیره‌سازی چیدمان متصل نیست."))}</span>
        </div>
        <div class="cp-vd-layout-manager-grid">
          <div class="cp-vd-layout-list">
            <div class="cp-vd-layout-list-head"><strong>${esc(t(state.locale, "Available layouts", "چیدمان‌های موجود"))}</strong><label>${esc(t(state.locale, "Scope", "دامنه"))}<select disabled><option>All layouts</option><option>Project</option><option>Current User</option><option>Another User</option><option>All Users</option></select></label></div>
            <label class="cp-vd-layout-search"><span>${esc(t(state.locale, "Find layout", "جست‌وجوی چیدمان"))}</span><input type="search" placeholder="${esc(t(state.locale, "Search by name…", "جست‌وجو بر اساس نام…"))}" disabled></label>
            <table class="cp-vd-mini"><thead><tr><th></th><th>${esc(t(state.locale, "Name", "نام"))}</th><th>${esc(t(state.locale, "Scope", "دامنه"))}</th><th>${esc(t(state.locale, "Status", "وضعیت"))}</th></tr></thead><tbody>
              ${layouts.map((layout,index)=>`<tr class="${index===0?"is-selected":""}"><td><input type="radio" name="vd-layout-choice" ${index===0?"checked":""} disabled aria-label="${esc(layout.name)}"></td><td><strong>${esc(layout.name)}</strong><small>${esc(layout.owner)}</small></td><td>${esc(t(state.locale,layout.scope,layout.scope==="Project"?"پروژه":layout.scope==="User"?"کاربر":"سراسری"))}</td><td>${esc(t(state.locale,layout.status,layout.status==="Current"?"فعلی":"موجود"))}</td></tr>`).join("")}
            </tbody></table>
          </div>
          <aside class="cp-vd-layout-properties"><h3>${esc(t(state.locale, "Layout properties", "مشخصات چیدمان"))}</h3>
            <dl><div><dt>${esc(t(state.locale, "Name", "نام"))}</dt><dd>CUBI Classic Schedule</dd></div><div><dt>${esc(t(state.locale, "Scope", "دامنه"))}</dt><dd>Project</dd></div><div><dt>${esc(t(state.locale, "Owner", "مالک"))}</dt><dd>Current project</dd></div><div><dt>${esc(t(state.locale, "Last modified", "آخرین تغییر"))}</dt><dd>03-Nov-2026</dd></div><div><dt>${esc(t(state.locale, "Description", "شرح"))}</dt><dd>${esc(layouts[0].description)}</dd></div></dl>
            <label class="cp-vd-layout-default"><input type="checkbox" checked disabled> ${esc(t(state.locale, "Use as default layout for this project", "استفاده به‌عنوان چیدمان پیش‌فرض پروژه"))}</label>
            <fieldset disabled><legend>${esc(t(state.locale, "Sharing", "اشتراک‌گذاری"))}</legend><label><input type="radio" name="vd-layout-scope" checked> Project</label><label><input type="radio" name="vd-layout-scope"> User</label><label><input type="radio" name="vd-layout-scope"> Global</label></fieldset>
          </aside>
        </div>
        <p class="cp-vd-note">${esc(t(state.locale, "Layouts may be project-, user-, or globally-scoped. New, Open, Save, Save As, Delete, import/export and default-layout actions remain disabled until the layout service and permission checks are connected.", "چیدمان می‌تواند در دامنه پروژه، کاربر یا سراسری باشد. عملیات ایجاد، بازکردن، ذخیره، ذخیره با نام، حذف، ورود/خروجی و تعیین پیش‌فرض تا اتصال سرویس چیدمان و کنترل دسترسی غیرفعال هستند."))}</p>
      </section>`;
    }
    case "customize-details": {
      // Desktop Details customization exposes the complete standard tab set.
      // Tasks is intentionally excluded because it is not part of the desktop edition.
      const availableTabs: Array<[string, string, string]> = [
        ["successors", "Successors", "جانشین‌ها"],
        ["codes", "Codes", "کدها"],
        ["discussion", "Discussion", "گفت‌وگو"],
        ["notebook", "Notebook", "دفترچه"],
        ["steps", "Steps", "گام‌ها"],
        ["feedback", "Feedback", "بازخورد"],
        ["documents", "Documents", "اسناد"],
        ["expenses", "Expenses", "هزینه‌ها"],
        ["summary", "Summary", "خلاصه"],
        ["relationships", "Relationships", "روابط"],
        ["risks", "Risks", "ریسک‌ها"],
        ["custom-fields", "Custom Fields", "فیلدهای سفارشی"],
        ["update-history", "Update History", "تاریخچه تغییرات"],
      ];
      const displayedTabs: Array<[string, string, string]> = [
        ["general", "General", "عمومی"],
        ["status", "Status", "وضعیت"],
        ["resources", "Resources", "منابع"],
        ["predecessors", "Predecessors", "پیش‌نیازها"],
        ["codes", "Codes", "کدها"],
      ];
      const tabItem = ([id, en, fa]: [string, string, string], checked: boolean): string =>
        `<li data-vd-detail-tab-row="${id}"><label><input type="checkbox" name="detail-tab-${id}" data-vd-detail-tab="${id}" ${checked ? "checked" : ""}> ${esc(t(state.locale, en, fa))}</label>${checked ? `<span class="cp-vd-inline-actions"><button type="button" disabled aria-label="Move ${esc(en)} up" title="Move up">↑</button><button type="button" disabled aria-label="Move ${esc(en)} down" title="Move down">↓</button></span>` : ""}</li>`;
      return `<div class="cp-vd-details-customize">
        <div class="cp-vd-two">
          <section><strong>${esc(t(state.locale, "Available tabs", "زبانه‌های موجود"))}</strong><ul>${availableTabs.map((tab) => tabItem(tab, false)).join("")}</ul></section>
          <section><strong>${esc(t(state.locale, "Displayed tabs · example order", "زبانه‌های نمایشی · ترتیب نمونه"))}</strong><ol>${displayedTabs.map((tab) => tabItem(tab, true)).join("")}</ol></section>
        </div>
        <p class="cp-vd-note">${esc(t(state.locale, "Standard desktop Details tabs are listed. Selectable controls are a visual preview; tab visibility and order are not saved in this build.", "همه زبانه‌های استاندارد جزئیات نسخه دسکتاپ فهرست شده‌اند. کنترل‌ها پیش‌نمایش بصری هستند و ترتیب یا نمایش زبانه‌ها در این نسخه ذخیره نمی‌شود."))}</p>
      </div>`;
    }
    case "new-wbs":
      return `<div class="cp-vd-form"><label>${esc(t(state.locale, "WBS code", "کد WBS"))}<input name="wbsCode" value="1.6" required></label><label>${esc(t(state.locale, "WBS name", "نام WBS"))}<input name="wbsName" placeholder="New work package" required></label><label>${esc(t(state.locale, "Parent WBS", "WBS والد"))}<select name="parent"><option>1 — CUBI-DEMO-001 Riverside Pump Station</option><option>1.1 — Project Management</option><option>1.2 — Engineering</option><option>1.3 — Procurement</option><option>1.4 — Construction</option><option>1.5 — Testing & Commissioning</option></select></label><label>${esc(t(state.locale, "Responsible manager", "مدیر مسئول"))}<select><option>Project Manager</option><option>Engineering Manager</option><option>Construction Manager</option></select></label><p class="cp-vd-note">${esc(t(state.locale, "Visual preview only — no WBS record will be saved.", "صرفاً پیش‌نمایش بصری — رکورد WBS ذخیره نمی‌شود."))}</p></div>`;
    case "new-form":
      return `<div class="cp-vd-form"><label>${esc(t(state.locale, "Form ID", "شناسه فرم"))}<input name="formId" value="FRM-NEW-001"></label><label>${esc(t(state.locale, "Form title", "عنوان فرم"))}<input name="formTitle" placeholder="New inspection form"></label><label>${esc(t(state.locale, "Library", "کتابخانه"))}<select name="library"><option>Organization library</option><option>Project library</option></select></label><label>${esc(t(state.locale, "Version", "نسخه"))}<input value="1.0"></label><label>${esc(t(state.locale, "Workflow", "گردش کار"))}<select><option>Submit → Review → Approve</option><option>Submit → Verify → Close</option><option>Submit → Return for correction → Resubmit</option></select></label><label>${esc(t(state.locale, "Form access", "دسترسی فرم"))}<select><option>Assigned form users</option><option>Project team</option><option>Organization administrators</option></select></label><p class="cp-vd-note">${esc(t(state.locale, "Organization templates are reusable; project forms remain scoped to this project. Preview only.", "قالب‌های سازمانی قابل استفاده مجدد هستند؛ فرم‌های پروژه در محدوده همین پروژه می‌مانند. صرفاً پیش‌نمایش."))}</p></div>`;
    case "new-project":
      return `<div class="cp-vd-project-wizard">
        <ol class="cp-vd-project-steps" aria-label="Project creation steps">
          <li aria-current="step"><b>1</b><span>${esc(t(state.locale, "Business Domain", "حوزه کسب‌وکار"))}</span></li>
          <li><b>2</b><span>${esc(t(state.locale, "Identity", "مشخصات"))}</span></li>
          <li><b>3</b><span>${esc(t(state.locale, "Configuration", "پیکربندی"))}</span></li>
          <li><b>4</b><span>${esc(t(state.locale, "Development", "توسعه ساختار"))}</span></li>
        </ol>
        <section class="cp-vd-project-step"><h4>1 · ${esc(t(state.locale, "Business Domain", "حوزه کسب‌وکار"))}</h4><div class="cp-vd-form cp-vd-project-grid">
          <label>${esc(t(state.locale, "Business domain", "حوزه کسب‌وکار"))}<select required><option value="">${esc(t(state.locale, "Select a domain…", "انتخاب حوزه…"))}</option><option>Construction</option><option>Oil & Gas</option><option>Infrastructure</option><option>Industrial</option><option>Energy</option><option>Other</option></select></label>
          <label>${esc(t(state.locale, "Portfolio", "سبد پروژه"))}<select><option>None</option><option>Capital Projects</option><option>Infrastructure Programme</option></select></label>
          <label>${esc(t(state.locale, "Responsible organization", "سازمان مسئول"))}<select><option>Choose organization…</option><option>Project Management Office</option><option>Engineering</option><option>Construction</option></select></label>
        </div></section>
        <section class="cp-vd-project-step"><h4>2 · ${esc(t(state.locale, "Project Identity", "مشخصات پروژه"))}</h4><div class="cp-vd-form cp-vd-project-grid">
          <label>${esc(t(state.locale, "Project name", "نام پروژه"))} <em>*</em><input name="projectName" required minlength="2" maxlength="120" placeholder="${esc(t(state.locale, "Enter project name", "نام پروژه را وارد کنید"))}"></label>
          <label>${esc(t(state.locale, "Project ID", "شناسه پروژه"))} <em>*</em><input name="projectId" required pattern="[A-Z0-9][A-Z0-9_-]{1,39}" placeholder="AUTO-GENERATED"><small>${esc(t(state.locale, "Suggested from name; tenant uniqueness check is not connected.", "از نام پیشنهاد می‌شود؛ بررسی یکتایی در این پیش‌نمایش متصل نیست."))}</small></label>
          <label class="is-wide">${esc(t(state.locale, "Description", "شرح"))}<textarea maxlength="2000" rows="2" placeholder="${esc(t(state.locale, "Optional project description", "شرح اختیاری پروژه"))}"></textarea></label>
        </div></section>
        <section class="cp-vd-project-step"><h4>3 · ${esc(t(state.locale, "Planning Configuration", "پیکربندی برنامه‌ریزی"))}</h4><div class="cp-vd-form cp-vd-project-grid">
          <label>${esc(t(state.locale, "Start date", "تاریخ شروع"))} <em>*</em><input type="date" required></label>
          <label>${esc(t(state.locale, "Target finish", "پایان هدف"))}<input type="date"></label>
          <label>${esc(t(state.locale, "Date system", "سیستم تاریخ"))}<select required><option value="gregorian">Gregorian</option><option value="jalali">Jalali</option></select></label>
          <label>${esc(t(state.locale, "Project calendar", "تقویم پروژه"))} <em>*</em><select required><option value="">Choose calendar…</option><option>5-Day Workweek</option><option>6-Day Workweek</option><option>24 Hour</option></select></label>
          <label>${esc(t(state.locale, "Default activity duration type", "نوع مدت پیش‌فرض فعالیت"))}<select><option>Fixed Duration & Units</option><option>Fixed Duration & Units/Time</option><option>Fixed Units</option><option>Fixed Units/Time</option></select></label>
        </div></section>
        <section class="cp-vd-project-step"><h4>4 · ${esc(t(state.locale, "Project Development", "توسعه ساختار پروژه"))}</h4><div class="cp-vd-form cp-vd-project-grid">
          <label>${esc(t(state.locale, "WBS template", "قالب ساختار شکست کار"))}<select><option>Blank project</option><option>Building construction</option><option>Infrastructure</option><option>Industrial plant</option></select></label>
          <label>${esc(t(state.locale, "Copy from project", "کپی از پروژه"))}<select><option>None</option><option>Choose an authorized project…</option></select></label>
          <label class="cp-vd-check"><input type="checkbox"> ${esc(t(state.locale, "Create starter WBS and activities", "ایجاد ساختار شکست کار و فعالیت‌های اولیه"))}</label>
          <label class="cp-vd-check"><input type="checkbox"> ${esc(t(state.locale, "Include resource and calendar templates", "افزودن قالب منابع و تقویم‌ها"))}</label>
        </div></section>
        <div class="cp-vd-project-wizard-actions"><button type="button" disabled>Back</button><button type="button" disabled>Next</button><button type="button" class="is-primary" disabled>Create Project</button></div>
        <p class="cp-vd-note">${esc(t(state.locale, "Required fields are marked *. Validation, ID uniqueness, project creation and template copying are not connected in this visual preview.", "فیلدهای الزامی با * مشخص شده‌اند. اعتبارسنجی، یکتایی شناسه، ایجاد پروژه و کپی قالب در این پیش‌نمایش بصری متصل نیستند."))}</p>
      </div>`;
    case "project-properties": {
      const tabs: Array<[string,string,string]> = [
        ["General","General","عمومی"],["Dates","Dates","تاریخ‌ها"],["Notebook","Notebook","دفترچه"],["Budget Log","Budget Log","گزارش بودجه"],["Spending Plan","Spending Plan","برنامه هزینه"],["Budget Summary","Budget Summary","خلاصه بودجه"],["Funding","Funding","تأمین مالی"],["Codes","Codes","کدها"],["Defaults","Defaults","پیش‌فرض‌ها"],["Resources","Resources","منابع"],["Settings","Settings","تنظیمات"],["Calculations","Calculations","محاسبات"],["Custom fields","Custom Fields","فیلدهای سفارشی"],
      ];
      return `<section class="cp-vd-project-details">
        <header class="cp-vd-project-context"><div><strong>Riverside Pump Station Upgrade</strong><span><bdi dir="ltr">CUBI-DEMO-001</bdi> · ${esc(t(state.locale,"Active project","پروژه فعال"))}</span></div><span class="cp-vd-note">${esc(t(state.locale,"Project-level details and defaults","جزئیات و پیش‌فرض‌های سطح پروژه"))}</span></header>
        <nav class="cp-vd-project-tabs" role="tablist" aria-label="${esc(t(state.locale,"Project detail sections","بخش‌های جزئیات پروژه"))}">
          ${tabs.map(([id,en,fa],index)=>`<button type="button" role="tab" aria-selected="${index===0}" class="${index===0?"is-active":""}" disabled>${esc(t(state.locale,en,fa))}</button>`).join("")}
        </nav>
        <div class="cp-vd-project-tab-panel" role="tabpanel" aria-label="${esc(t(state.locale,"General project details","جزئیات عمومی پروژه"))}">
          <div class="cp-vd-project-section"><h3>${esc(t(state.locale,"General","عمومی"))}</h3><div class="cp-vd-form">
            <label>${esc(t(state.locale,"Project ID","شناسه پروژه"))}<input value="CUBI-DEMO-001" readonly></label>
            <label>${esc(t(state.locale,"Project name","نام پروژه"))}<input value="Riverside Pump Station Upgrade" disabled></label>
            <label>${esc(t(state.locale,"Status","وضعیت"))}<select disabled><option>Active</option><option>Planned</option><option>On hold</option><option>Completed</option></select></label>
            <label>${esc(t(state.locale,"Responsible manager","مدیر مسئول"))}<select disabled><option>Project Manager</option><option>Program Manager</option></select></label>
            <label>${esc(t(state.locale,"EPS / Portfolio","ساختار سازمانی / سبد"))}<input value="Capital Projects / Water" disabled></label>
            <label>${esc(t(state.locale,"Project website","وب‌سایت پروژه"))}<input placeholder="https://" disabled></label>
          </div></div>
          <div class="cp-vd-project-section"><h3>${esc(t(state.locale,"Schedule dates","تاریخ‌های زمان‌بندی"))}</h3><div class="cp-vd-form">
            <label>${esc(t(state.locale,"Planned start","شروع برنامه‌ای"))}<input type="date" value="2026-11-02" disabled></label>
            <label>${esc(t(state.locale,"Must finish by","باید تا تاریخ پایان یابد"))}<input type="date" value="2027-05-28" disabled></label>
            <label>${esc(t(state.locale,"Data date","تاریخ داده"))}<input type="date" value="2026-12-03" disabled></label>
            <label>${esc(t(state.locale,"Calculated finish","پایان محاسبه‌شده"))}<input value="—" readonly></label>
            <label>${esc(t(state.locale,"Anticipated start","شروع پیش‌بینی‌شده"))}<input type="date" disabled></label>
            <label>${esc(t(state.locale,"Anticipated finish","پایان پیش‌بینی‌شده"))}<input type="date" disabled></label>
          </div></div>
          <div class="cp-vd-project-section"><h3>${esc(t(state.locale,"Defaults for new activities","پیش‌فرض فعالیت‌های جدید"))}</h3><div class="cp-vd-form">
            <label>${esc(t(state.locale,"Default activity type","نوع فعالیت پیش‌فرض"))}<select disabled><option>Task Dependent</option><option>Resource Dependent</option><option>Level of Effort</option></select></label>
            <label>${esc(t(state.locale,"Default duration type","نوع مدت پیش‌فرض"))}<select disabled><option>Fixed Duration & Units</option><option>Fixed Units / Time</option><option>Fixed Units</option></select></label>
            <label>${esc(t(state.locale,"Percent complete type","نوع درصد تکمیل"))}<select disabled><option>Duration</option><option>Units</option><option>Physical</option></select></label>
            <label>${esc(t(state.locale,"Default activity calendar","تقویم فعالیت پیش‌فرض"))}<select disabled><option>5-Day Workweek</option><option>6-Day Workweek</option><option>24 Hour</option></select></label>
            <label>${esc(t(state.locale,"Default rate type","نوع نرخ پیش‌فرض"))}<select disabled><option>Price per Unit</option><option>Price per Time</option></select></label>
            <label>${esc(t(state.locale,"Default cost account","حساب هزینه پیش‌فرض"))}<select disabled><option>Not assigned</option></select></label>
          </div></div>
          <div class="cp-vd-project-section"><h3>${esc(t(state.locale,"Resource assignment defaults","پیش‌فرض تخصیص منابع"))}</h3><div class="cp-vd-project-checks">
            <label><input type="checkbox" checked disabled> ${esc(t(state.locale,"Drive activity dates by default","هدایت تاریخ‌های فعالیت به‌صورت پیش‌فرض"))}</label>
            <label><input type="checkbox" disabled> ${esc(t(state.locale,"Allow the same resource to be assigned more than once","اجازه تخصیص چندباره یک منبع به فعالیت"))}</label>
          </div></div>
        </div>
        <p class="cp-vd-note">${esc(t(state.locale,"All project detail tabs are inventoried. This General-tab preview is read-only; dates, defaults, financial tabs, settings and calculations are not saved or executed here. The Planning Resources tab is intentionally excluded because it is server-edition-only.", "تمام زبانه‌های جزئیات پروژه در فهرست آمده‌اند. این پیش‌نمایش زبانه عمومی فقط‌خواندنی است؛ تاریخ‌ها، پیش‌فرض‌ها، زبانه‌های مالی، تنظیمات و محاسبات در اینجا ذخیره یا اجرا نمی‌شوند. زبانه منابع برنامه‌ریزی به‌دلیل وابستگی به نسخه سرور عمداً حذف شده است."))}</p>
      </section>`;
    }
    case "calendar":
      return `<section class="cp-vd-calendar-editor">
        <header class="cp-vd-calendar-editor-toolbar"><div><strong>${esc(t(state.locale,"Calendar editor","ویرایشگر تقویم"))}</strong><span>${esc(t(state.locale,"5-Day Workweek · Global calendar","هفته کاری پنج‌روزه · تقویم سراسری"))}</span></div><div><button type="button" disabled>${esc(t(state.locale,"Modify","ویرایش"))}</button><button type="button" disabled>${esc(t(state.locale,"Time Periods…","دوره‌های زمانی…"))}</button><button type="button" disabled>${esc(t(state.locale,"Used By…","موارد استفاده…"))}</button></div></header>
        <div class="cp-vd-calendar-editor-main">
          <div class="cp-vd-calendar-properties"><h3>${esc(t(state.locale,"Calendar properties","مشخصات تقویم"))}</h3>
            <div class="cp-vd-form cp-vd-calendar-fields">
              <label>${esc(t(state.locale,"Calendar name","نام تقویم"))}<input value="5-Day Workweek" readonly></label>
              <label>${esc(t(state.locale,"Calendar pool","مخزن تقویم"))}<select disabled><option>Global</option><option>Project</option><option>Resource</option></select></label>
              <label>${esc(t(state.locale,"Calendar type","نوع تقویم"))}<select disabled><option>Standard</option><option>Shared Resource</option><option>Personal Resource</option></select></label>
              <label>${esc(t(state.locale,"Parent global calendar","تقویم سراسری والد"))}<select disabled><option>None — base calendar</option><option>Standard 5-Day</option></select></label>
              <label>${esc(t(state.locale,"Hours per day","ساعت در روز"))}<input value="8" readonly></label>
              <label>${esc(t(state.locale,"Hours per week","ساعت در هفته"))}<input value="40" readonly></label>
              <label>${esc(t(state.locale,"Hours per month","ساعت در ماه"))}<input value="176" readonly></label>
              <label>${esc(t(state.locale,"Hours per year","ساعت در سال"))}<input value="2080" readonly></label>
              <label>${esc(t(state.locale,"Use assigned calendar time periods","استفاده از دوره‌های زمانی تقویم تخصیص‌یافته"))}<input value="Enabled by administrator" readonly></label>
            </div>
          </div>
          <div class="cp-vd-calendar-workweek"><h3>${esc(t(state.locale,"Standard workweek","هفته کاری استاندارد"))}</h3>
            <table class="cp-vd-mini"><thead><tr><th>${esc(t(state.locale,"Day","روز"))}</th><th>${esc(t(state.locale,"Working hours","ساعات کاری"))}</th><th>${esc(t(state.locale,"Work status","وضعیت کاری"))}</th></tr></thead><tbody>
              ${[[ "Saturday", "شنبه", "08:00–12:00 · 13:00–17:00", true ],[ "Sunday", "یکشنبه", "08:00–12:00 · 13:00–17:00", true ],[ "Monday", "دوشنبه", "08:00–12:00 · 13:00–17:00", true ],[ "Tuesday", "سه‌شنبه", "08:00–12:00 · 13:00–17:00", true ],[ "Wednesday", "چهارشنبه", "08:00–12:00 · 13:00–17:00", true ],[ "Thursday", "پنجشنبه", "—", false ],[ "Friday", "جمعه", "—", false ]].map(([en, fa, hours, working]) => `<tr><td>${esc(t(state.locale,String(en),String(fa)))}</td><td><input class="cp-vd-calendar-hours" aria-label="${esc(String(en))} working hours" value="${esc(String(hours))}" disabled></td><td><label class="cp-vd-calendar-working"><input type="checkbox" ${working?"checked":""} disabled><span class="cp-vd-calendar-day-status ${working?"is-working":"is-nonwork"}">${esc(t(state.locale,working?"Working":"Nonwork",working?"کاری":"تعطیل"))}</span></label></td></tr>`).join("")}
            </tbody></table>
            <div class="cp-vd-calendar-work-modes"><label><input type="radio" name="calendar-hours-mode" checked disabled> ${esc(t(state.locale,"Total work hours/day","مجموع ساعات کاری روز"))}</label><label><input type="radio" name="calendar-hours-mode" disabled> ${esc(t(state.locale,"Detailed work hours/day","جزئیات ساعات کاری روز"))}</label></div>
          </div>
        </div>
        <div class="cp-vd-calendar-editor-bottom">
          <section><h3>${esc(t(state.locale,"Exceptions and holidays","استثناها و تعطیلات"))}</h3><table class="cp-vd-mini"><thead><tr><th>${esc(t(state.locale,"Date","تاریخ"))}</th><th>${esc(t(state.locale,"Description","شرح"))}</th><th>${esc(t(state.locale,"Type","نوع"))}</th><th>${esc(t(state.locale,"Working hours","ساعات کاری"))}</th></tr></thead><tbody><tr><td><bdi dir="ltr">2026-12-21</bdi></td><td>${esc(t(state.locale,"Winter solstice adjustment","تغییر ساعت انقلاب زمستانی"))}</td><td>${esc(t(state.locale,"Nonwork","تعطیل"))}</td><td>—</td></tr><tr><td><bdi dir="ltr">2027-03-20</bdi></td><td>${esc(t(state.locale,"Local holiday","تعطیل محلی"))}</td><td>${esc(t(state.locale,"Nonwork","تعطیل"))}</td><td>—</td></tr><tr><td><bdi dir="ltr">2027-05-01</bdi></td><td>${esc(t(state.locale,"Reduced shift","شیفت کوتاه"))}</td><td>${esc(t(state.locale,"Modified hours","ساعات اصلاح‌شده"))}</td><td>08:00–12:00</td></tr></tbody></table><div class="cp-vd-calendar-actions"><button type="button" disabled>${esc(t(state.locale,"Work","کاری"))}</button><button type="button" disabled>${esc(t(state.locale,"Nonwork","تعطیل"))}</button><button type="button" disabled>${esc(t(state.locale,"Standard","استاندارد"))}</button></div></section>
          <section><h3>${esc(t(state.locale,"Hours per time period","ساعات هر دوره زمانی"))}</h3><div class="cp-vd-form cp-vd-calendar-periods">${[["Hour","1"],["Day","8"],["Week","40"],["Month","176"],["Year","2080"]].map(([name,value])=>`<label>${esc(t(state.locale,name,name==="Hour"?"ساعت":name==="Day"?"روز":name==="Week"?"هفته":name==="Month"?"ماه":"سال"))}<input type="number" value="${value}" disabled></label>`).join("")}</div><p class="cp-vd-note">${esc(t(state.locale,"Stored time is hourly; these values convert display and entry units when calendar-specific time periods are enabled.", "زمان در پایگاه داده بر حسب ساعت ذخیره می‌شود؛ این مقادیر هنگام فعال بودن دوره‌های زمانی تقویم، واحدهای ورودی و نمایشی را تبدیل می‌کنند."))}</p></section>
        </div>
        <p class="cp-vd-note">${esc(t(state.locale,"Calendar inheritance, work/nonwork periods, exceptions, used-by assignments and hours-per-period conversion are preview-only. Editing a base calendar can affect linked project/resource calendars and manual future-period assignment values.", "ارث‌بری تقویم، بازه‌های کاری و غیرکاری، استثناها، تخصیص‌های استفاده‌کننده و تبدیل ساعات دوره‌ها فقط پیش‌نمایش هستند. ویرایش تقویم پایه می‌تواند تقویم‌های پروژه و منابعِ پیوندخورده و مقادیر دستی دوره‌های آینده را تحت تأثیر قرار دهد."))}</p>
      </section>`;
    case "schedule":
      return `<div class="cp-vd-schedule-options"><div class="cp-vd-form"><label>${esc(t(state.locale, "Data date", "تاریخ داده"))}<input type="date" value="2026-12-03"></label><label>${esc(t(state.locale, "Schedule mode", "حالت زمان‌بندی"))}<select><option>Forward and backward</option><option>Forward only</option></select></label><label>${esc(t(state.locale, "Out-of-sequence progress", "پیشرفت خارج از توالی"))}<select><option>Retained Logic</option><option>Progress Override</option><option>Actual Dates</option></select></label><label>${esc(t(state.locale, "Default calendar", "تقویم پیش‌فرض"))}<select><option>Project Default</option><option>Activity Calendar</option><option>24 Hour</option></select></label></div><fieldset><legend>${esc(t(state.locale, "Scheduling options", "گزینه‌های زمان‌بندی"))}</legend><label><input type="checkbox" checked> Recalculate dates for not-started activities</label><label><input type="checkbox" checked> Use expected finish dates</label><label><input type="checkbox"> Ignore relationships to and from other projects</label><label><input type="checkbox" checked> Calculate multiple float paths</label><label><input type="checkbox"> Make open-ended activities critical</label><label><input type="checkbox" checked> Log scheduling messages</label></fieldset><div class="cp-vd-hintbox"> ${esc(t(state.locale, "Schedule execution is disabled in this visual preview. These controls do not alter CPM dates or project data.", "اجرای زمان‌بندی در این پیش‌نمایش غیرفعال است. این گزینه‌ها تاریخ‌های CPM یا داده پروژه را تغییر نمی‌دهند."))}</div></div>`;
    case "level":
      return `<div class="cp-vd-schedule-options"><div class="cp-vd-form"><label>${esc(t(state.locale, "Level", "تسطیح"))}<select><option>All resources</option><option>Selected resources</option></select></label><label>${esc(t(state.locale, "Priority sequence", "توالی اولویت"))}<select><option>Total Float → Activity Priority</option><option>Activity Priority → Total Float</option><option>Early Start → Activity ID</option></select></label><label>${esc(t(state.locale, "Maximum percent to exceed availability", "حداکثر درصد عبور از ظرفیت"))}<input type="number" value="0" min="0" max="100"></label><label>${esc(t(state.locale, "Preserve minimum float", "حفظ حداقل شناوری"))}<input type="number" value="0" min="0"></label></div><fieldset><legend>${esc(t(state.locale, "Leveling options", "گزینه‌های تسطیح"))}</legend><label><input type="checkbox" checked> Level only within available total float</label><label><input type="checkbox" checked> Consider resource calendars</label><label><input type="checkbox"> Preserve scheduled early and late dates</label><label><input type="checkbox" checked> Recalculate assignments after leveling</label><label><input type="checkbox"> Allow splitting activities</label></fieldset><p class="cp-vd-note">${esc(t(state.locale, "Visual preview only — no resource leveling is run and no activity dates are changed.", "صرفاً پیش‌نمایش بصری — تسطیح منابع اجرا نمی‌شود و تاریخ فعالیت‌ها تغییر نمی‌کند."))}</p></div>`;
    case "baselines":
      return `<div class="cp-vd-schedule-options"><div class="cp-vd-form"><label>${esc(t(state.locale, "Primary baseline", "خط مبنای اصلی"))}<select><option>BL-01 — Approved baseline</option><option>BL-02 — Recovery baseline</option><option>Project baseline</option></select></label><label>${esc(t(state.locale, "Secondary baseline", "خط مبنای ثانویه"))}<select><option>None</option><option>BL-01 — Approved baseline</option><option>BL-02 — Recovery baseline</option></select></label><label>${esc(t(state.locale, "Tertiary baseline", "خط مبنای سوم"))}<select><option>None</option><option>BL-01 — Approved baseline</option><option>BL-02 — Recovery baseline</option></select></label><label>${esc(t(state.locale, "Baseline source", "منبع خط مبنا"))}<select><option>Current project</option><option>Existing baseline</option></select></label></div>${rows(["Baseline", "Type", "Created", "Activities", "Status"], `<tr><td>BL-01</td><td>Original</td><td>03-Nov-2026</td><td>20</td><td>Approved</td></tr><tr><td>BL-02</td><td>Current</td><td>—</td><td>—</td><td>Not assigned</td></tr>`)}<div class="cp-vd-hintbox">Create, update, assign, restore or compare baselines. ${esc(t(state.locale, "Baseline actions are illustrative and do not save a project snapshot.", "فرمان‌های خط مبنا نمایشی هستند و تصویر پروژه ذخیره نمی‌کنند."))}</div></div>`;
    case "find":
      return `<div class="cp-vd-form"><label>${esc(t(state.locale, "Find activity", "یافتن فعالیت"))}<input name="filter" value="${esc(state.filter)}"></label><div class="cp-vd-radios"><label><input type="radio" checked> ${esc(t(state.locale, "Activity ID", "شناسه"))}</label><label><input type="radio"> ${esc(t(state.locale, "Activity name", "نام"))}</label></div></div>`;
    case "find-replace":
      return `<div class="cp-vd-form"><label>${esc(t(state.locale, "Find", "یافتن"))}<input></label><label>${esc(t(state.locale, "Replace with", "جایگزینی با"))}<input></label><label class="cp-vd-check"><input type="checkbox"> ${esc(t(state.locale, "Match case", "تطابق حروف"))}</label></div>`;
    case "renumber":
      return `<div class="cp-vd-form"><label>${esc(t(state.locale, "Prefix", "پیشوند"))}<input value="A"></label><label>${esc(t(state.locale, "Start number", "شمارهٔ شروع"))}<input value="1000"></label><label>${esc(t(state.locale, "Increment", "گام"))}<input value="10"></label></div>`;
    case "resource-shifts":
      return `<section class="cp-vd-resource-details"><header class="cp-vd-assignment-context"><strong>${esc(t(state.locale,"Resource shifts","شیفت‌های منابع"))}</strong><span>${esc(t(state.locale,"Resource: Mobile crane 50t","منبع: جرثقیل متحرک ۵۰ تن"))}</span></header>
        <div class="cp-vd-form">
          <label>${esc(t(state.locale,"Shift name","نام شیفت"))}<input value="Day shift" disabled></label><label>${esc(t(state.locale,"Shift calendar","تقویم شیفت"))}<select disabled><option>Standard 5-Day</option><option>Six-Day Site</option></select></label>
          <label>${esc(t(state.locale,"Effective start","شروع اعتبار"))}<input type="date" value="2026-01-01" disabled></label><label>${esc(t(state.locale,"Effective finish","پایان اعتبار"))}<input type="date" disabled></label>
          <label>${esc(t(state.locale,"Shift pattern","الگوی شیفت"))}<select disabled><option>Fixed weekly pattern</option><option>Rotating pattern</option><option>Calendar-based</option></select></label><label>${esc(t(state.locale,"Hours per shift","ساعت هر شیفت"))}<input type="number" value="8" disabled></label>
        </div>
        <section><h3>${esc(t(state.locale,"Daily shift periods","بازه‌های روزانه شیفت"))}</h3><table class="cp-vd-mini"><thead><tr><th>${esc(t(state.locale,"Day","روز"))}</th><th>${esc(t(state.locale,"Start","شروع"))}</th><th>${esc(t(state.locale,"Finish","پایان"))}</th><th>${esc(t(state.locale,"Break","وقفه"))}</th><th>${esc(t(state.locale,"Net work hours","ساعات خالص کار"))}</th></tr></thead><tbody>${["Saturday","Sunday","Monday","Tuesday","Wednesday","Thursday","Friday"].map((day,index)=>`<tr><td>${esc(t(state.locale,day,["شنبه","یکشنبه","دوشنبه","سه‌شنبه","چهارشنبه","پنجشنبه","جمعه"][index]))}</td><td>08:00</td><td>${index===6?"—":"17:00"}</td><td>${index===6?"—":"12:00–13:00"}</td><td>${index===6?"0":"8.0"}</td></tr>`).join("")}</tbody></table></section>
        <div class="cp-vd-form"><label class="cp-vd-check"><input type="checkbox" checked disabled> ${esc(t(state.locale,"Use resource calendar for shift availability","استفاده از تقویم منبع برای ظرفیت شیفت"))}</label><label class="cp-vd-check"><input type="checkbox" disabled> ${esc(t(state.locale,"Allow overtime","اجازه اضافه‌کاری"))}</label></div>
        <p class="cp-vd-note">${esc(t(state.locale,"Shift definitions are separate from the base calendar. This read-only shift sample does not reserve resource capacity or change assignment units.", "تعریف شیفت از تقویم پایه مستقل است. این نمونه فقط‌خواندنی ظرفیت منبع را رزرو نمی‌کند و واحد تخصیص را تغییر نمی‌دهد."))}</p>
      </section>`;
    case "resource-details": {
      const tabs: Array<[string,string,string]> = [["General","General","عمومی"],["Codes","Codes","کدها"],["Details","Details","جزئیات"],["Units & Prices","Units & Prices","واحدها و قیمت‌ها"],["Roles","Roles","نقش‌ها"],["Notes","Notes","یادداشت‌ها"],["Custom fields","Custom Fields","فیلدهای سفارشی"]];
      return `<section class="cp-vd-resource-details"><header class="cp-vd-assignment-context"><strong>${esc(t(state.locale,"Resource Details","جزئیات منبع"))}</strong><span><bdi dir="ltr">R-100</bdi> · PM Office</span></header>
        <nav class="cp-vd-project-tabs" role="tablist" aria-label="${esc(t(state.locale,"Resource detail sections","بخش‌های جزئیات منبع"))}">${tabs.map(([id,en,fa],index)=>`<button type="button" role="tab" aria-selected="${index===0}" class="${index===0?"is-active":""}" disabled>${esc(t(state.locale,en,fa))}</button>`).join("")}</nav>
        <div class="cp-vd-resource-detail-body">
          <section><h3>${esc(t(state.locale,"General","عمومی"))}</h3><div class="cp-vd-form">
            <label>${esc(t(state.locale,"Resource ID","شناسه منبع"))}<input value="R-100" readonly></label><label>${esc(t(state.locale,"Resource name","نام منبع"))}<input value="PM Office" disabled></label>
            <label>${esc(t(state.locale,"Resource type","نوع منبع"))}<select disabled><option>Labor</option><option>Nonlabor</option><option>Material</option></select></label><label>${esc(t(state.locale,"Employee ID","شناسه کارمند"))}<input value="—" disabled></label>
            <label>${esc(t(state.locale,"Title","عنوان"))}<input value="Project Management Office" disabled></label><label>${esc(t(state.locale,"E-mail address","رایانامه"))}<input value="—" disabled></label>
            <label>${esc(t(state.locale,"Office phone","تلفن دفتر"))}<input value="—" disabled></label><label class="cp-vd-check"><input type="checkbox" checked disabled> ${esc(t(state.locale,"Active resource — available for assignment","منبع فعال — قابل تخصیص"))}</label>
          </div></section>
          <section><h3>${esc(t(state.locale,"Details","جزئیات"))}</h3><div class="cp-vd-form">
            <label>${esc(t(state.locale,"Unit of measure","واحد سنجش"))}<select disabled><option>Hour</option><option>Day</option><option>m³</option></select></label><label>${esc(t(state.locale,"Default units/time","واحد پیش‌فرض / زمان"))}<input value="1.00 h/d" disabled></label>
            <label>${esc(t(state.locale,"Maximum units/time","حداکثر واحد / زمان"))}<input value="2.00 h/d" disabled></label><label>${esc(t(state.locale,"Primary role","نقش اصلی"))}<select disabled><option>Project Manager</option><option>Planner</option></select></label>
            <label>${esc(t(state.locale,"Resource calendar","تقویم منبع"))}<select disabled><option>Standard 5-Day</option></select></label><label>${esc(t(state.locale,"Shift","شیفت"))}<select disabled><option>Day shift</option></select></label>
          </div></section>
          <section><h3>${esc(t(state.locale,"Units & Prices","واحدها و قیمت‌ها"))}</h3><div class="cp-vd-tablewrap"><table class="cp-vd-mini"><thead><tr><th>${esc(t(state.locale,"Effective date","تاریخ اثر"))}</th><th>${esc(t(state.locale,"Price / unit","قیمت / واحد"))}</th><th>${esc(t(state.locale,"Currency","ارز"))}</th><th>${esc(t(state.locale,"Price factor","ضریب قیمت"))}</th></tr></thead><tbody><tr><td>01-Jan-2026</td><td>55.40</td><td>USD</td><td>1.00</td></tr><tr><td>01-Jan-2027</td><td>58.20</td><td>USD</td><td>1.00</td></tr></tbody></table></div></section>
          <section><h3>${esc(t(state.locale,"Roles and codes","نقش‌ها و کدها"))}</h3><div class="cp-vd-form"><label>${esc(t(state.locale,"Assigned roles","نقش‌های تخصیص‌یافته"))}<input value="Project Manager; Planner" disabled></label><label>${esc(t(state.locale,"Resource codes","کدهای منبع"))}<input value="Discipline: Management" disabled></label><label>${esc(t(state.locale,"Notes","یادداشت‌ها"))}<textarea rows="2" disabled>Resource record for visual review.</textarea></label></div></section>
        </div>
        <p class="cp-vd-note">${esc(t(state.locale,"The desktop resource detail inventory is General, Codes, Details, Units & Prices, Roles, Notes and Custom Fields. The Progress Reporter tab is excluded because it belongs to the connected server environment. This sample resource is read-only.", "فهرست جزئیات منبع دسکتاپ شامل عمومی، کدها، جزئیات، واحدها و قیمت‌ها، نقش‌ها، یادداشت‌ها و فیلدهای سفارشی است. زبانه گزارش‌دهنده پیشرفت به‌دلیل وابستگی به محیط سرور حذف شده است. این منبع نمونه فقط‌خواندنی است."))}</p>
      </section>`;
    }
    case "assign-resources": {
      const activity = ACTIVITIES.find((item) => item.id === state.activityId);
      const availableResources = RESOURCES.map((resource) => ({ ...resource, rate: resource.units > 0 ? Math.round(resource.cost / resource.units * 100) / 100 : 0 }));
      return `<section class="cp-vd-assignment-dialog">
        <div class="cp-vd-assignment-context"><strong>${esc(t(state.locale, "Assign resources to activity", "تخصیص منابع به فعالیت"))}</strong><span><bdi dir="ltr">${esc(state.activityId)}</bdi> · ${esc(activity?.name ?? "—")}</span></div>
        <div class="cp-vd-assignment-filter"><label>${esc(t(state.locale, "Find resources", "جست‌وجوی منابع"))}<input type="search" placeholder="${esc(t(state.locale, "Search by ID or name…", "جست‌وجو با شناسه یا نام…"))}" disabled></label><label>${esc(t(state.locale, "Resource type", "نوع منبع"))}<select disabled><option>All types</option><option>Labor</option><option>Equipment</option><option>Material</option></select></label></div>
        <div class="cp-vd-assignment-grid">
          <section><h3>${esc(t(state.locale, "Available resources", "منابع موجود"))}</h3><div class="cp-vd-assignment-table"><table class="cp-vd-mini"><thead><tr><th></th><th>ID</th><th>${esc(t(state.locale, "Resource", "منبع"))}</th><th>${esc(t(state.locale, "Type", "نوع"))}</th><th>${esc(t(state.locale, "Budget units", "واحد بودجه"))}</th><th>${esc(t(state.locale, "Budget cost", "هزینه بودجه"))}</th><th>${esc(t(state.locale, "Rate / unit", "نرخ / واحد"))}</th></tr></thead><tbody>
            ${availableResources.map((resource)=>`<tr><td><input type="checkbox" disabled aria-label="Select ${esc(resource.name)}"></td><td><bdi dir="ltr">${esc(resource.id)}</bdi></td><td>${esc(resource.name)}</td><td>${esc(t(state.locale,resource.type,resource.type==="Labor"?"نیروی انسانی":resource.type==="Material"?"مصالح":"تجهیزات"))}</td><td>${resource.units.toLocaleString("en-US")}</td><td>${resource.cost.toLocaleString("en-US")}</td><td>${resource.rate.toLocaleString("en-US")}</td></tr>`).join("")}
          </tbody></table></div><p class="cp-vd-note">${esc(t(state.locale, "Resource catalogue figures are demonstration data; no availability reservation is implied.", "مقادیر فهرست منابع داده نمایشی هستند و به معنی رزرو ظرفیت نیستند."))}</p></section>
          <aside><h3>${esc(t(state.locale, "Assignment details", "جزئیات تخصیص"))}</h3><div class="cp-vd-form">
            <label>${esc(t(state.locale, "Budgeted units", "واحد بودجه"))}<input type="number" min="0" step="0.01" value="40" disabled></label>
            <label>${esc(t(state.locale, "Units / time", "واحد / زمان"))}<input type="number" min="0" step="0.01" value="1" disabled></label>
            <label>${esc(t(state.locale, "Rate type", "نوع نرخ"))}<select disabled><option>Price per Unit</option><option>Price per Time</option></select></label>
            <label>${esc(t(state.locale, "Rate source", "منبع نرخ"))}<select disabled><option>Resource</option><option>Role</option><option>Override</option></select></label>
            <label>${esc(t(state.locale, "Price / unit override", "قیمت / واحد جایگزین"))}<input type="number" min="0" step="0.01" disabled></label>
            <label>${esc(t(state.locale, "Overtime factor", "ضریب اضافه‌کاری"))}<input type="number" min="0" step="0.01" value="1" disabled></label>
            <label class="cp-vd-assignment-check"><input type="checkbox" disabled> ${esc(t(state.locale, "Primary resource", "منبع اصلی"))}</label>
            <label>${esc(t(state.locale, "Resource calendar", "تقویم منبع"))}<select disabled><option>Use resource calendar</option><option>Use activity calendar</option></select></label>
            <label>${esc(t(state.locale, "Assignment start", "شروع تخصیص"))}<input type="date" value="${esc(activity?.start ?? "")}" disabled></label>
            <label>${esc(t(state.locale, "Assignment finish", "پایان تخصیص"))}<input type="date" value="${esc(activity?.finish ?? "")}" disabled></label>
            <label>${esc(t(state.locale, "Resource curve", "منحنی منبع"))}<select disabled><option>Linear</option><option>Front Loaded</option><option>Back Loaded</option><option>Bell</option><option>Manual</option></select></label>
            <label>${esc(t(state.locale, "Cost account", "حساب هزینه"))}<select disabled><option>Not assigned</option></select></label>
          </div><div class="cp-vd-assignment-actions"><button type="button" disabled>${esc(t(state.locale, "Assign", "تخصیص"))}</button><button type="button" disabled>${esc(t(state.locale, "Remove", "حذف"))}</button></div></aside>
        </div><p class="cp-vd-note">${esc(t(state.locale, "Visual preview only — assignment, availability, cost recalculation and project updates are not connected.", "صرفاً پیش‌نمایش بصری — تخصیص، ظرفیت، محاسبه مجدد هزینه و به‌روزرسانی پروژه متصل نیست."))}</p>
      </section>`;
    }
    case "assign-resources-by-role":
      return `<section class="cp-vd-assignment-dialog"><div class="cp-vd-assignment-context"><strong>${esc(t(state.locale, "Assign resources by role", "تخصیص منابع بر اساس نقش"))}</strong><span><bdi dir="ltr">${esc(state.activityId)}</bdi></span></div>
        <div class="cp-vd-form"><label>${esc(t(state.locale, "Required role", "نقش موردنیاز"))}<select disabled><option>Site engineer</option><option>Planner</option><option>Cost engineer</option><option>Construction manager</option></select></label><label>${esc(t(state.locale, "Proficiency", "سطح مهارت"))}<select disabled><option>Any proficiency</option><option>Intermediate or higher</option><option>Advanced or higher</option><option>Expert</option></select></label></div>
        <section><h3>${esc(t(state.locale, "Eligible resources", "منابع واجد شرایط"))}</h3><div class="cp-vd-assignment-table"><table class="cp-vd-mini"><thead><tr><th></th><th>ID</th><th>${esc(t(state.locale, "Resource", "منبع"))}</th><th>${esc(t(state.locale, "Type", "نوع"))}</th><th>${esc(t(state.locale, "Units", "واحد"))}</th></tr></thead><tbody>${RESOURCES.map((resource)=>`<tr><td><input type="checkbox" disabled aria-label="Select ${esc(resource.name)}"></td><td><bdi dir="ltr">${esc(resource.id)}</bdi></td><td>${esc(resource.name)}</td><td>${esc(resource.type)}</td><td>${resource.units.toLocaleString("en-US")}</td></tr>`).join("")}</tbody></table></div></section>
        <div class="cp-vd-form"><label>${esc(t(state.locale, "Assignment units", "واحد تخصیص"))}<input type="number" min="0" step="0.01" disabled></label><label>${esc(t(state.locale, "Rate source", "منبع نرخ"))}<select disabled><option>Prompt when resource and role share an assignment</option><option>Resource rate</option><option>Role rate</option><option>Override rate</option></select></label></div>
        <p class="cp-vd-note">${esc(t(state.locale, "The role remains the requirement; the selected resource is the staffing choice. When both exist on one assignment, rate source and price/unit rules must be explicit.", "نقش به‌عنوان نیاز باقی می‌ماند و منبع انتخاب‌شده نیروی تأمین‌کننده است. هنگام وجود هر دو در یک تخصیص، منبع نرخ و قواعد قیمت هر واحد باید صریح باشد."))}</p>
      </section>`;
    case "assign-roles":
      return `<section class="cp-vd-assignment-dialog"><div class="cp-vd-assignment-context"><strong>${esc(t(state.locale, "Assign roles to activity", "تخصیص نقش به فعالیت"))}</strong><span><bdi dir="ltr">${esc(state.activityId)}</bdi></span></div><div class="cp-vd-form">
        <label>${esc(t(state.locale, "Role", "نقش"))}<select disabled><option>Site engineer</option><option>Planner</option><option>Cost engineer</option><option>Construction manager</option><option>Commissioning engineer</option></select></label>
        <label>${esc(t(state.locale, "Role units", "واحد نقش"))}<input type="number" min="0" step="0.01" value="1" disabled></label>
        <label>${esc(t(state.locale, "Max units / time", "حداکثر واحد / زمان"))}<input type="number" min="0" step="0.01" value="1" disabled></label>
        <label>${esc(t(state.locale, "Proficiency", "سطح مهارت"))}<select disabled><option>Not specified</option><option>Entry</option><option>Intermediate</option><option>Advanced</option><option>Expert</option></select></label>
        <label>${esc(t(state.locale, "Start", "شروع"))}<input type="date" disabled></label><label>${esc(t(state.locale, "Finish", "پایان"))}<input type="date" disabled></label>
        <label>${esc(t(state.locale, "Candidate resource", "منبع نامزد"))}<select disabled><option>Unassigned</option>${RESOURCES.map((resource)=>`<option>${esc(resource.name)}</option>`).join("")}</select></label>
      </div><p class="cp-vd-note">${esc(t(state.locale, "Role requirements and resource assignments are separate records; assigning a role does not silently assign a resource.", "نیاز نقش و تخصیص منبع دو رکورد مستقل هستند؛ تخصیص نقش نباید به‌صورت پنهان منبعی را تخصیص دهد."))}</p></section>`;
    case "assign-predecessors":
      return `<div class="cp-vd-form"><label>${esc(t(state.locale, "Predecessor activity", "فعالیت پیش‌نیاز"))}<select>${ACTIVITIES.map((item) => `<option value="${esc(item.id)}">${esc(item.id)} — ${esc(item.name)}</option>`).join("")}</select></label><label>${esc(t(state.locale, "Relationship type", "نوع رابطه"))}<select><option>FS — Finish to Start</option><option>SS — Start to Start</option><option>FF — Finish to Finish</option><option>SF — Start to Finish</option></select></label><label>${esc(t(state.locale, "Lag / Lead", "تأخیر / پیش‌افتادگی"))}<input type="number" value="0"></label><label>${esc(t(state.locale, "Lag calendar", "تقویم تأخیر"))}<select><option>Predecessor calendar</option><option>Successor calendar</option><option>Project default calendar</option><option>24 Hour</option></select></label><p class="cp-vd-note">FS, SS, FF and SF relationships retain their signed lag and selected lag calendar.</p></div>`;
    case "assign-successors":
      return `<div class="cp-vd-form"><label>${esc(t(state.locale, "Successor activity", "فعالیت جانشین"))}<select>${ACTIVITIES.map((item) => `<option value="${esc(item.id)}">${esc(item.id)} — ${esc(item.name)}</option>`).join("")}</select></label><label>${esc(t(state.locale, "Relationship type", "نوع رابطه"))}<select><option>FS — Finish to Start</option><option>SS — Start to Start</option><option>FF — Finish to Finish</option><option>SF — Start to Finish</option></select></label><label>${esc(t(state.locale, "Lag / Lead", "تأخیر / پیش‌افتادگی"))}<input type="number" value="0"></label><label>${esc(t(state.locale, "Lag calendar", "تقویم تأخیر"))}<select><option>Predecessor calendar</option><option>Successor calendar</option><option>Project default calendar</option><option>24 Hour</option></select></label></div>`;
    case "add-activity":
      return `<div class="cp-vd-schedule-options"><div class="cp-vd-form"><label>${esc(t(state.locale, "Activity ID", "شناسه فعالیت"))}<input value="A1160"></label><label>${esc(t(state.locale, "Activity name", "نام فعالیت"))}<input placeholder="New activity"></label><label>${esc(t(state.locale, "WBS", "ساختار شکست"))}<select>${WBS_TREE.map((item) => `<option>${esc(item.code)} — ${esc(item.name)}</option>`).join("")}</select></label><label>${esc(t(state.locale, "Activity type", "نوع فعالیت"))}<select><option>Task Dependent</option><option>Resource Dependent</option><option>Level of Effort</option><option>Start Milestone</option><option>Finish Milestone</option><option>WBS Summary</option></select></label><label>${esc(t(state.locale, "Duration type", "نوع مدت"))}<select><option>Fixed Duration & Units</option><option>Fixed Units / Time</option><option>Fixed Units</option></select></label><label>${esc(t(state.locale, "Original duration", "مدت اولیه"))}<input type="number" min="0" step="0.5" value="5"></label><label>${esc(t(state.locale, "Calendar", "تقویم"))}<select><option>5-Day Workweek</option><option>6-Day Workweek</option><option>24 Hour</option><option>Activity-specific calendar</option></select></label><label>${esc(t(state.locale, "Constraint", "محدودیت"))}<select><option>As Soon As Possible</option><option>Start On</option><option>Start On or After</option><option>Finish On</option><option>Finish On or Before</option></select></label></div><p class="cp-vd-note">${esc(t(state.locale, "Visual preview only — no activity is added and no schedule calculation is performed.", "صرفاً پیش‌نمایش بصری — فعالیتی افزوده نمی‌شود و محاسبه زمان‌بندی انجام نمی‌شود."))}</p></div>`;
    case "budgeting":
      return `<section class="cp-vd-financial-dialog"><header class="cp-vd-assignment-context"><strong>${esc(t(state.locale,"Budget and Spending Plan","بودجه و برنامه هزینه"))}</strong><span>CUBI-DEMO-001 · EUR</span></header>
      <div class="cp-vd-resource-kpis"><div><span>Approved budget</span><strong>€1,225,000</strong></div><div><span>Budget changes</span><strong>+€25,000</strong></div><div><span>Current budget</span><strong>€1,250,000</strong></div><div><span>Spending plan</span><strong>€1,180,000</strong></div></div>
      <div class="cp-vd-financial-grid"><section><h3>Budget Log and Changes</h3><div class="cp-vd-form"><label>Change ID<input value="BC-004" disabled></label><label>Change date<input type="date" value="2026-11-01" disabled></label><label>Change amount<input value="25000" disabled></label><label>Reason<input value="Approved scope adjustment" disabled></label><label>Approval status<select disabled><option>Approved</option><option>Pending</option><option>Rejected</option></select></label></div>${rows(["Change ID","Date","Amount","Reason","Status"],'<tr><td>BC-003</td><td>15-Oct-2026</td><td>€18,000</td><td>Approved variation</td><td>Approved</td></tr><tr><td>BC-004</td><td>01-Nov-2026</td><td>€25,000</td><td>Scope adjustment</td><td>Approved</td></tr>')}</section>
      <section><h3>Funding Sources and Assignments</h3>${rows(["Source","Type","Committed","Assigned","Available"],'<tr><td>Owner funding</td><td>Equity</td><td>€800,000</td><td>€760,000</td><td>€40,000</td></tr><tr><td>Bank facility</td><td>Debt</td><td>€450,000</td><td>€390,000</td><td>€60,000</td></tr>')}<div class="cp-vd-form"><label>Funding source<select disabled><option>Owner funding</option></select></label><label>Assigned amount<input value="760000" disabled></label></div></section>
      <section class="cp-vd-financial-wide"><h3>Monthly Spending Plan</h3>${rows(["Financial period","Budget","Spending plan","Actual","Variance"],'<tr><td>Nov-2026</td><td>€110,000</td><td>€105,000</td><td>€92,000</td><td>€13,000</td></tr><tr><td>Dec-2026</td><td>€125,000</td><td>€120,000</td><td>—</td><td>—</td></tr><tr><td>Jan-2027</td><td>€140,000</td><td>€135,000</td><td>—</td><td>—</td></tr>')}<p class="cp-vd-note">Financial periods follow the financial-period calendar, not the activity work calendar.</p></section></div>
      <p class="cp-vd-note">Visual sample only. Budget changes, funding assignments and spending-plan values are not saved or posted.</p></section>`;
    case "earned-value":
      return `<section class="cp-vd-financial-dialog"><header class="cp-vd-assignment-context"><strong>Earned Value Analysis</strong><span>Data date: 03-Dec-2026 · Baseline: BL-01</span></header>
      <div class="cp-vd-resource-kpis"><div><span>Planned Value (PV)</span><strong>€640,000</strong></div><div><span>Earned Value (EV)</span><strong>€590,000</strong></div><div><span>Actual Cost (AC)</span><strong>€615,000</strong></div><div><span>Budget at Completion</span><strong>€1,225,000</strong></div></div>
      <section><h3>Earned Value Calculation Settings</h3><div class="cp-vd-form"><label>Earned value baseline<select disabled><option>BL-01 — Approved baseline</option><option>Project baseline</option></select></label><label>Technique for activities with no resource assignments<select disabled><option>Activity percent complete</option><option>0 / 100</option><option>50 / 50</option></select></label><label>Technique for WBS<select disabled><option>Activity percent complete</option><option>WBS milestones</option><option>0 / 100</option><option>50 / 50</option></select></label><label>WBS earned value method<select disabled><option>Activity percent complete</option><option>WBS weighted milestones</option></select></label></div></section>
      <section><h3>Performance Indices and Variances</h3>${rows(["Metric","Definition","Sample value","Interpretation"],'<tr><td>Schedule Variance (SV)</td><td>EV − PV</td><td>−€50,000</td><td>Behind planned value</td></tr><tr><td>Cost Variance (CV)</td><td>EV − AC</td><td>−€25,000</td><td>Over budget for work earned</td></tr><tr><td>SPI</td><td>EV / PV</td><td>0.92</td><td>Below 1.00</td></tr><tr><td>CPI</td><td>EV / AC</td><td>0.96</td><td>Below 1.00</td></tr>')}</section>
      <p class="cp-vd-note">Illustrative figures only. EV uses the assigned baseline and configured WBS/activity technique; no index is calculated in this preview.</p></section>`;
    case "update-progress":
      return `<section class="cp-vd-financial-dialog"><header class="cp-vd-assignment-context"><strong>${esc(t(state.locale,"Update Activity Progress","به‌روزرسانی پیشرفت فعالیت"))}</strong><span><bdi dir="ltr">A1040</bdi> · Concrete foundations</span></header><div class="cp-vd-form">
      <label>${esc(t(state.locale,"Data date","تاریخ داده"))}<input type="date" value="2026-12-03" disabled></label><label>${esc(t(state.locale,"Percent complete type","نوع درصد پیشرفت"))}<select disabled><option>Physical</option><option>Duration</option><option>Units</option></select></label><label>${esc(t(state.locale,"Physical % complete","درصد پیشرفت فیزیکی"))}<input type="number" min="0" max="100" value="55" disabled></label><label>${esc(t(state.locale,"Actual start","شروع واقعی"))}<input type="date" value="2026-10-12" disabled></label><label>${esc(t(state.locale,"Actual finish","پایان واقعی"))}<input type="date" disabled></label><label>${esc(t(state.locale,"Remaining duration","مدت باقی‌مانده"))}<input type="number" value="18" min="0" disabled></label><label>${esc(t(state.locale,"Actual units","واحد واقعی"))}<input value="420" disabled></label><label>${esc(t(state.locale,"Remaining units","واحد باقی‌مانده"))}<input value="340" disabled></label><label>${esc(t(state.locale,"Actual cost","هزینه واقعی"))}<input value="€92,000" disabled></label><label>${esc(t(state.locale,"Remaining cost","هزینه باقی‌مانده"))}<input value="€68,000" disabled></label></div>
      <fieldset><legend>${esc(t(state.locale,"Progress actions","عملیات پیشرفت"))}</legend><label><input type="checkbox" disabled> ${esc(t(state.locale,"Suspend progress","تعلیق پیشرفت"))}</label><label><input type="checkbox" disabled> ${esc(t(state.locale,"Resume progress","ازسرگیری پیشرفت"))}</label><label><input type="checkbox" checked disabled> ${esc(t(state.locale,"Preserve actual dates","حفظ تاریخ‌های واقعی"))}</label></fieldset>
      <p class="cp-vd-note">${esc(t(state.locale,"Actual dates, remaining duration, percent-complete type and out-of-sequence progress policy must remain consistent. This preview does not update or schedule the project.","تاریخ‌های واقعی، مدت باقی‌مانده، نوع درصد پیشرفت و سیاست پیشرفت خارج از توالی باید سازگار بمانند. این پیش‌نمایش پروژه را به‌روزرسانی یا زمان‌بندی نمی‌کند."))}</p></section>`;
    case "apply-actuals":
      return `<section class="cp-vd-financial-dialog"><h3>${esc(t(state.locale,"Apply Actuals","اعمال واقعیات"))}</h3><div class="cp-vd-form"><label>${esc(t(state.locale,"Apply through data date","اعمال تا تاریخ داده"))}<input type="date" value="2026-12-03" disabled></label><label>${esc(t(state.locale,"Project scope","دامنه پروژه"))}<select disabled><option>Current project</option><option>Selected activities</option></select></label><label>${esc(t(state.locale,"Actuals source","منبع واقعیات"))}<select disabled><option>Activity and assignment progress</option><option>Approved period actuals</option></select></label></div><fieldset><legend>${esc(t(state.locale,"Apply options","گزینه‌های اعمال"))}</legend><label><input type="checkbox" checked disabled> ${esc(t(state.locale,"Update actual start and finish dates","به‌روزرسانی تاریخ شروع و پایان واقعی"))}</label><label><input type="checkbox" checked disabled> ${esc(t(state.locale,"Recalculate remaining duration","محاسبه مجدد مدت باقی‌مانده"))}</label><label><input type="checkbox" disabled> ${esc(t(state.locale,"Apply actual units and costs","اعمال واحدها و هزینه‌های واقعی"))}</label><label><input type="checkbox" checked disabled> ${esc(t(state.locale,"Preserve existing actual dates","حفظ تاریخ‌های واقعی موجود"))}</label></fieldset><p class="cp-vd-note">${esc(t(state.locale,"Controlled project-wide operation. This preview performs no updates and does not run the scheduler.","عملیاتی کنترل‌شده در سطح پروژه است. این پیش‌نمایش هیچ به‌روزرسانی انجام نمی‌دهد و زمان‌بند را اجرا نمی‌کند."))}</p></section>`;
    case "store-period-performance":
      return `<section class="cp-vd-financial-dialog"><h3>${esc(t(state.locale,"Store Period Performance","ثبت عملکرد دوره"))}</h3><div class="cp-vd-form"><label>${esc(t(state.locale,"Financial period","دوره مالی"))}<select disabled><option>Nov-2026</option><option>Oct-2026</option><option>Dec-2026</option></select></label><label>${esc(t(state.locale,"Project","پروژه"))}<input value="CUBI-DEMO-001" disabled></label><label>${esc(t(state.locale,"Posting status","وضعیت ثبت"))}<input value="Not posted" disabled></label></div>${rows(["Assignment","Actual this period units","Actual to date units","Actual this period cost","Actual to date cost"],'<tr><td>Concrete crew</td><td>320</td><td>1,840</td><td>€18,400</td><td>€105,800</td></tr><tr><td>Mobile crane 50t</td><td>24</td><td>116</td><td>€3,600</td><td>€17,400</td></tr>')}<p class="cp-vd-note">${esc(t(state.locale,"Posting locks selected period history. Past-period edits require explicit permission and an audit trail. No period data is posted here.","ثبت، تاریخچه دوره انتخاب‌شده را قفل می‌کند. ویرایش دوره‌های گذشته به مجوز صریح و ردپای ممیزی نیاز دارد. در اینجا داده‌ای ثبت نمی‌شود."))}</p></section>`;
    case "expense-details":
      return `<section class="cp-vd-financial-dialog"><h3>Expense Details</h3><div class="cp-vd-form"><label>Expense item<input value="Temporary site power" disabled></label><label>Activity<input value="A1040 · Concrete foundations" disabled></label><label>Expense category<select disabled><option>Utilities</option><option>Equipment rental</option><option>Subcontract</option></select></label><label>Accrual type<select disabled><option>Uniform / prorated</option><option>Start of activity</option><option>End of activity</option></select></label><label>Cost account<select disabled><option>CA-300 Construction</option></select></label><label>Vendor<input value="Utility provider" disabled></label><label>Budgeted expense cost<input value="€12,500" disabled></label><label>Actual expense cost<input value="€7,800" disabled></label><label>Remaining expense cost<input value="€4,700" disabled></label></div><p class="cp-vd-note">Expenses are activity-linked cost items, distinct from resource assignments. Accrual type controls when expense is recognized.</p></section>`;
    case "cost-accounts":
      return `<section class="cp-vd-financial-dialog"><h3>Cost Account Dictionary</h3>${rows(["Account ID","Account name","Parent account","Level","Status"],'<tr><td>CA-100</td><td>Engineering</td><td>Project Costs</td><td>2</td><td>Active</td></tr><tr><td>CA-200</td><td>Procurement</td><td>Project Costs</td><td>2</td><td>Active</td></tr><tr><td>CA-300</td><td>Construction</td><td>Project Costs</td><td>2</td><td>Active</td></tr><tr><td>CA-310</td><td>Concrete Works</td><td>CA-300</td><td>3</td><td>Active</td></tr>')}<div class="cp-vd-form"><label>Default cost account<select disabled><option>CA-300 Construction</option></select></label><label>Account code<input value="CA-310" disabled></label><label>Account name<input value="Concrete Works" disabled></label><label>Parent account<select disabled><option>CA-300 Construction</option></select></label></div><p class="cp-vd-note">Cost-account coding is separate from budget creation and cost transactions.</p></section>`;
    case "global-change":
      return `<section class="cp-vd-global-change"><header class="cp-vd-assignment-context"><strong>${esc(t(state.locale,"Global Change Specification","مشخصات تغییر سراسری"))}</strong><span>GC-004 · ${esc(t(state.locale,"Current user","کاربر جاری"))}</span></header>
      <div class="cp-vd-form"><label>${esc(t(state.locale,"Specification name","نام مشخصات"))}<input value="Normalize remaining duration" disabled></label><label>${esc(t(state.locale,"Available to","قابل دسترس برای"))}<select disabled><option>Current User</option><option>All Users</option><option>Another User</option></select></label><label>${esc(t(state.locale,"Change subject","موضوع تغییر"))}<select disabled><option>Activities</option><option>Resource Assignments</option><option>Project Expenses</option></select></label><label>${esc(t(state.locale,"Specification status","وضعیت مشخصات"))}<input value="Draft — not applied" disabled></label></div>
      <section><h3>${esc(t(state.locale,"If — Conditions","اگر — شروط"))}</h3>${rows(["Join","Parameter","Operator","Value"],'<tr><td>All</td><td>Activity Status</td><td>Equals</td><td>In Progress</td></tr><tr><td>And</td><td>Remaining Duration</td><td>Greater than</td><td>20d</td></tr>')}<div class="cp-vd-inline-actions"><button type="button" disabled>Add condition</button><button type="button" disabled>Delete</button><button type="button" disabled>▲</button><button type="button" disabled>▼</button></div></section>
      <section><h3>${esc(t(state.locale,"Then / Else Statements","دستورات آنگاه / در غیر این صورت"))}</h3>${rows(["Branch","Parameter","Operator","New value"],'<tr><td>Then</td><td>Remaining Duration</td><td>Assign</td><td>Remaining Duration − 2d</td></tr><tr><td>Else</td><td>Activity Code: REVIEW</td><td>Assign</td><td>Required</td></tr>')}<div class="cp-vd-inline-actions"><button type="button" disabled>Add Then</button><button type="button" disabled>Add Else</button><button type="button" disabled>Move up</button><button type="button" disabled>Move down</button></div></section>
      <section><h3>${esc(t(state.locale,"Preview Change Report","پیش‌نمایش گزارش تغییرات"))}</h3>${rows(["Select","Project / WBS / Activity","Field","Old value","New value","Exception"],'<tr><td><input type="checkbox" checked disabled></td><td>CUBI-DEMO-001 / WBS-02 / A1040</td><td>Remaining Duration</td><td>22d</td><td>20d</td><td>—</td></tr><tr><td><input type="checkbox" disabled></td><td>CUBI-DEMO-001 / WBS-03 / A1080</td><td>Remaining Duration</td><td>—</td><td>—</td><td>Invalid value</td></tr>')}<div class="cp-vd-form"><label>${esc(t(state.locale,"Save report as","ذخیره گزارش به‌صورت"))}<select disabled><option>HTML</option><option>Text (.txt)</option></select></label><label class="cp-vd-check"><input type="checkbox" disabled> Overwrite existing report</label></div></section>
      <p class="cp-vd-note">${esc(t(state.locale,"Preview first, exclude exception rows, verify old/new values and permissions, then explicitly commit. This is a visual sample; no project values are changed.","ابتدا پیش‌نمایش بگیرید، ردیف‌های دارای خطا را کنار بگذارید، مقادیر قبلی/جدید و مجوزها را بررسی و سپس صریحاً ثبت کنید. این نمونه بصری است و داده پروژه را تغییر نمی‌دهد."))}</p></section>`;
    case "reports-runner":
      return `<section class="cp-vd-report-runner"><header class="cp-vd-assignment-context"><strong>${esc(t(state.locale,"Report Library","کتابخانه گزارش‌ها"))}</strong><span>Global · Project · User</span></header>
      <div class="cp-vd-inline-actions"><button type="button" disabled>Run</button><button type="button" disabled>Run Batch</button><button type="button" disabled>New</button><button type="button" disabled>Modify</button><button type="button" disabled>Delete</button><button type="button" disabled>Import</button><button type="button" disabled>Export</button><button type="button" disabled>Report Wizard</button><button type="button" disabled>Report Editor</button><button type="button" disabled>Groups / Batches</button></div>
      ${rows(["Select","Report name","Scope","Group","Last run","Format"],'<tr><td><input type="checkbox" disabled></td><td>Activity Schedule Detail</td><td>Project</td><td>Schedules</td><td>—</td><td>HTML</td></tr><tr><td><input type="checkbox" disabled></td><td>Resource and Role Summary</td><td>Global</td><td>Resources</td><td>—</td><td>PDF</td></tr><tr><td><input type="checkbox" disabled></td><td>Cost Variance by WBS</td><td>User</td><td>Cost Control</td><td>—</td><td>Spreadsheet</td></tr>')}
      <section><h3>${esc(t(state.locale,"Run Parameters","پارامترهای اجرا"))}</h3><div class="cp-vd-form"><label>Project<select disabled><option>CUBI-DEMO-001</option></select></label><label>Data date<input type="date" value="2026-12-03" disabled></label><label>Time period<select disabled><option>Current period</option><option>Financial year</option></select></label><label>Output format<select disabled><option>HTML</option><option>PDF</option><option>Spreadsheet</option><option>Text</option></select></label><label>Output destination<input value="Reports/CUBI-DEMO-001" disabled></label></div></section>
      <p class="cp-vd-note">${esc(t(state.locale,"Reports can be global or project reports and may be imported/exported, grouped and run in batches. Preview output and report execution are not connected.","گزارش‌ها می‌توانند سراسری یا پروژه‌ای باشند و امکان ورود/خروجی، گروه‌بندی و اجرای دسته‌ای دارند. اجرای گزارش و پیش‌نمایش خروجی متصل نیست."))}</p></section>`;
    case "threshold-monitor":
      return `<section class="cp-vd-threshold-monitor"><header class="cp-vd-assignment-context"><strong>${esc(t(state.locale,"Threshold Monitoring","پایش آستانه‌ها"))}</strong><span>Project: CUBI-DEMO-001</span></header>
      ${rows(["Threshold","Parameter","Lower / Upper limit","Monitor","Status"],'<tr><td>Schedule variance</td><td>Finish variance</td><td>+10d</td><td>Weekly</td><td><span class="cp-vd-status is-warning">Exceeded</span></td></tr><tr><td>Cost exposure</td><td>At Completion Variance</td><td>€25,000</td><td>Monthly</td><td><span class="cp-vd-status is-warning">Exceeded</span></td></tr><tr><td>Float watch</td><td>Total Float</td><td>0d</td><td>Daily</td><td><span class="cp-vd-status">Within limit</span></td></tr>')}
      <div class="cp-vd-inline-actions"><button type="button" disabled>Add Threshold</button><button type="button" disabled>Assign Responsible</button><button type="button" disabled>Monitor</button><button type="button" disabled>Issue Navigator</button></div>
      <section><h3>${esc(t(state.locale,"Generated Issues","مسائل ایجادشده"))}</h3>${rows(["Issue ID","Threshold","Activity / WBS","Priority","Responsible","Status"],'<tr><td>ISS-014</td><td>Schedule variance</td><td>A1040 · Concrete foundations</td><td>High</td><td>Project Controls</td><td>Open</td></tr><tr><td>ISS-018</td><td>Cost exposure</td><td>WBS-03 · Construction</td><td>Medium</td><td>Cost Engineer</td><td>Under review</td></tr>')}</section>
      <section><h3>${esc(t(state.locale,"Issue Details and History","جزئیات و تاریخچه مسئله"))}</h3><div class="cp-vd-form"><label>Issue title<input value="Foundation work behind approved plan" disabled></label><label>Priority<select disabled><option>High</option><option>Medium</option><option>Low</option></select></label><label>Responsible manager<select disabled><option>Project Controls</option></select></label><label>Tracking layout<select disabled><option>Six-week lookahead</option></select></label><label>Status<select disabled><option>Open</option><option>In Progress</option><option>Closed</option></select></label><label>History<input value="Created · Assigned · Commented" disabled></label></div></section>
      <p class="cp-vd-note">${esc(t(state.locale,"Threshold monitoring, issue generation, responsibility assignment, history and tracking layouts are not connected in this preview.","پایش آستانه، ایجاد مسئله، تخصیص مسئولیت، تاریخچه و چیدمان پیگیری در این پیش‌نمایش متصل نیستند."))}</p></section>`;
    case "assign-activity-codes":
      return `<section><h3>${esc(t(state.locale,"Assign Activity Codes","تخصیص کدهای فعالیت"))}</h3><div class="cp-vd-form"><label>Activity<input value="A1040 · Concrete foundations" disabled></label><label>Code type<select disabled><option>DISC — Discipline</option><option>PHASE — Project Phase</option><option>AREA — Work Area</option></select></label><label>Code scope<select disabled><option>Project</option><option>EPS</option><option>Global</option></select></label><label>Code value<select disabled><option>CIV — Civil</option><option>STR — Structural</option><option>MEP — Mechanical / Electrical</option></select></label></div>${rows(["Code","Value","Description","Scope","Assigned"],'<tr><td>DISC</td><td>CIV</td><td>Civil works</td><td>Project</td><td>Yes</td></tr><tr><td>PHASE</td><td>EXEC</td><td>Execution</td><td>Global</td><td>Yes</td></tr>')}<p class="cp-vd-note">Global, EPS and project code scopes are separate. Code assignment is preview-only.</p></section>`;
    case "recalculate-assignment-costs":
      return `<section class="cp-vd-financial-dialog"><h3>${esc(t(state.locale,"Recalculate Resource and Role Assignment Costs","محاسبه مجدد هزینه تخصیص منابع و نقش‌ها"))}</h3><div class="cp-vd-form"><label>Scope<select disabled><option>Current project</option><option>Selected activities</option></select></label><label>Rate source<select disabled><option>Assignment rate source</option><option>Resource price list</option><option>Role price list</option></select></label><label>Effective date<input type="date" value="2026-12-03" disabled></label><label>Currency<select disabled><option>Project currency — EUR</option></select></label></div><fieldset><legend>Recalculate</legend><label><input type="checkbox" checked disabled> Labor and non-labor resource costs</label><label><input type="checkbox" checked disabled> Material resource costs</label><label><input type="checkbox" checked disabled> Role assignment costs</label><label><input type="checkbox" disabled> Preserve manually entered costs</label></fieldset><p class="cp-vd-note">Assignment costs depend on units, price/rate source, effective dates, currency and rate type. No costs are recalculated here.</p></section>`;
    case "import":
      return `<section class="cp-vd-interchange"><div class="cp-vd-interchange-tabs"><strong>Import Project</strong><span class="is-active">Import</span><span>Template Manager</span><span>Status</span></div>
        <div class="cp-vd-interchange-grid"><div class="cp-vd-interchange-main">
          <fieldset><legend>Source</legend><div class="cp-vd-form"><label>Import type<select disabled><option>Project Archive (.xer)</option><option>Structured Project XML (.xml)</option><option>Microsoft Project XML</option><option>XLSX Spreadsheet</option><option>MPX</option></select></label><label>Information type<select disabled><option>Project</option><option>Resource Only</option><option>Role Only</option></select></label><label>File<input value="CUBI-DEMO-001.xer" readonly></label><label>Template<select disabled><option>Standard Project Import</option><option>Schedule Only</option><option>Full Project + Baselines</option></select></label><label>Template actions<select disabled><option>Manage Templates…</option><option>New Template…</option><option>Modify Template…</option></select></label></div></fieldset>
          <fieldset><legend>Import action and destination</legend><div class="cp-vd-form"><label>Import action<select disabled><option>Create New</option><option>Add Into Existing Project</option><option>Replace Existing</option><option>Update Existing</option></select></label><label>Import to EPS / Project / WBS<input value="CUBI Portfolio / Infrastructure" readonly></label><label>Project name handling<select disabled><option>Use source name</option><option>Use mapped name</option></select></label><label>Baseline import (XML only)<select disabled><option>Unavailable for XER — select Structured Project XML (.xml)</option><option>Project and selected baselines</option><option>Primary only</option></select></label></div></fieldset>
          <fieldset><legend>Data selection / template mapping</legend><div class="cp-vd-interchange-checks">${["Project properties","WBS hierarchy","Activities and milestones","Relationships and lag","Resources and roles","Resource assignments","Calendars","Activity / Project / Resource codes","Expenses and cost accounts","Custom fields","Financial period actuals","Baselines"].map((name,i)=>`<label><input type="checkbox" ${i<10?"checked":""} disabled> ${name}</label>`).join("")}</div></fieldset>
          <div class="cp-vd-interchange-mapping"><strong>Field mapping preview</strong>${rows(["Source field","CUBI target","Action"],`<tr><td>Activity ID</td><td>Activity ID</td><td>Map</td></tr><tr><td>Activity Name</td><td>Activity Name</td><td>Map</td></tr><tr><td>Calendar ID</td><td>Calendar reference</td><td>Match / create</td></tr><tr><td>EPS Activity Code</td><td>Activity Code</td><td>Convert to project / ignore</td></tr><tr><td>Financial Period Start/Finish</td><td>Financial period calendar</td><td>Exact date match required</td></tr>`)}</div>
        </div><aside class="cp-vd-interchange-side"><strong>Pre-import validation</strong><ul><li>File format and version</li><li>Project / WBS destination permission</li><li>Duplicate project and activity IDs</li><li>Calendar and code dictionary matches</li><li>Relationship endpoints and cycles</li><li>Baseline selection and conflicts</li><li>Financial-period date alignment</li><li>Custom-field type compatibility</li></ul><div class="cp-vd-admin-callout"><strong>Conflict policy</strong><span>Create, add, replace and update are materially different operations. Replace must require a destructive impact preview and explicit confirmation.</span></div></aside></div>
        <p class="cp-vd-note">${esc(t(state.locale,"Visual preview only: no file is read, parsed, mapped, validated or imported. Real import must produce a row-level error report and a reversible transaction.", "پیش‌نمایش بصری است: هیچ فایلی خوانده، تحلیل، نگاشت، اعتبارسنجی یا وارد نمی‌شود. ورود واقعی باید گزارش خطای ردیفی و تراکنش قابل بازگشت داشته باشد."))}</p></section>`;
    case "export":
      return `<section class="cp-vd-interchange"><div class="cp-vd-interchange-tabs"><strong>Export Project</strong><span class="is-active">Export</span><span>Template Manager</span></div>
        <div class="cp-vd-interchange-grid"><div class="cp-vd-interchange-main">
          <fieldset><legend>Export source and format</legend><div class="cp-vd-form"><label>Export type<select disabled><option>Project Archive (.xer)</option><option>Structured Project XML (.xml)</option><option>Microsoft Project XML</option><option>XLSX Spreadsheet</option><option>MPX</option><option>UN/CEFACT IMS XML</option><option>IPMDAR</option><option>CPP</option></select></label><label>Information type<select disabled><option>Project</option><option>Resource Only</option><option>Role Only</option><option>Activities</option><option>Activity Relationships</option><option>Expenses</option><option>Resources</option><option>Resource Assignments</option></select></label><label>Project<select disabled><option>CUBI-DEMO-001 — Riverside Pump Station Upgrade</option></select></label><label>Template<select disabled><option>Standard Project Export</option><option>Full Project Archive</option><option>Schedule Exchange</option></select></label><label>Output file<input value="CUBI-DEMO-001-export.xer" readonly></label></div></fieldset>
          <fieldset><legend>Export content</legend><div class="cp-vd-interchange-checks">${["Project and WBS","Activities and relationships","Resources, roles and assignments","Calendars and shifts","Activity / Project / Resource codes","Expenses and cost accounts","Custom fields","Project and assigned baselines","Stored period performance","Documents and notes"].map((name,i)=>`<label><input type="checkbox" ${i<8?"checked":""} disabled> ${name}</label>`).join("")}</div></fieldset>
          <fieldset><legend>Baseline selection</legend><div class="cp-vd-form"><label>Baseline export mode<select disabled><option>Project / Primary / Secondary / Tertiary</option><option>Selected baselines</option><option>None</option></select></label><label>Data date<input value="2026-12-03" readonly></label></div></fieldset>
        </div><aside class="cp-vd-interchange-side"><strong>Export checks</strong><ul><li>Export Project Data privilege</li><li>Selected project scope</li><li>Personal information disclosure</li><li>Template and format compatibility</li><li>Baseline and financial period alignment</li><li>Output destination and overwrite policy</li></ul><div class="cp-vd-admin-callout"><strong>Data protection</strong><span>Export packages can contain personal or confidential project information. Apply access controls and audit the export.</span></div></aside></div>
        <p class="cp-vd-note">${esc(t(state.locale,"Visual preview only: no project data is serialized and no file is written. Export content is format-dependent; unsupported objects must be reported, not silently dropped.", "پیش‌نمایش بصری است: هیچ داده پروژه‌ای سریال‌سازی و هیچ فایلی نوشته نمی‌شود. محتوای خروجی وابسته به قالب است؛ اشیای پشتیبانی‌نشده باید گزارش شوند، نه اینکه بی‌صدا حذف شوند."))}</p></section>`;
    case "print":
      return `<section class="cp-vd-print-workspace">
        <header class="cp-vd-print-toolbar" role="toolbar" aria-label="${esc(t(state.locale,"Print preview toolbar","نوار ابزار پیش‌نمایش چاپ"))}">
          <button type="button" disabled>${esc(t(state.locale,"Print","چاپ"))}</button><button type="button" data-vd-dialog="page-setup">${esc(t(state.locale,"Page Setup…","تنظیم صفحه…"))}</button><button type="button" data-vd-dialog="print-setup">${esc(t(state.locale,"Print Setup…","تنظیم چاپ…"))}</button>
          <span class="cp-vd-print-divider"></span><button type="button" disabled aria-label="First page">|◀</button><button type="button" disabled aria-label="Previous page">◀</button><span class="cp-vd-print-page-count">Page 1 of 3</span><button type="button" disabled aria-label="Next page">▶</button><button type="button" disabled aria-label="Last page">▶|</button>
          <span class="cp-vd-print-divider"></span><button type="button" disabled>−</button><span>100%</span><button type="button" disabled>＋</button><button type="button" disabled>${esc(t(state.locale,"Portrait","عمودی"))}</button><button type="button" disabled>${esc(t(state.locale,"Landscape","افقی"))}</button>
        </header>
        <div class="cp-vd-print-stage"><div class="cp-vd-print-page">
          <div class="cp-vd-print-page-header"><span>CUBI · Construction Project Controls</span><span>Riverside Pump Station Upgrade</span></div>
          <h2>${esc(t(state.locale,"Activity Schedule","برنامه زمان‌بندی فعالیت‌ها"))}</h2><p><bdi dir="ltr">CUBI-DEMO-001</bdi> · Data Date: 03-Dec-2026</p>
          <table class="cp-vd-mini"><thead><tr><th>Activity ID</th><th>Activity Name</th><th>Start</th><th>Finish</th><th>% Complete</th></tr></thead><tbody>${ACTIVITIES.slice(0,8).map((row)=>`<tr><td>${esc(row.id)}</td><td>${esc(row.name)}</td><td>${fmtDate(row.start)}</td><td>${fmtDate(row.finish)}</td><td>${row.pct}%</td></tr>`).join("")}</tbody></table>
          <div class="cp-vd-print-gantt"><span></span><span></span><span></span><span></span><span></span><span></span><span></span><span></span></div>
          <footer class="cp-vd-print-page-footer"><span>Confidential · CUBI Project Workspace</span><span>1 / 3</span></footer>
        </div></div>
        <p class="cp-vd-note">${esc(t(state.locale,"Print preview is illustrative. Page count, printer output, PDF/HTML publishing and page navigation are not connected.", "پیش‌نمایش چاپ نمونه است؛ تعداد صفحات، خروجی چاپگر، انتشار PDF/HTML و پیمایش صفحات متصل نیستند."))}</p>
      </section>`;
    case "page-setup":
      return `<section class="cp-vd-page-setup"><nav class="cp-vd-page-setup-tabs" role="tablist"><button type="button" class="is-active" aria-selected="true" disabled>${esc(t(state.locale,"Page","صفحه"))}</button><button type="button" aria-selected="false" disabled>${esc(t(state.locale,"Margins","حاشیه‌ها"))}</button><button type="button" aria-selected="false" disabled>${esc(t(state.locale,"Header/Footer","سربرگ / پابرگ"))}</button><button type="button" aria-selected="false" disabled>${esc(t(state.locale,"Sheet","برگه"))}</button></nav>
        <section class="cp-vd-page-setup-section"><h3>${esc(t(state.locale,"Orientation","جهت صفحه"))}</h3><label><input type="radio" name="vd-page-orientation" disabled> ${esc(t(state.locale,"Portrait","عمودی"))}</label><label><input type="radio" name="vd-page-orientation" checked disabled> ${esc(t(state.locale,"Landscape","افقی"))}</label></section>
        <section class="cp-vd-page-setup-section"><h3>${esc(t(state.locale,"Scaling","مقیاس‌بندی"))}</h3><label><input type="radio" name="vd-page-scale" checked disabled> ${esc(t(state.locale,"Adjust to","تنظیم بر اساس"))} <input type="number" value="100" disabled> % ${esc(t(state.locale,"normal size","اندازه عادی"))}</label><label><input type="radio" name="vd-page-scale" disabled> ${esc(t(state.locale,"Fit to","جاسازی در"))} <input type="number" value="1" disabled> ${esc(t(state.locale,"page(s) wide by","صفحه عرض در"))} <input type="number" value="0" disabled> ${esc(t(state.locale,"tall","صفحه ارتفاع"))}</label><label><input type="radio" name="vd-page-scale" disabled> ${esc(t(state.locale,"Fit timescale to","تنظیم مقیاس زمانی در"))} <input type="number" value="1" disabled> ${esc(t(state.locale,"page(s) wide","صفحه عرض"))}</label></section>
        <section class="cp-vd-page-setup-section"><h3>${esc(t(state.locale,"Paper size","اندازه کاغذ"))}</h3><div class="cp-vd-form"><label>${esc(t(state.locale,"Paper","کاغذ"))}<select disabled><option>A4</option><option>A3</option><option>Letter</option><option>Legal</option></select></label><label>${esc(t(state.locale,"Width","عرض"))}<input value="297 mm" disabled></label><label>${esc(t(state.locale,"Height","ارتفاع"))}<input value="210 mm" disabled></label><label>${esc(t(state.locale,"Units","واحد"))}<select disabled><option>Millimeters</option><option>Inches</option></select></label></div></section>
        <section class="cp-vd-page-setup-section"><h3>${esc(t(state.locale,"Margins","حاشیه‌ها"))}</h3><div class="cp-vd-form">${[["Top","بالا","12"],["Bottom","پایین","12"],["Left","چپ","10"],["Right","راست","10"],["Header","سربرگ","5"],["Footer","پابرگ","5"]].map(([en,fa,value])=>`<label>${esc(t(state.locale,en,fa))}<input type="number" value="${value}" disabled></label>`).join("")}</div></section>
        <section class="cp-vd-page-setup-section"><h3>${esc(t(state.locale,"Header and footer content","محتوای سربرگ و پابرگ"))}</h3><div class="cp-vd-form"><label>${esc(t(state.locale,"Header left","سربرگ چپ"))}<input value="Project name" disabled></label><label>${esc(t(state.locale,"Header center","سربرگ وسط"))}<input value="Activity Schedule" disabled></label><label>${esc(t(state.locale,"Header right","سربرگ راست"))}<input value="Data Date" disabled></label><label>${esc(t(state.locale,"Footer left","پابرگ چپ"))}<input value="CUBI" disabled></label><label>${esc(t(state.locale,"Footer center","پابرگ وسط"))}<input value="Confidential" disabled></label><label>${esc(t(state.locale,"Footer right","پابرگ راست"))}<input value="Page number" disabled></label></div></section>
        <section class="cp-vd-page-setup-section"><h3>${esc(t(state.locale,"Sheet options","گزینه‌های برگه"))}</h3><div class="cp-vd-form"><label>${esc(t(state.locale,"Date range","بازه تاریخ"))}<select disabled><option>Entire timescale</option><option>Current timescale</option><option>Custom range</option></select></label><label>${esc(t(state.locale,"Pages wide","تعداد صفحات عرض"))}<input type="number" value="1" disabled></label><label>${esc(t(state.locale,"Columns to print","ستون‌های قابل چاپ"))}<input value="All visible columns" disabled></label><label>${esc(t(state.locale,"Activity table scale","مقیاس جدول فعالیت"))}<input value="100%" disabled></label><label class="cp-vd-check"><input type="checkbox" checked disabled> ${esc(t(state.locale,"Repeat table on every page","تکرار جدول در همه صفحات"))}</label><label class="cp-vd-check"><input type="checkbox" disabled> ${esc(t(state.locale,"Print with gradient","چاپ با طیف رنگی"))}</label><label>${esc(t(state.locale,"Tiled page order","ترتیب صفحات کاشی‌شده"))}<select disabled><option>Across, then down</option><option>Down, then across</option></select></label></div></section>
        <p class="cp-vd-note">${esc(t(state.locale,"Page setup preview only. The selected paper, margins, scaling, header/footer and sheet options are not saved or sent to a printer.", "تنظیم صفحه صرفاً پیش‌نمایش است؛ کاغذ، حاشیه‌ها، مقیاس، سربرگ/پابرگ و گزینه‌های برگه ذخیره یا به چاپگر ارسال نمی‌شوند."))}</p>
      </section>`;
    case "print-setup":
      return `<section class="cp-vd-page-setup"><h3>${esc(t(state.locale,"Printer selection and properties","انتخاب چاپگر و مشخصات آن"))}</h3><div class="cp-vd-form"><label>${esc(t(state.locale,"Printer","چاپگر"))}<select disabled><option>System default printer</option><option>Save as PDF</option></select></label><label>${esc(t(state.locale,"Paper source","منبع کاغذ"))}<select disabled><option>Auto select</option><option>Tray 1</option></select></label><label>${esc(t(state.locale,"Print quality","کیفیت چاپ"))}<select disabled><option>Normal</option><option>Draft</option><option>High</option></select></label><label>${esc(t(state.locale,"Color mode","حالت رنگ"))}<select disabled><option>Color</option><option>Grayscale</option></select></label></div><p class="cp-vd-note">${esc(t(state.locale,"Printer driver settings are not available in this browser preview.", "تنظیمات درایور چاپگر در این پیش‌نمایش مرورگر در دسترس نیست."))}</p></section>`;
    case "report-wizard":
      return `<div class="cp-vd-form"><label>${esc(t(state.locale, "Report", "گزارش"))}<select><option>Schedule report</option><option>Cost report</option><option>Resource report</option></select></label><label>${esc(t(state.locale, "Group by", "گروه‌بندی"))}<select><option>WBS</option><option>Resource</option></select></label><label class="cp-vd-check"><input type="checkbox" checked> ${esc(t(state.locale, "Include Gantt chart", "شامل نمودار گانت"))}</label></div>`;
    case "preferences":
      return `<div class="cp-vd-form"><label>${esc(t(state.locale, "Language", "زبان"))}<select><option>English</option><option>فارسی</option></select></label><label>${esc(t(state.locale, "Date format", "قالب تاریخ"))}<select><option>DD-MMM-YY</option><option>YYYY-MM-DD</option></select></label><label class="cp-vd-check"><input type="checkbox" checked> ${esc(t(state.locale, "Confirm before delete", "تأیید پیش از حذف"))}</label></div>`;
    case "admin-preferences":
      return `<div class="cp-vd-form"><label>${esc(t(state.locale, "Industry", "صنعت"))}<select><option>Construction</option><option>Engineering</option></select></label><label>${esc(t(state.locale, "Week starts on", "شروع هفته"))}<select><option>Sunday</option><option>Saturday</option></select></label></div>`;
    case "dictionaries":
      return `${rows(["Dictionary", "Values"], `<tr><td>Activity codes</td><td>Phase, Discipline</td></tr><tr><td>Custom fields</td><td>Package, Zone</td></tr><tr><td>Currencies</td><td>USD</td></tr>`)}`;
    case "roles":
      return `${rows(["Role", "Units", "Rate"], `<tr><td>Site engineer</td><td>2.0</td><td>85</td></tr><tr><td>Planner</td><td>1.0</td><td>95</td></tr>`)}`;
    case "security-profiles":
      return `${rows(["Profile", "Users", "Access"], `<tr><td>Administrator</td><td>1</td><td>Full</td></tr><tr><td>Project Manager</td><td>3</td><td>Project</td></tr><tr><td>Read only</td><td>5</td><td>View</td></tr>`)}<p class="cp-vd-note">${esc(t(state.locale, "Sample profiles for layout review.", "پروفایل‌های نمونه برای بازبینی چیدمان."))}</p>`;
    case "network-options":
      return `<div class="cp-vd-form"><label>${esc(t(state.locale, "Box template", "قالب جعبه"))}<select><option>Activity ID / Name / Dates</option><option>Activity ID / Name</option></select></label><label class="cp-vd-check"><input type="checkbox" checked> ${esc(t(state.locale, "Critical path border", "حاشیهٔ مسیر بحرانی"))}</label></div>`;
    case "timeline-options":
      return `<div class="cp-vd-two"><div><strong>${esc(t(state.locale, "Show on timeline", "نمایش در خط زمانی"))}</strong><ul>${[["Summary bars", "میله‌های خلاصه"], ["Milestones", "نقاط عطف"], ["Data date", "تاریخ داده"], ["Phase labels", "برچسب فازها"]].map((item) => `<li><label><input type="checkbox" checked> ${esc(t(state.locale, item[0], item[1]))}</label></li>`).join("")}</ul></div><div class="cp-vd-form"><label>${esc(t(state.locale, "Date format", "قالب تاریخ"))}<select><option>DD-MMM-YY</option><option>DD/MM/YYYY</option></select></label><label>${esc(t(state.locale, "Bar height", "ارتفاع میله"))}<input value="14 px"></label></div></div>`;
    case "background-lines":
      return `<div class="cp-vd-form"><label>Major vertical lines<select><option>Month boundaries</option><option>Quarter boundaries</option><option>Year boundaries</option><option>None</option></select></label><label>Minor vertical lines<select><option>Week boundaries</option><option>Day boundaries</option><option>None</option></select></label><label>Horizontal row lines<select><option>Every activity</option><option>Group bands only</option><option>None</option></select></label><div class="cp-vd-two"><label>Major line color<input type="color" value="#b7c3d1"></label><label>Minor line color<input type="color" value="#e2e8f0"></label></div><label class="cp-vd-check"><input type="checkbox" checked> Shade nonworking periods from assigned calendar</label><p class="cp-vd-note">Display settings only. Calendar working time is not changed.</p></div>`;
    case "relationship-lines":
      return `<div class="cp-vd-form"><label class="cp-vd-check"><input type="checkbox" checked> Show relationship lines</label><label>Line style<select><option>Solid</option><option>Dashed</option><option>Dotted</option></select></label><label>Line color<select><option>By relationship type</option><option>Single color</option><option>Critical path color</option></select></label><div class="cp-vd-two"><label>Normal relationship color<input type="color" value="#64748b"></label><label>Critical relationship color<input type="color" value="#c0392b"></label></div><label>Arrowhead<select><option>At successor</option><option>Both ends</option><option>None</option></select></label><label class="cp-vd-check"><input type="checkbox"> Show relationship labels</label><p class="cp-vd-note">FS, SS, FF and SF links are shown as sample graphics only.</p></div>`;
    case "data-date-line":
      return `<div class="cp-vd-form"><label class="cp-vd-check"><input type="checkbox" checked> Display data date line</label><label>Data date<input value="2026-12-03" readonly></label><label>Line style<select><option>Solid</option><option>Dashed</option><option>Dotted</option></select></label><label>Line width<select><option>2 px</option><option>1 px</option><option>3 px</option></select></label><label>Line color<input type="color" value="#d97706"></label><label>Label position<select><option>Top</option><option>Bottom</option><option>Hidden</option></select></label></div>`;
    case "gantt-legend":
      return `<div class="cp-vd-form"><label class="cp-vd-check"><input type="checkbox" checked> Show legend</label><label>Position<select><option>Bottom</option><option>Top</option><option>Left</option><option>Right</option></select></label><label>Contents<select><option>Visible bar definitions</option><option>All bar definitions</option><option>Selected items</option></select></label><label class="cp-vd-check"><input type="checkbox" checked> Include critical and milestone symbols</label><label class="cp-vd-check"><input type="checkbox"> Include relationship line types</label><p class="cp-vd-note">Legend preview reflects the sample bar definitions.</p></div>`;
    case "progress-line":
      return `<div class="cp-vd-form"><label class="cp-vd-check"><input type="checkbox" checked> Display progress line</label><label>Progress basis<select><option>Activity percent complete</option><option>Physical percent complete</option><option>Duration percent complete</option></select></label><label>Reference date<select><option>Data date</option><option>Selected status date</option></select></label><label>Line style<select><option>Solid</option><option>Dashed</option><option>Dotted</option></select></label><label>Line color<input type="color" value="#15966a"></label><label>Line width<select><option>2 px</option><option>1 px</option><option>3 px</option></select></label><p class="cp-vd-note">No progress values are recalculated in this visual preview.</p></div>`;
    case "attachments":
      return `<div class="cp-vd-form"><div class="cp-vd-two"><section><h4>Curtain attachments</h4><label>Attachment<select><option>Construction phase</option><option>Procurement window</option><option>Commissioning window</option></select></label><div class="cp-vd-inline-actions"><button type="button">Add curtain</button><button type="button">Hide selected</button><button type="button">Show all</button><button type="button">Delete selected</button></div></section><section><h4>Text and notebook attachments</h4><label>Text attachment<input value="Design review gate"></label><label>Attach to bar<select><option>A1130 — Design review gate</option><option>A1320 — Foundations and plinth</option></select></label><label>Notebook item<select><option>Inspection notes</option><option>Construction method statement</option><option>Commissioning checklist</option></select></label><div class="cp-vd-inline-actions"><button type="button">Add text</button><button type="button">Remove text</button><button type="button">Attach notebook</button></div></section></div><p class="cp-vd-note">Attachment commands are non-persistent visual examples; no files or notebook records are changed.</p></div>`;
    case "collapsed-bars":
      return `<div class="cp-vd-form"><label class="cp-vd-check"><input type="checkbox" checked> Customize collapsed bars</label><label>Summary bar style<select><option>WBS summary bracket</option><option>Solid summary bar</option><option>Outline summary bar</option></select></label><label>Show child activity bars<select><option>Hide when collapsed</option><option>Show behind summary</option></select></label><label>Summary label<select><option>WBS name</option><option>WBS code</option><option>Activity count</option></select></label><label>Bar position<select><option>Top</option><option>Middle</option><option>Bottom</option></select></label><label>Bar color<input type="color" value="#6b7f96"></label><p class="cp-vd-note">Controls the visual representation of collapsed summary groups only.</p></div>`;
    case "network-box-layout":
      return `<div class="cp-vd-form"><div class="cp-vd-two"><section><h4>Activity box fields</h4><ul>${["Activity ID","Activity Name","Start","Finish","Original Duration","Remaining Duration","Total Float","Free Float","Percent Complete","Calendar","Activity Code"].map((item,index)=>`<li><label><input type="checkbox" ${index<8?"checked":""}> ${item}</label></li>`).join("")}</ul></section><section><h4>Box appearance</h4><label>Box template<select><option>Standard activity details</option><option>Compact ID and name</option><option>Dates and float</option><option>Resource and cost</option></select></label><label>Font<select><option>Workspace default</option><option>Inter 10</option><option>Inter 11</option><option>Vazirmatn 11</option></select></label><label>Normal fill<input type="color" value="#ffffff"></label><label>Critical fill<input type="color" value="#fff1f0"></label><label>Border color<input type="color" value="#7b8da3"></label><label>Box width<select><option>180 px</option><option>140 px</option><option>220 px</option></select></label></section></div><p class="cp-vd-note">Box fields and formatting are visual examples; the activity network is not recalculated.</p></div>`;
    case "trace-options":
      return `<div class="cp-vd-form"><div class="cp-vd-two"><label>Predecessor levels<select><option>1 level</option><option>2 levels</option><option>All levels</option></select></label><label>Successor levels<select><option>1 level</option><option>2 levels</option><option>All levels</option></select></label><label>Relationship labels<select><option>Type and lag</option><option>Type only</option><option>Hidden</option></select></label><label>Date labels<select><option>Start and finish</option><option>Start only</option><option>Hidden</option></select></label></div><div class="cp-vd-two"><label class="cp-vd-check"><input type="checkbox" checked> Highlight selected activity</label><label class="cp-vd-check"><input type="checkbox" checked> Highlight critical path</label><label class="cp-vd-check"><input type="checkbox"> Show total float</label><label class="cp-vd-check"><input type="checkbox" checked> Show relationship type and lag</label><label class="cp-vd-check"><input type="checkbox" checked> Auto-center selected activity</label></div><label>Connector routing<select><option>Orthogonal</option><option>Straight</option><option>Curved</option></select></label><p class="cp-vd-note">Trace Logic is a visual dependency inspection; no schedule calculation is executed.</p></div>`;
    case "usage-profile-options":
      return `<div class="cp-vd-form"><div class="cp-vd-two"><label>Display format<select><option>Regular histogram</option><option>Stacked histogram</option><option>Spreadsheet</option></select></label><label>Time interval<select><option>Week</option><option>Day</option><option>Month</option><option>Financial period</option></select></label><label>Data field<select><option>Budgeted units</option><option>Actual units</option><option>Remaining units</option><option>At completion units</option><option>Budgeted cost</option><option>Actual cost</option><option>Remaining cost</option></select></label><label>Grouping<select><option>WBS</option><option>Resource</option><option>Role</option><option>Activity code</option><option>None</option></select></label></div><div class="cp-vd-two"><label class="cp-vd-check"><input type="checkbox" checked> Show planned values</label><label class="cp-vd-check"><input type="checkbox" checked> Show actual values</label><label class="cp-vd-check"><input type="checkbox" checked> Show remaining values</label><label class="cp-vd-check"><input type="checkbox"> Show cumulative values</label><label class="cp-vd-check"><input type="checkbox" checked> Show profile legend</label><label class="cp-vd-check"><input type="checkbox"> Show resource availability</label><label class="cp-vd-check"><input type="checkbox"> Show resource limits</label><label class="cp-vd-check"><input type="checkbox"> Highlight overallocation</label></div><p class="cp-vd-note">Profile and spreadsheet values are fixed illustrative data and do not summarize live assignments.</p></div>`;
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
    "background-lines": ["Gantt Background Lines", "خطوط پس‌زمینه گانت"],
    "relationship-lines": ["Relationship Line Options", "تنظیمات خطوط روابط"],
    "data-date-line": ["Data Date Line", "خط تاریخ داده"],
    "gantt-legend": ["Gantt Legend", "راهنمای گانت"],
    "progress-line": ["Progress Line", "خط پیشرفت"],
    attachments: ["Gantt Attachments", "پیوست‌های گانت"],
    "collapsed-bars": ["Collapsed Bar Settings", "تنظیمات میله‌های جمع‌شده"],
    "network-box-layout": ["Activity Box Layout", "چیدمان جعبه فعالیت"],
    "trace-options": ["Trace Logic Preferences", "تنظیمات ردیابی منطق"],
    "usage-profile-options": ["Usage Profile and Spreadsheet Options", "تنظیمات پروفایل و صفحه مصرف"],
    "new-wbs": ["New WBS Element", "عنصر جدید WBS"], "new-form": ["Create Form", "ایجاد فرم"],
    "module-actions": ["Add / Edit Workspace Item", "افزودن / ویرایش آیتم محیط کار"],
    budgeting: ["Budget and Spending Plan", "بودجه و برنامه هزینه"], "earned-value": ["Earned Value Analysis", "تحلیل ارزش کسب‌شده"],
    "update-progress": ["Update Activity Progress", "به‌روزرسانی پیشرفت فعالیت"], "apply-actuals": ["Apply Actuals", "اعمال واقعیات"],
    "store-period-performance": ["Store Period Performance", "ثبت عملکرد دوره"], "expense-details": ["Expense Details", "جزئیات هزینه"],
    "cost-accounts": ["Cost Account Dictionary", "واژه‌نامه حساب‌های هزینه"],
    "global-change": ["Global Change", "تغییر سراسری"], "reports-runner": ["Reports", "گزارش‌ها"],
    "threshold-monitor": ["Threshold Monitor and Issue Navigator", "پایش آستانه و راهنمای مسائل"],
    "assign-activity-codes": ["Assign Activity Codes", "تخصیص کدهای فعالیت"],
    "recalculate-assignment-costs": ["Recalculate Assignment Costs", "محاسبه مجدد هزینه تخصیص‌ها"],
  };
  const entry = titles[name] ?? [name, name];
  return t(locale, entry[0], entry[1]);
}

function renderDialogs(state: DemoState): string {
  const names = ["columns", "filters", "group-sort", "timescale", "bars", "bar-options", "font-row", "layout-manager", "customize-details", "new-project", "project-properties", "calendar", "schedule", "level", "baselines", "find", "find-replace", "renumber", "assign-resources", "assign-roles", "assign-predecessors", "assign-successors", "add-activity", "import", "export", "print", "report-wizard", "preferences", "admin-preferences", "dictionaries", "roles", "network-options", "timeline-options", "shortcuts", "about", "security-profiles", "module-actions", "new-wbs", "new-form", "background-lines", "relationship-lines", "data-date-line", "gantt-legend", "progress-line", "attachments", "collapsed-bars", "network-box-layout", "trace-options", "usage-profile-options", "budgeting", "earned-value", "update-progress", "apply-actuals", "store-period-performance", "expense-details", "cost-accounts", "global-change", "reports-runner", "threshold-monitor", "assign-activity-codes", "recalculate-assignment-costs"];
  return names.map((name) => `<dialog class="cp-vd-dialog" data-vd-dialog="${name}">
    <form method="dialog" data-vd-form="${name}">
      <div class="cp-vd-dialog-title"><span>${esc(dialogTitle(name, state.locale))}</span><button type="button" data-vd-close aria-label="Close">×</button></div>
      <div class="cp-vd-dialog-body">${dialogContent(name, state)}</div>
      <div class="cp-vd-dialog-actions"><button type="submit" class="is-primary">${esc(t(state.locale, "OK", "تأیید"))}</button><button type="button" data-vd-default>${esc(t(state.locale, "Default", "پیش‌فرض"))}</button><button type="button" data-vd-close>${esc(t(state.locale, "Cancel", "لغو"))}</button></div>
    </form>
  </dialog>`).join("");
}

function renderLanguageSwitch(state: DemoState): string {
  // Only locales with complete translations in this visual shell are offered.
  // Add German, Chinese, or another locale here when its full shell pack ships.
  const supported = getAvailableWorkspaceLocales();
  return `<label class="cp-vd-language"><span>${esc(t(state.locale, "Language", "زبان"))}</span>
    <select data-vd-locale aria-label="${esc(t(state.locale, "Select language", "انتخاب زبان"))}" title="${esc(t(state.locale, "Select workspace language", "انتخاب زبان محیط کار"))}">
      ${supported.map((locale) => `<option value="${esc(locale)}"${state.locale === locale ? " selected" : ""}>${esc(getWorkspaceLocaleDisplayName(locale))}</option>`).join("")}
    </select>
  </label>`;
}

export function renderVisualDemo(state: DemoState): string {
  const index = WINDOWS.findIndex((window) => window.id === state.window);
  const navGroups: Array<{ id: string; en: string; fa: string; items: DemoWindowId[] }> = [
    { id: "planning", en: "Planning & Schedule", fa: "برنامه‌ریزی و زمان‌بندی", items: ["wbs", "activities", "network", "trace", "timeline", "activity-profile", "resource-profile", "activity-sheet", "resource-sheet", "calendars"] },
    { id: "controls", en: "Project Controls", fa: "کنترل پروژه", items: ["assignments", "resources", "roles", "cost-control", "progress-control", "procurement", "changes-claims", "tracking", "expenses", "thresholds", "issues", "risks"] },
    { id: "information", en: "Information & Administration", fa: "اطلاعات و مدیریت", items: ["documents", "reports", "form-builder", "comments", "organization", "administration", "smart-guide", "assistant", "search"] },
  ];
  const navGroup = (group: typeof navGroups[number]): string => {
    const collapsed = state.collapsedNavGroups.includes(group.id);
    return `<section class="cp-vd-nav-group"><button type="button" class="cp-vd-nav-heading" data-vd-nav-group="${group.id}" aria-expanded="${!collapsed}"><span>${esc(t(state.locale, group.en, group.fa))}</span><i aria-hidden="true">${collapsed ? "＋" : "−"}</i></button><div class="cp-vd-nav-group-items" ${collapsed ? "hidden" : ""}>${WINDOWS.filter((item) => group.items.includes(item.id)).map((item) => `<button type="button" class="cp-vd-nav-link${state.window === item.id ? " is-active" : ""}" data-vd-window="${item.id}" aria-current="${state.window === item.id ? "page" : "false"}"><span>${esc(label(item, state.locale))}</span></button>`).join("")}</div></section>`;
  };
  return `<style>
  .cp-vd-module-toolbar{display:flex;align-items:center;gap:5px;flex-wrap:wrap;padding:7px 10px;border-block:1px solid #d8e0e9;background:#f0f4f8}
  .cp-vd-module-toolbar button{border:1px solid #cbd6e2;border-radius:3px;background:#fff;color:#294765;padding:5px 9px;font:11px Inter,Vazirmatn,sans-serif}
  .cp-vd-module-toolbar button:disabled{opacity:.5;cursor:not-allowed}
  .cp-vd-details-context-name{max-width:260px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:11px;color:#294765}
  .cp-vd-details-context-project{font-size:10px;color:#6b7d91;white-space:nowrap}
  .cp-vd-details-empty{min-height:120px;background:#fff;border-block-start:1px solid #d8e0e9}
  .cp-vd-empty-selection{padding:22px 14px;text-align:center;color:#526579}
  .cp-vd-empty-selection strong{display:block;color:#294765;margin-bottom:6px}
  .cp-vd-empty-selection p{margin:0;font-size:12px}
  .cp-vd-filter-manager{display:grid;grid-template-columns:minmax(180px,230px) minmax(0,1fr);gap:12px;min-width:0}
  .cp-vd-filter-library,.cp-vd-filter-definition{min-width:0;border:1px solid #d8e0e9;background:#fff;padding:9px}
  .cp-vd-filter-library-head,.cp-vd-filter-rules-head{display:flex;align-items:center;justify-content:space-between;gap:8px;padding-bottom:7px;border-bottom:1px solid #e1e7ee;color:#294765;font-size:11px}
  .cp-vd-filter-category{padding:8px 0;border-bottom:1px solid #edf1f5}
  .cp-vd-filter-category strong{display:block;font-size:10px;color:#526579;margin-bottom:5px}
  .cp-vd-filter-category ul{list-style:none;padding:0;margin:0;display:grid;gap:5px}
  .cp-vd-filter-category label,.cp-vd-filter-logic label{display:flex;align-items:center;gap:5px;font-size:11px}
  .cp-vd-filter-definition{display:grid;gap:9px}
  .cp-vd-filter-definition fieldset{display:flex;gap:14px;flex-wrap:wrap;border:1px solid #d8e0e9;padding:8px}
  .cp-vd-filter-definition legend{font-size:10px;color:#526579;padding:0 4px}
  .cp-vd-filter-logic{display:flex;gap:14px;flex-wrap:wrap;padding:6px 8px;background:#f5f7fa;border:1px solid #e1e7ee}
  .cp-vd-filter-rules-head span{font-size:10px;color:#6b7d91}
  .cp-vd-filter-table{min-width:620px}
  .cp-vd-filter-table select,.cp-vd-filter-table input{width:100%;min-width:145px;max-width:100%;border:1px solid #cbd6e2;background:#fff;padding:5px;font:11px Inter,Vazirmatn,sans-serif}
  .cp-vd-filter-manager .cp-vd-form{grid-template-columns:minmax(0,1fr) minmax(0,180px)}
  .cp-vd-group-sort{display:grid;gap:12px;min-width:0}
  .cp-vd-group-sort-section{display:grid;gap:8px;min-width:0;border:1px solid #d8e0e9;background:#fff;padding:9px}
  .cp-vd-group-table,.cp-vd-sort-table{min-width:650px}
  .cp-vd-group-table select,.cp-vd-sort-table select{max-width:100%;min-width:115px;padding:4px;border:1px solid #cbd6e2;background:#fff;font:11px Inter,Vazirmatn,sans-serif}
  .cp-vd-group-table td:last-child{white-space:nowrap}
  .cp-vd-group-table td button{font-size:10px;padding:3px 5px;margin-inline-end:3px}
  .cp-vd-group-band-options{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:7px;padding:8px;background:#f5f7fa;border:1px solid #e1e7ee}
  .cp-vd-group-band-options label{display:flex;align-items:center;gap:5px;font-size:11px}
  @media(max-width:850px){.cp-vd-group-band-options{grid-template-columns:repeat(2,minmax(0,1fr))}}
  .cp-vd-timescale-editor{display:grid;gap:12px;min-width:0}
  .cp-vd-timescale-section{border:1px solid #d8e0e9;background:#fff;padding:10px;display:grid;gap:9px}
  .cp-vd-timescale-section h4{margin:0;color:#294765;font-size:11px}
  .cp-vd-timescale-top{grid-template-columns:repeat(4,minmax(0,1fr))}
  .cp-vd-timescale-grid{grid-template-columns:repeat(3,minmax(0,1fr))}
  .cp-vd-timescale-options{display:flex;gap:16px;flex-wrap:wrap;padding:7px;background:#f5f7fa}
  .cp-vd-timescale-options label{display:flex;align-items:center;gap:5px;font-size:11px}
  .cp-vd-timescale-preview{border:1px solid #d8e0e9;background:#f8fafc;padding:8px}
  .cp-vd-timescale-preview strong{font-size:10px;color:#294765}
  .cp-vd-timescale-ruler{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:1px;margin-top:7px}
  .cp-vd-timescale-ruler span{padding:5px 3px;text-align:center;background:#e7edf4;border-inline-start:1px solid #cbd6e2;font-size:10px;color:#294765}
  .cp-vd-timescale-ruler.is-minor span{background:#fff;color:#6b7d91}
  @media(max-width:850px){.cp-vd-timescale-top,.cp-vd-timescale-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
  .cp-vd-columns-editor{display:grid;gap:10px;min-width:0}
  .cp-vd-columns-toolbar,.cp-vd-columns-footer{display:flex;align-items:end;gap:8px;flex-wrap:wrap;padding:8px;background:#f5f7fa;border:1px solid #d8e0e9}
  .cp-vd-columns-toolbar label,.cp-vd-columns-footer label{display:grid;gap:4px;font-size:10px;color:#526579;flex:1;min-width:160px}
  .cp-vd-columns-toolbar input,.cp-vd-columns-toolbar select,.cp-vd-columns-footer select{min-width:0;padding:5px;border:1px solid #cbd6e2;background:#fff;font:11px Inter,Vazirmatn,sans-serif}
  .cp-vd-columns-transfer{display:grid;grid-template-columns:minmax(0,1fr) 58px minmax(0,1fr);gap:8px;align-items:center}
  .cp-vd-columns-list{min-width:0;border:1px solid #d8e0e9;background:#fff;padding:8px}
  .cp-vd-columns-list>strong{display:block;color:#294765;font-size:11px;padding-bottom:6px;border-bottom:1px solid #e1e7ee}
  .cp-vd-columns-list ul{list-style:none;padding:0;margin:7px 0;max-height:210px;overflow:auto;display:grid;gap:5px}
  .cp-vd-columns-list li{display:flex;align-items:center;justify-content:space-between;gap:6px;font-size:11px}
  .cp-vd-column-width{font-size:10px;color:#6b7d91}
  .cp-vd-columns-transfer-actions{display:grid;gap:6px}
  .cp-vd-columns-transfer-actions button{min-height:27px}
  .cp-vd-column-properties{border:1px solid #d8e0e9;background:#fff;padding:9px}
  .cp-vd-column-properties h4{margin:0 0 8px;color:#294765;font-size:11px}
  .cp-vd-column-properties .cp-vd-form{grid-template-columns:repeat(4,minmax(0,1fr))}
  @media(max-width:760px){.cp-vd-columns-transfer{grid-template-columns:1fr}.cp-vd-columns-transfer-actions{grid-template-columns:repeat(4,1fr)}.cp-vd-column-properties .cp-vd-form{grid-template-columns:repeat(2,minmax(0,1fr))}}
  .cp-vd-project-wizard{display:grid;gap:10px;min-width:0}
  .cp-vd-project-steps{list-style:none;padding:0;margin:0;display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:5px}
  .cp-vd-project-steps li{display:flex;align-items:center;gap:6px;padding:7px;background:#eef2f6;border:1px solid #d8e0e9;color:#526579;font-size:10px;min-width:0}
  .cp-vd-project-steps li[aria-current="step"]{background:#e7f0fa;border-color:#1976d2;color:#0f2747;font-weight:700}
  .cp-vd-project-steps b{display:grid;place-items:center;flex:0 0 20px;height:20px;border-radius:50%;background:#fff;border:1px solid #b8c5d3}
  .cp-vd-project-step{border:1px solid #d8e0e9;background:#fff;padding:10px;display:grid;gap:8px}
  .cp-vd-project-step h4{margin:0;padding-bottom:6px;border-bottom:1px solid #e1e7ee;color:#294765;font-size:11px}
  .cp-vd-project-grid{grid-template-columns:repeat(3,minmax(0,1fr))}
  .cp-vd-project-grid .is-wide{grid-column:1/-1}
  .cp-vd-project-grid em{color:#c0392b;font-style:normal}
  .cp-vd-project-grid small{font-size:9px;color:#6b7d91}
  .cp-vd-project-wizard-actions{display:flex;justify-content:flex-end;gap:7px;padding-top:4px}
  .cp-vd-project-wizard-actions .is-primary{background:#0f2747;color:#fff;border-color:#0f2747}
  @media(max-width:760px){.cp-vd-project-steps{grid-template-columns:repeat(2,minmax(0,1fr))}.cp-vd-project-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
  @media(max-width:480px){.cp-vd-project-grid{grid-template-columns:1fr}.cp-vd-project-grid .is-wide{grid-column:auto}}
  @media(max-width:850px){.cp-vd-filter-manager{grid-template-columns:1fr}.cp-vd-filter-library{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.cp-vd-filter-library-head{grid-column:1/-1}}
  .cp-vd-module-toolbar .cp-vd-note{margin-inline-start:auto}
  .cp-vd-module-split{display:grid;grid-template-columns:minmax(0,1fr) minmax(245px,30%);min-height:350px}
  .cp-vd-module-details{background:#f0f4f8;border-inline-start:1px solid #cbd5e1;padding:8px;min-width:0}
  .cp-vd-detail-heading{display:flex;justify-content:space-between;gap:8px;padding:7px;color:#294765}
  .cp-vd-detail-heading span{font-size:11px;color:#6b7d91}
  .cp-vd-detail-tabs{display:flex;gap:3px;overflow-x:auto;border-bottom:1px solid #cbd5e1}
  .cp-vd-detail-tabs button{border:0;border-bottom:2px solid transparent;background:transparent;padding:7px 8px;white-space:nowrap;color:#53677e;font-size:11px}
  .cp-vd-detail-tabs button.is-active{border-color:#c87935;color:#173d68;font-weight:700}
  .cp-vd-module-detail-panel{padding:10px 4px;font-size:11px}
  .cp-vd-module-detail{margin:0;display:grid;grid-template-columns:1fr;gap:7px}
  .cp-vd-module-detail div{display:grid;grid-template-columns:minmax(85px,38%) minmax(0,1fr);gap:8px;border-bottom:1px solid #dce3eb;padding:4px}
  .cp-vd-module-detail dt{color:#6b7d91}.cp-vd-module-detail dd{margin:0;color:#263d56;font-weight:600}
  @media(max-width:900px){.cp-vd-module-split{grid-template-columns:1fr}.cp-vd-module-details{border-inline-start:0;border-top:1px solid #cbd5e1}.cp-vd-module-toolbar .cp-vd-note{margin-inline-start:0}}
</style>
<style>
  .cp-vd-workspace-grid{display:grid;grid-template-columns:208px minmax(0,1fr) 48px;min-height:560px;background:#eef2f7}
  .cp-vd-left-nav{min-width:0;overflow:auto;background:#e7edf5;border-inline-end:1px solid #c7d2df;padding:8px 6px}
  .cp-vd-nav-group{margin:0 0 3px}.cp-vd-nav-group-items[hidden]{display:none}
  .cp-vd-nav-heading{display:flex;align-items:center;justify-content:space-between;width:100%;border:0;background:transparent;padding:10px 8px 5px;color:#718096;font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:.04em;text-align:start;cursor:pointer}
  .cp-vd-nav-heading i{font-style:normal;font-size:13px}.cp-vd-nav-link{display:flex;align-items:center;gap:8px;width:100%;border:0;border-radius:4px;background:transparent;color:#263c56;padding:7px 9px;text-align:start;font:12px Inter,Vazirmatn,sans-serif;cursor:pointer}
  .cp-vd-nav-link:hover{background:#dce6f1}.cp-vd-nav-link.is-active{background:#d3e2f4;color:#123d70;font-weight:700;box-shadow:inset 3px 0 #c87935}
  .cp-vd-main{min-width:0;overflow:auto;background:#f7f9fc}
  .cp-vd-right-rail{display:flex;flex-direction:column;align-items:center;gap:7px;padding:8px 4px;background:#e8edf4;border-inline-start:1px solid #c7d2df}
  .cp-vd-right-rail button{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:2px;width:38px;min-height:36px;border:1px solid #c8d3e0;border-radius:4px;background:#fff;color:#24476c;font-size:17px;cursor:pointer}
  .cp-vd-right-rail button:hover{background:#dce9f7;border-color:#7898bb}
  .cp-vd-right-rail .cp-vd-rail-add{min-height:58px;background:#173d68;color:#fff;border-color:#173d68}
  .cp-vd-rail-add span{font-size:10px;font-weight:700}
  @media(max-width:900px){.cp-vd-workspace-grid{grid-template-columns:minmax(0,1fr) 42px}.cp-vd-left-nav{grid-column:1/-1;display:flex;gap:4px;overflow-x:auto;border-inline-end:0;border-bottom:1px solid #c7d2df;max-height:54px}.cp-vd-nav-group,.cp-vd-nav-group-items{display:contents}.cp-vd-nav-heading{display:none}.cp-vd-nav-link{width:auto;white-space:nowrap;flex:0 0 auto}.cp-vd-main{grid-column:1}.cp-vd-right-rail{grid-column:2;grid-row:2;position:sticky;top:0}.cp-vd-right-rail button{width:34px}}
  @media(max-width:560px){.cp-vd-workspace-grid{grid-template-columns:minmax(0,1fr)}.cp-vd-left-nav{grid-column:1}.cp-vd-main{grid-column:1}.cp-vd-right-rail{grid-column:1;grid-row:auto;position:sticky;bottom:0;flex-direction:row;justify-content:space-around;z-index:5;border-inline-start:0;border-top:1px solid #c7d2df}.cp-vd-right-rail button{min-height:34px}.cp-vd-right-rail .cp-vd-rail-add{min-height:38px}}



.cp-vd-assistant-layout{display:grid;grid-template-columns:minmax(0,1fr) 260px;gap:10px;padding:12px;background:#eef2f7}.cp-vd-assistant-chat{display:flex;flex-direction:column;gap:10px;min-width:0}.cp-vd-assistant-context{display:flex;flex-wrap:wrap;gap:8px 16px;padding:9px 12px;border:1px solid #d5dee8;border-radius:5px;background:#fff;font-size:10px;color:#64748b}.cp-vd-assistant-context strong{color:#294765}.cp-vd-assistant-message{max-width:88%;padding:11px 13px;border:1px solid #d5dee8;border-radius:7px;background:#fff;color:#334155;font-size:11px}.cp-vd-assistant-message.is-user{align-self:flex-end;background:#e7f0fa;border-color:#c7d9ed}.cp-vd-assistant-message>b{color:#173d68}.cp-vd-assistant-message p{margin:7px 0;line-height:1.55}.cp-vd-assistant-message small{color:#718096}.cp-vd-assistant-message ul{padding-inline-start:18px;line-height:1.8}.cp-vd-assistant-proposal{margin-top:9px;padding:10px;border:1px solid #d8b78f;border-inline-start:4px solid #c87935;border-radius:4px;background:#fff9f1}.cp-vd-assistant-proposal p{margin:5px 0 9px}.cp-vd-assistant-composer{padding:10px;border:1px solid #cbd5e1;border-radius:6px;background:#fff}.cp-vd-assistant-composer textarea{width:100%;resize:vertical;border:1px solid #cbd5e1;border-radius:4px;padding:8px;font:12px Inter,Vazirmatn,sans-serif}.cp-vd-assistant-composer>div{display:flex;align-items:center;gap:7px;margin-top:7px}.cp-vd-assistant-composer button,.cp-vd-assistant-file{border:1px solid #cbd5e1;border-radius:4px;background:#f8fafc;padding:6px 9px;color:#425a73;font-size:10px}.cp-vd-assistant-file input{max-width:145px}.cp-vd-assistant-composer button:disabled,.cp-vd-assistant-composer textarea:disabled{opacity:.6}.cp-vd-assistant-composer small{display:block;margin-top:7px;color:#718096;font-size:9px}.cp-vd-assistant-side{padding:12px;border:1px solid #d5dee8;border-radius:5px;background:#f8fafc}.cp-vd-assistant-side h3{margin:0 0 9px;color:#294765;font-size:13px}.cp-vd-assistant-side article{padding:9px 0;border-bottom:1px solid #dce3eb}.cp-vd-assistant-side article strong{font-size:11px;color:#334b66}.cp-vd-assistant-side article p{font-size:10px;color:#718096;line-height:1.5}.cp-vd-smart-guide{padding:12px;background:#f7f9fc}.cp-vd-guide-summary{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;padding:10px}.cp-vd-guide-summary div{display:flex;flex-direction:column;gap:4px;padding:10px;border:1px solid #d5dee8;border-radius:5px;background:#fff}.cp-vd-guide-summary strong{font-size:19px;color:#173d68}.cp-vd-guide-summary span{font-size:10px;color:#718096}.cp-vd-guide-layout{display:grid;grid-template-columns:minmax(0,1fr) 300px;gap:10px}.cp-vd-guide-steps{display:grid;gap:7px}.cp-vd-guide-step{display:grid;grid-template-columns:34px minmax(0,1fr) auto auto;gap:10px;align-items:center;padding:10px;border:1px solid #d5dee8;border-radius:5px;background:#fff}.cp-vd-guide-step>b{display:grid;place-items:center;width:30px;height:30px;border-radius:50%;background:#e8edf4;color:#53677e}.cp-vd-guide-step.is-complete>b{background:#d8efe4;color:#26724e}.cp-vd-guide-step.is-current>b{background:#dce9f7;color:#173d68}.cp-vd-guide-step.is-warning>b{background:#fff0d8;color:#9a5b1d}.cp-vd-guide-step strong{font-size:11px;color:#294765}.cp-vd-guide-step p{margin:4px 0 0;font-size:10px;color:#718096}.cp-vd-guide-step>span{font-size:10px;color:#64748b;white-space:nowrap}.cp-vd-guide-checks{padding:11px;border:1px solid #d5dee8;border-radius:5px;background:#fff}.cp-vd-guide-checks h3{margin:0 0 9px;color:#294765;font-size:12px}.cp-vd-guide-check{display:flex;gap:8px;align-items:center;padding:8px 0;border-bottom:1px solid #edf1f5;font-size:10px;color:#53677e}.cp-vd-guide-check b{font-size:13px}.cp-vd-guide-check.is-pass b{color:#2c8a61}.cp-vd-guide-check.is-warning b{color:#c87935}.cp-vd-guide-check.is-pending b{color:#94a3b8}@media(max-width:900px){.cp-vd-assistant-layout,.cp-vd-guide-layout{grid-template-columns:1fr}.cp-vd-assistant-side{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.cp-vd-assistant-side h3,.cp-vd-assistant-side .cp-vd-hintbox{grid-column:1/-1}}@media(max-width:560px){.cp-vd-guide-summary{grid-template-columns:repeat(2,minmax(0,1fr))}.cp-vd-guide-step{grid-template-columns:30px minmax(0,1fr)}.cp-vd-guide-step>span,.cp-vd-guide-step button{grid-column:2}.cp-vd-assistant-message{max-width:100%}.cp-vd-assistant-side{grid-template-columns:1fr}}
.cp-vd-form-builder-grid{display:grid;grid-template-columns:minmax(170px,19%) minmax(360px,1fr) minmax(220px,26%);min-height:570px;background:#eef2f7}.cp-vd-form-library-tabs{display:flex;gap:5px;padding:8px 12px;border-bottom:1px solid #d4dde7;background:#f4f7fa}.cp-vd-form-library-tabs button{display:flex;align-items:center;gap:10px;border:1px solid #cbd6e2;border-radius:4px;background:#fff;padding:7px 11px;color:#425a73;font-size:11px}.cp-vd-form-library-tabs button.is-active{background:#dce9f7;border-color:#7898bb;color:#173d68;font-weight:700}.cp-vd-form-library-tabs span{border-radius:10px;background:#e8edf4;padding:2px 6px}.cp-vd-form-list{padding:10px;border-inline-end:1px solid #cbd5e1;background:#f6f8fb;min-width:0}.cp-vd-form-list>strong{display:block;margin-bottom:8px;color:#425a73;font-size:12px}.cp-vd-form-list-item{display:flex;flex-direction:column;gap:4px;width:100%;margin-bottom:6px;padding:8px;border:1px solid #d5dee8;border-radius:4px;background:#fff;text-align:start;color:#334b66}.cp-vd-form-list-item span{display:flex;flex-direction:column;gap:3px}.cp-vd-form-list-item strong{font-size:11px}.cp-vd-form-list-item small{font-size:10px;color:#718096}.cp-vd-form-canvas{padding:10px;min-width:0;overflow:auto}.cp-vd-form-canvas-toolbar{display:flex;justify-content:space-between;gap:8px;margin-bottom:8px;color:#53677e;font-size:11px}.cp-vd-form-paper{max-width:760px;min-height:500px;margin:auto;padding:26px;background:#fff;border:1px solid #cbd5e1;box-shadow:0 2px 9px #1e293b12;color:#334155}.cp-vd-form-paper>header{display:flex;gap:18px;align-items:center;border-bottom:2px solid #c87935;padding-bottom:15px}.cp-vd-form-logo{display:grid;place-content:center;min-width:76px;height:64px;border:1px dashed #9aa9ba;color:#173d68;text-align:center;font-weight:800}.cp-vd-form-logo small{font-size:7px}.cp-vd-form-paper h3{margin:0 0 5px;color:#173d68}.cp-vd-form-paper p{margin:3px 0;font-size:10px;color:#64748b}.cp-vd-form-paper section{margin-top:18px;padding:12px;border:1px solid #dce3eb;border-radius:4px}.cp-vd-form-paper h4{margin:0 0 10px;font-size:12px;color:#294765}.cp-vd-form-paper label{display:flex;flex-direction:column;gap:4px;margin:7px 0;font-size:10px;color:#53677e}.cp-vd-form-paper input,.cp-vd-form-paper textarea{width:100%;border:1px solid #d5dee8;border-radius:3px;padding:6px;background:#fbfcfd;font:11px Inter,Vazirmatn,sans-serif}.cp-vd-form-paper-row{display:grid;grid-template-columns:1fr 1fr;gap:10px}.cp-vd-form-paper footer{display:flex;justify-content:space-between;margin-top:18px;padding-top:12px;border-top:1px solid #dce3eb;font-size:10px}.cp-vd-form-properties{background:#f6f8fb;border-inline-start:1px solid #cbd5e1;min-width:0}.cp-vd-form-property-tabs{display:flex;flex-wrap:wrap;gap:2px;padding:6px;border-bottom:1px solid #d5dee8}.cp-vd-form-property-tabs button{border:0;border-bottom:2px solid transparent;background:transparent;padding:6px 7px;font-size:10px;color:#64748b}.cp-vd-form-property-tabs button.is-active{border-color:#c87935;color:#173d68;font-weight:700}.cp-vd-form-property-panel{padding:10px}.cp-vd-form-workflow{list-style:none;padding:0;margin:0;display:grid;gap:8px}.cp-vd-form-workflow li{display:flex;gap:9px;align-items:center;padding:10px;border:1px solid #d5dee8;border-radius:4px;background:#fff}.cp-vd-form-workflow li>b{display:grid;place-items:center;width:24px;height:24px;border-radius:50%;background:#dce9f7;color:#173d68}.cp-vd-form-workflow li span{display:flex;flex-direction:column;gap:3px}.cp-vd-form-workflow small{font-size:10px;color:#718096}@media(max-width:1100px){.cp-vd-form-builder-grid{grid-template-columns:180px minmax(0,1fr)}.cp-vd-form-properties{grid-column:1/-1;border-inline-start:0;border-top:1px solid #cbd5e1}}@media(max-width:700px){.cp-vd-form-builder-grid{grid-template-columns:1fr}.cp-vd-form-list{border-inline-end:0;border-bottom:1px solid #cbd5e1}.cp-vd-form-paper{padding:14px}.cp-vd-form-paper-row{grid-template-columns:1fr}}
.cp-vd-module-overview{display:grid;grid-template-columns:minmax(0,1fr) minmax(190px,27%);gap:10px;padding:10px 12px;border-bottom:1px solid #d8e0e9;background:#f8fafc}.cp-vd-metric-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:7px}.cp-vd-metric-card{display:flex;flex-direction:column;gap:4px;min-width:0;padding:9px;border:1px solid #d9e1ea;border-radius:5px;background:#fff}.cp-vd-metric-card>span{font-size:10px;color:#64748b}.cp-vd-metric-card>strong{font-size:19px;line-height:1.2;color:#1e3d60;overflow-wrap:anywhere}.cp-vd-metric-card>small{font-size:10px;color:#718096}.cp-vd-metric-card>i{height:4px;margin-top:3px;border-radius:5px;background:#e7edf4;overflow:hidden}.cp-vd-metric-card>i>b{display:block;height:100%;background:#376da8}.cp-vd-metric-card.is-orange>i>b{background:#c87935}.cp-vd-metric-card.is-green>i>b{background:#3b8a69}.cp-vd-metric-card.is-red>i>b{background:#c04e4e}.cp-vd-module-chart{display:flex;flex-direction:column;justify-content:center;gap:10px;padding:8px;border:1px solid #d9e1ea;border-radius:5px;background:#fff;min-width:0}.cp-vd-module-chart>strong{font-size:11px;color:#425a73}.cp-vd-module-stack{display:flex;height:12px;overflow:hidden;border-radius:6px;background:#e7edf4}.cp-vd-module-stack span.is-blue,.cp-vd-module-legend i.is-blue{background:#376da8}.cp-vd-module-stack span.is-orange,.cp-vd-module-legend i.is-orange{background:#c87935}.cp-vd-module-stack span.is-green,.cp-vd-module-legend i.is-green{background:#3b8a69}.cp-vd-module-stack span.is-red,.cp-vd-module-legend i.is-red{background:#c04e4e}.cp-vd-module-legend{display:flex;flex-wrap:wrap;gap:6px 10px}.cp-vd-module-legend span{display:flex;align-items:center;gap:4px;font-size:9px;color:#64748b}.cp-vd-module-legend i{width:7px;height:7px;border-radius:2px}@media(max-width:900px){.cp-vd-module-overview{grid-template-columns:1fr}.cp-vd-module-chart{min-height:76px}}@media(max-width:560px){.cp-vd-metric-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
.cp-vd-calendar-hours{width:100%;min-width:145px;border:1px solid #cbd5e1;border-radius:3px;background:#fff;padding:4px 6px;color:#334155;font:11px Inter,Vazirmatn,sans-serif}.cp-vd-calendar-working{display:flex;align-items:center;gap:5px;white-space:nowrap}.cp-vd-calendar-working input{accent-color:#3b8a69}.cp-vd-register-search,.cp-vd-register-sort{display:flex;align-items:center;gap:6px;font-size:11px;color:var(--cp-vd-muted);white-space:nowrap}.cp-vd-register-search input,.cp-vd-register-sort select{min-width:118px;max-width:190px;height:29px;border:1px solid var(--cp-vd-border);border-radius:5px;background:var(--cp-vd-panel);color:var(--cp-vd-text);padding:3px 7px}.cp-vd-register-search input{min-width:170px}.cp-vd-register-count{font-size:11px;font-weight:700;color:var(--cp-vd-muted);white-space:nowrap}.cp-vd-empty-state{text-align:center;padding:28px!important;color:var(--cp-vd-muted)}@media(max-width:760px){.cp-vd-register-search,.cp-vd-register-sort{width:100%;justify-content:space-between}.cp-vd-register-search input,.cp-vd-register-sort select{flex:1;max-width:none}.cp-vd-register-count{margin-inline-start:auto}}</style><div class="cp-vd" data-visual-demo dir="${state.locale.startsWith("fa") ? "rtl" : "ltr"}">
    <div class="cp-vd-titlebar"><strong>CUBI</strong><span>${esc(t(state.locale, "Professional Workspace", "محیط کار حرفه‌ای"))}</span><span class="cp-vd-project">CUBI-DEMO-001 — ${esc(t(state.locale, "Riverside Pump Station Upgrade", "ارتقای ایستگاه پمپ ریورساید"))}</span><span class="cp-vd-demo-badge">${esc(t(state.locale, "Visual demo · sample data", "نمایش بصری · دادهٔ نمونه"))}</span><span class="cp-vd-titlebar-spacer"></span>${renderLanguageSwitch(state)}<button type="button" class="cp-vd-fullscreen" data-vd-fullscreen aria-pressed="${state.fullscreen ? "true" : "false"}" title="${esc(t(state.locale, "Toggle full screen", "تغییر حالت تمام‌صفحه"))}">${esc(state.fullscreen ? t(state.locale, "Return to normal view", "بازگشت به نمای اصلی") : t(state.locale, "Full screen", "تمام‌صفحه"))}</button><button type="button" class="cp-vd-exit" data-vd-action='{"command":"sign-out"}' title="${esc(t(state.locale, "Sign out and return to home page", "خروج از حساب و بازگشت به صفحه اصلی"))}">${esc(t(state.locale, "Sign out", "خروج از حساب"))}</button></div>
    ${renderMenus(state)}
    ${renderToolbars(state)}
    ${renderTabs(state)}
    <div class="cp-vd-layoutbar"><span>${esc(t(state.locale, "Layout", "چیدمان"))}: <strong>CUBI Classic Schedule Layout</strong></span><span>${esc(t(state.locale, "Filter", "فیلتر"))}: <strong>${esc(state.filter || t(state.locale, "All Activities", "همهٔ فعالیت‌ها"))}</strong></span><span class="cp-vd-layoutspacer"></span><button type="button" class="cp-vd-btn" data-vd-dialog="columns">${workspaceIcon("columns")}${esc(t(state.locale, "Columns", "ستون‌ها"))}</button><button type="button" class="cp-vd-btn" data-vd-dialog="filters">${workspaceIcon("filter")}${esc(t(state.locale, "Filters", "فیلترها"))}</button><button type="button" class="cp-vd-btn" data-vd-dialog="group-sort">${workspaceIcon("sort")}${esc(t(state.locale, "Group and Sort", "گروه و ترتیب"))}</button><button type="button" class="cp-vd-btn" data-vd-dialog="timescale">${workspaceIcon("clock")}${esc(t(state.locale, "Timescale", "مقیاس"))}</button><button type="button" class="cp-vd-btn" data-vd-dialog="bars">${workspaceIcon("bars")}${esc(t(state.locale, "Bars", "میله‌ها"))}</button></div>
    <div class="cp-vd-workspace-grid">
      <nav class="cp-vd-left-nav" aria-label="${esc(t(state.locale, "Workspace navigation", "ناوبری محیط کار"))}">
        <section class="cp-vd-nav-group"><div class="cp-vd-nav-heading">${esc(t(state.locale, "Project Workspace", "محیط پروژه"))}</div><div class="cp-vd-nav-group-items"><button type="button" class="cp-vd-nav-link${state.window === "projects" ? " is-active" : ""}" data-vd-window="projects" aria-current="${state.window === "projects" ? "page" : "false"}">${workspaceIcon("project")}<span>${esc(t(state.locale, "Projects", "پروژه‌ها"))}</span></button></div></section>
        ${navGroups.map(navGroup).join("")}
      </nav>
      <main class="cp-vd-main">${renderWindow(state)}</main>
      <aside class="cp-vd-right-rail" aria-label="${esc(t(state.locale, "Context commands", "فرمان‌های زمینه‌ای"))}">
        <button type="button" class="cp-vd-rail-add" data-vd-dialog="module-actions" title="${esc(t(state.locale, "Add item", "افزودن آیتم"))}">＋<span>${esc(t(state.locale, "Add", "افزودن"))}</span></button>
        <button type="button" data-vd-dialog="module-actions" title="${esc(t(state.locale, "Edit selected item", "ویرایش آیتم انتخاب‌شده"))}">✎</button>
        <button type="button" data-vd-dialog="module-actions" title="${esc(t(state.locale, "Assign or link", "تخصیص یا پیوند"))}">↗</button>
        <button type="button" data-vd-window="comments" title="${esc(t(state.locale, "Comments and notes", "دیدگاه‌ها و یادداشت‌ها"))}">▤</button>
        <button type="button" data-vd-dialog="module-actions" title="${esc(t(state.locale, "More commands", "فرمان‌های بیشتر"))}">⋯</button>
      </aside>
    </div>
    <div class="cp-vd-status"><span>${esc(t(state.locale, "Project", "پروژه"))}: CUBI-DEMO-001</span><span>${esc(t(state.locale, "Data date", "تاریخ داده"))}: <bdi dir="ltr">03-Dec-2026</bdi></span><span>${esc(t(state.locale, "Baseline", "خط مبنا"))}: BL-01</span><span>${esc(t(state.locale, "Window", "پنجره"))}: ${esc(label(WINDOWS[index] ?? WINDOWS[0], state.locale))}</span><span class="cp-vd-status-end">${esc(t(state.locale, "Preview data — not saved or calculated", "دادهٔ پیش‌نمایش — ذخیره یا محاسبه نشده"))}</span></div>
    ${renderDialogs(state)}
    <div class="cp-vd-context-menu" data-vd-context-menu hidden role="menu" aria-label="${esc(t(state.locale, "Selection commands", "فرمان‌های انتخاب"))}">
      <div data-vd-context-panel="activity" hidden>
        <strong>${esc(t(state.locale, "Activity", "فعالیت"))}: <bdi data-vd-context-activity></bdi></strong>
        <button type="button" role="menuitem" data-vd-context-action="activity-details">${esc(t(state.locale, "Activity Details…", "جزئیات فعالیت…"))}</button>
        <button type="button" role="menuitem" data-vd-context-action="assign-resources">${esc(t(state.locale, "Assign Resources…", "تخصیص منابع…"))}</button>
        <button type="button" role="menuitem" data-vd-context-action="add-predecessor">${esc(t(state.locale, "Assign Predecessors…", "تخصیص پیش‌نیازها…"))}</button>
        <button type="button" role="menuitem" data-vd-context-action="add-successor">${esc(t(state.locale, "Assign Successors…", "تخصیص جانشین‌ها…"))}</button>
        <button type="button" role="menuitem" data-vd-context-action="activity-codes">${esc(t(state.locale, "Assign Activity Codes…", "تخصیص کدهای فعالیت…"))}</button>
        <hr><button type="button" role="menuitem" disabled>${esc(t(state.locale, "Delete Activity", "حذف فعالیت"))}</button>
      </div>
      <div data-vd-context-panel="wbs" hidden>
        <strong>${esc(t(state.locale, "WBS Element", "عنصر ساختار شکست کار"))}: <bdi data-vd-context-wbs></bdi></strong>
        <button type="button" role="menuitem" data-vd-context-action="wbs-details">${esc(t(state.locale, "WBS Details…", "جزئیات ساختار شکست…"))}</button>
        <button type="button" role="menuitem" data-vd-context-action="wbs-activities">${esc(t(state.locale, "Show Activities", "نمایش فعالیت‌ها"))}</button>
        <button type="button" role="menuitem" data-vd-context-action="wbs-add-child">${esc(t(state.locale, "Add Child WBS…", "افزودن زیرشاخه…"))}</button>
        <hr><button type="button" role="menuitem" disabled>${esc(t(state.locale, "Delete WBS", "حذف ساختار شکست"))}</button>
      </div>
    </div>
  </div>`;
}

export function createVisualDemoState(locale: string): DemoState {
  return {
    window: "activities",
    activityId: "A1320",
    selectedWbsCode: "1",
    wbsDetailTab: "general",
    collapsedWbsCodes: [],
    collapsedNavGroups: [],
    scale: "month",
    activityView: "schedule",
    detailTab: "general",
    moduleDetailTab: "general",
    moduleSelectedRow: 0,
    moduleSearch: "",
    moduleSort: "default",
    moduleSortBy: "",
    moduleColumnWindow: null,
    moduleAvailableColumns: [],
    moduleColumns: [],
    formLibrary: "organization",
    formTab: "design",
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
    fullscreen: false,
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
    const paths = NETWORK_LINKS.map((link) => {
      const start = boxOf(network.querySelector(`[data-vd-node="${link.predecessor}"]`), origin);
      const end = boxOf(network.querySelector(`[data-vd-node="${link.successor}"]`), origin);
      if (!start || !end) return "";
      const critical = Boolean(
        ACTIVITIES.find((item) => item.id === link.predecessor)?.critical && ACTIVITIES.find((item) => item.id === link.successor)?.critical,
      );
      const marker = critical ? "cp-vd-net-arrow-critical" : "cp-vd-net-arrow";
      const label = `${link.type} ${link.lag > 0 ? "+" : ""}${link.lag}${link.unit}`;
      const labelX = (start.left + start.right + end.left + end.right) / 4;
      const labelY = (start.middle + end.middle) / 2 - 7;
      return `<path d="${routeLink(start, end, outward)}" class="${critical ? "is-critical" : ""}" data-link-type="${link.type}" marker-end="url(#${marker})"></path><text class="cp-vd-network-link-label" x="${labelX}" y="${labelY}" text-anchor="middle">${esc(label)}</text>`;
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
  document.addEventListener("fullscreenchange", () => {
    state.fullscreen = document.fullscreenElement === root.querySelector<HTMLElement>("[data-visual-demo]");
    draw();
  });
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
    const groupByWindow: Partial<Record<DemoWindowId, string>> = {
      wbs: "planning", activities: "planning", network: "planning", trace: "planning", timeline: "planning",
      "activity-profile": "planning", "resource-profile": "planning", "activity-sheet": "planning", "resource-sheet": "planning", calendars: "planning",
      assignments: "controls", resources: "controls", roles: "controls", "cost-control": "controls", "progress-control": "controls", procurement: "controls",
      "changes-claims": "controls", tracking: "controls", expenses: "controls", thresholds: "controls", issues: "controls", risks: "controls",
      documents: "information", reports: "information", "form-builder": "information", comments: "information", organization: "information", administration: "information",
      "smart-guide": "information", assistant: "information", search: "information",
    };
    const activeGroup = groupByWindow[id];
    if (activeGroup) state.collapsedNavGroups = state.collapsedNavGroups.filter((group) => group !== activeGroup);
    draw();
  };
  const openDialog = (name: string): void => {
    closeMenus();
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
    if (action.window) { if (action.adminSection && ADMIN_SECTIONS.some(([id]) => id === action.adminSection)) state.adminSection = action.adminSection; navigate(action.window); return; }
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
      case "sign-out": {
        const button = root.querySelector<HTMLButtonElement>('[data-vd-action*="sign-out"]');
        if (button) button.disabled = true;
        void fetch("/preview/logout", {
          method: "POST",
          credentials: "same-origin",
          redirect: "follow",
        }).then((response) => {
          if (!response.ok) throw new Error(`SIGN_OUT_HTTP_${response.status}`);
          // The preview endpoint revokes the session and redirects its fetch to
          // the login screen; the top-level browser then returns to the public home page.
          window.location.assign("/");
        }).catch(() => {
          if (button) button.disabled = false;
          window.alert(t(state.locale, "Sign out failed. Check your connection and try again.", "خروج از حساب انجام نشد. اتصال را بررسی کنید و دوباره تلاش کنید."));
        });
        return;
      }
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

  root.addEventListener("change", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLSelectElement) || !target.matches("[data-vd-locale]")) return;
    const next = target.value;
    const available = getAvailableWorkspaceLocales();
    if ((next !== "en" && next !== "fa") || !available.includes(next)) return;
    state.locale = next;
    rememberWorkspaceLocale(next, available);
    writeStoredValue(LANDING_LOCALE_STORAGE_KEY, next);
    document.documentElement.lang = next;
    document.documentElement.dir = getWorkspaceLocaleDirection(next);
    document.title = next === "fa"
      ? "محیط کار CUBI — نمایش بصری"
      : "CUBI Workspace — visual demo";
    draw();
  });

  root.addEventListener("contextmenu", (event) => {
    const target = event.target as HTMLElement | null;
    if (!target || typeof target.closest !== "function") return;
    const activityRow = target.closest<HTMLElement>("[data-vd-activity]");
    const wbsRow = target.closest<HTMLElement>("[data-vd-wbs]");
    if (!activityRow && !wbsRow) return;
    event.preventDefault();
    if (activityRow?.dataset.vdActivity) state.activityId = activityRow.dataset.vdActivity;
    if (wbsRow?.dataset.vdWbs) state.selectedWbsCode = wbsRow.dataset.vdWbs;
    draw();
    const menu = root.querySelector<HTMLElement>("[data-vd-context-menu]");
    const kind = activityRow ? "activity" : "wbs";
    const panel = menu?.querySelector<HTMLElement>(`[data-vd-context-panel="${kind}"]`);
    if (!menu || !panel) return;
    menu.querySelectorAll<HTMLElement>("[data-vd-context-panel]").forEach((item) => { item.hidden = item !== panel; });
    const id = menu.querySelector<HTMLElement>(activityRow ? "[data-vd-context-activity]" : "[data-vd-context-wbs]");
    if (id) id.textContent = activityRow ? state.activityId : state.selectedWbsCode;
    menu.hidden = false;
    const left = Math.min(event.clientX, Math.max(8, window.innerWidth - menu.offsetWidth - 8));
    const top = Math.min(event.clientY, Math.max(8, window.innerHeight - menu.offsetHeight - 8));
    menu.style.left = `${left}px`;
    menu.style.top = `${top}px`;
  });

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
    const contextAction = target.closest<HTMLElement>("[data-vd-context-action]");
    if (contextAction?.dataset.vdContextAction) {
      const menu = root.querySelector<HTMLElement>("[data-vd-context-menu]");
      if (menu) menu.hidden = true;
      switch (contextAction.dataset.vdContextAction) {
        case "activity-details": state.detailsOpen = true; state.detailTab = "general"; draw(); break;
        case "assign-resources": openDialog("assign-resources"); break;
        case "add-predecessor": openDialog("assign-predecessors"); break;
        case "add-successor": openDialog("assign-successors"); break;
        case "activity-codes": openDialog("assign-activity-codes"); break;
        case "wbs-details": state.wbsDetailTab = "general"; draw(); break;
        case "wbs-activities": navigate("activities"); break;
        case "wbs-add-child": openDialog("new-wbs"); break;
      }
      return;
    }
    const actionTarget = target.closest<HTMLElement>("[data-vd-action]");
    if (actionTarget) {
      closeMenus();
      try { run(JSON.parse(actionTarget.dataset.vdAction ?? "{}") as MenuAction); } catch { /* malformed action */ }
      return;
    }
    const navGroup = target.closest<HTMLElement>("[data-vd-nav-group]");
    if (navGroup?.dataset.vdNavGroup) {
      const id = navGroup.dataset.vdNavGroup;
      state.collapsedNavGroups = state.collapsedNavGroups.includes(id) ? state.collapsedNavGroups.filter((item) => item !== id) : [...state.collapsedNavGroups, id];
      draw();
      return;
    }
    const tab = target.closest<HTMLElement>("[data-vd-window]");
    if (tab?.dataset.vdWindow) { navigate(tab.dataset.vdWindow as DemoWindowId); return; }
    const activityView = target.closest<HTMLElement>("[data-vd-activity-view]");
    if (activityView?.dataset.vdActivityView === "schedule" || activityView?.dataset.vdActivityView === "relationships") {
      state.activityView = activityView.dataset.vdActivityView;
      draw();
      return;
    }
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
    const formLibrary = target.closest<HTMLElement>("[data-vd-form-library]");
    if (formLibrary?.dataset.vdFormLibrary === "organization" || formLibrary?.dataset.vdFormLibrary === "project") {
      state.formLibrary = formLibrary.dataset.vdFormLibrary;
      draw();
      return;
    }
    const formTab = target.closest<HTMLElement>("[data-vd-form-tab]");
    if (formTab?.dataset.vdFormTab && ["design", "fields", "workflow", "permissions", "versions"].includes(formTab.dataset.vdFormTab)) {
      state.formTab = formTab.dataset.vdFormTab as DemoState["formTab"];
      draw();
      return;
    }
    const moduleTab = target.closest<HTMLElement>("[data-vd-module-tab]");
    if (moduleTab?.dataset.vdModuleTab) {
      state.moduleDetailTab = moduleTab.dataset.vdModuleTab as DemoState["moduleDetailTab"];
      draw();
      return;
    }
    const moduleRow = target.closest<HTMLElement>("[data-vd-module-row]");
    if (moduleRow?.dataset.vdModuleRow !== undefined) {
      state.moduleSelectedRow = Number(moduleRow.dataset.vdModuleRow);
      state.moduleDetailTab = "general";
      draw();
      return;
    }
    const adminSection = target.closest<HTMLElement>("[data-vd-admin]");
    if (adminSection?.dataset.vdAdmin) { state.adminSection = adminSection.dataset.vdAdmin; draw(); return; }
    const wbsToggle = target.closest<HTMLElement>("[data-vd-wbs-toggle]");
    if (wbsToggle?.dataset.vdWbsToggle) {
      const code = wbsToggle.dataset.vdWbsToggle;
      state.collapsedWbsCodes = state.collapsedWbsCodes.includes(code)
        ? state.collapsedWbsCodes.filter((item) => item !== code)
        : [...state.collapsedWbsCodes, code];
      draw();
      return;
    }
    const wbsRow = target.closest<HTMLElement>("[data-vd-wbs]");
    if (wbsRow?.dataset.vdWbs) {
      state.selectedWbsCode = wbsRow.dataset.vdWbs;
      draw();
      return;
    }
    const wbsDetailTab = target.closest<HTMLElement>("[data-vd-wbs-dtab]");
    if (wbsDetailTab?.dataset.vdWbsDtab) {
      state.wbsDetailTab = wbsDetailTab.dataset.vdWbsDtab as DemoState["wbsDetailTab"];
      draw();
      return;
    }
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
    const fullscreen = target.closest<HTMLElement>("[data-vd-fullscreen]");
    if (fullscreen) {
      const surface = root.querySelector<HTMLElement>("[data-visual-demo]");
      if (!surface) return;
      if (document.fullscreenElement === surface) {
        void document.exitFullscreen().catch(() => undefined);
      } else if (typeof surface.requestFullscreen === "function") {
        void surface.requestFullscreen().catch(() => {
          state.fullscreen = false;
          draw();
          window.alert(t(state.locale, "Full screen is not available in this browser.", "حالت تمام‌صفحه در این مرورگر در دسترس نیست."));
        });
      }
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
    if (!target.closest("[data-vd-context-menu]")) { const contextMenu = root.querySelector<HTMLElement>("[data-vd-context-menu]"); if (contextMenu) contextMenu.hidden = true; }
  });

  root.addEventListener("submit", (event) => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement) || !form.dataset.vdForm) return;
    event.preventDefault();
    const name = form.dataset.vdForm;
    const data = new FormData(form);
    if (name === "columns") {
      if (state.window === "activities") {
        state.columns = ACTIVITY_COLUMNS.filter((column) => data.has(column.id)).map((column) => column.id);
        if (!state.columns.length) state.columns = [...DEFAULT_COLUMNS];
      } else {
        state.moduleColumns = state.moduleAvailableColumns.filter((column) => data.has(column));
        if (!state.moduleColumns.length) state.moduleColumns = [...state.moduleAvailableColumns];
      }
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

  root.addEventListener("input", (event) => {
    const target = event.target;
    if (target instanceof HTMLInputElement && target.matches("[data-vd-module-search]")) {
      state.moduleSearch = target.value;
      const selection = root.querySelector<HTMLElement>("[data-vd-module-row].is-selected");
      if (selection && !selection.isConnected) state.moduleSelectedRow = 0;
      const active = document.activeElement === target;
      const start = target.selectionStart;
      const end = target.selectionEnd;
      draw();
      if (active) {
        const replacement = root.querySelector<HTMLInputElement>("[data-vd-module-search]");
        replacement?.focus();
        if (start !== null && end !== null) replacement?.setSelectionRange(start, end);
      }
    }
  });

  root.addEventListener("change", (event) => {
    const target = event.target as HTMLElement | null;
    if (target instanceof HTMLSelectElement && target.matches("[data-vd-module-sort-field]")) {
      state.moduleSortBy = state.moduleAvailableColumns.includes(target.value) ? target.value : (state.moduleAvailableColumns[0] ?? "");
      draw();
      return;
    }
    if (target instanceof HTMLSelectElement && target.matches("[data-vd-module-sort]")) {
      const next = target.value;
      if (next === "default" || next === "ascending" || next === "descending") {
        state.moduleSort = next;
        draw();
      }
      return;
    }
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
