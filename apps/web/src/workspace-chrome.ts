/**
 * Visible desktop chrome around the workspace: the product title bar, the
 * layout options bar and the status bar. Values come from the session; nothing
 * is invented here. Dialogs for layout options live in `workspace-dialogs.ts`.
 */
import { workspaceIcon } from "./workspace-icons.js";

export type ChromeProjectContext = {
  name: string;
  dataDate: string;
  baseline: string;
  user: string;
  database: string;
  layout: string;
  filter: string;
};

export type ChromeLayoutState = {
  groupBy: "wbs" | "none";
  ganttScale: "day" | "week" | "month" | "quarter" | "year";
  showRelationships: boolean;
  density: "compact" | "comfortable";
};

export type ChromeState = {
  locale: string;
  project?: ChromeProjectContext;
  layout?: ChromeLayoutState;
  activeWindowTitle: string;
  openWindowCount: number;
};

const L = {
  product: { en: "CUBI", fa: "کوبی" },
  productLine: { en: "Professional Workspace", fa: "محیط کار حرفه‌ای" },
  layout: { en: "Layout", fa: "چیدمان" },
  filter: { en: "Filter", fa: "فیلتر" },
  columns: { en: "Columns", fa: "ستون‌ها" },
  filters: { en: "Filters", fa: "فیلترها" },
  groupSort: { en: "Group and Sort", fa: "گروه‌بندی و ترتیب" },
  timescale: { en: "Timescale", fa: "مقیاس زمانی" },
  bars: { en: "Bars", fa: "میله‌ها" },
  fontRow: { en: "Font and Row", fa: "قلم و ردیف" },
  project: { en: "Project", fa: "پروژه" },
  dataDate: { en: "Data Date", fa: "تاریخ داده" },
  baseline: { en: "Baseline", fa: "خط مبنا" },
  user: { en: "User", fa: "کاربر" },
  database: { en: "Database", fa: "پایگاه داده" },
  windows: { en: "open windows", fa: "پنجرهٔ باز" },
  preview: { en: "Preview data", fa: "دادهٔ پیش‌نمایش" },
};

function fa(locale: string): boolean {
  return locale.split("-")[0] === "fa";
}

function pick(label: { en: string; fa: string }, locale: string): string {
  return fa(locale) ? label.fa : label.en;
}

function esc(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

export function renderTitleBar(state: ChromeState): string {
  const locale = state.locale;
  const projectName = state.project?.name ?? "";
  const subtitle = [state.activeWindowTitle, projectName].filter(Boolean).join(" — ");
  return `<div class="cp-titlebar" data-titlebar>
    <span class="cp-titlebar-brand"><span class="cp-titlebar-mark">C</span><strong>${esc(pick(L.product, locale))}</strong><span class="cp-titlebar-product">${esc(pick(L.productLine, locale))}</span></span>
    <span class="cp-titlebar-context" title="${esc(subtitle)}">${esc(subtitle)}</span>
    <span class="cp-titlebar-preview" title="${esc(pick(L.preview, locale))}">${esc(pick(L.preview, locale))}</span>
  </div>`;
}

function layoutButton(command: string, icon: string, label: string): string {
  return `<button type="button" class="cp-layoutbar-button" data-desktop-command="${esc(command)}">${workspaceIcon(icon)}<span>${esc(label)}</span></button>`;
}

export function renderLayoutBar(state: ChromeState): string {
  const locale = state.locale;
  const layoutName = state.project?.layout ?? "";
  const filterName = state.project?.filter ?? "";
  return `<div class="cp-layoutbar" data-layoutbar>
    <span class="cp-layoutbar-field"><span class="cp-layoutbar-key">${esc(pick(L.layout, locale))}:</span><strong>${esc(layoutName)}</strong></span>
    <span class="cp-layoutbar-field"><span class="cp-layoutbar-key">${esc(pick(L.filter, locale))}:</span><strong>${esc(filterName)}</strong></span>
    <span class="cp-layoutbar-spacer"></span>
    ${layoutButton("view.columns", "columns", pick(L.columns, locale))}
    ${layoutButton("edit.find", "filter", pick(L.filters, locale))}
    ${layoutButton("dialog.group-sort", "sort", pick(L.groupSort, locale))}
    ${layoutButton("dialog.timescale", "clock", pick(L.timescale, locale))}
    ${layoutButton("dialog.bars", "bars", pick(L.bars, locale))}
    ${layoutButton("dialog.font-row", "table", pick(L.fontRow, locale))}
  </div>`;
}

export function renderStatusBar(state: ChromeState): string {
  const locale = state.locale;
  const project = state.project;
  const cells: Array<[string, string]> = [
    [pick(L.project, locale), project?.name ?? "—"],
    [pick(L.dataDate, locale), project?.dataDate ?? "—"],
    [pick(L.baseline, locale), project?.baseline ?? "—"],
    [pick(L.user, locale), project?.user ?? "—"],
    [pick(L.database, locale), project?.database ?? "—"],
  ];
  return `<div class="cp-statusbar" data-statusbar>
    ${cells.map(([key, value]) => `<span class="cp-statusbar-cell"><span class="cp-statusbar-key">${esc(key)}:</span> <span>${esc(value)}</span></span>`).join("")}
    <span class="cp-statusbar-cell cp-statusbar-end"><span>${state.openWindowCount} ${esc(pick(L.windows, locale))}</span></span>
  </div>`;
}
