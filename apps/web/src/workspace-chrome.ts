/**
 * Compact desktop chrome around the workspace. Heights are fixed by the P6
 * desktop contract: title 23px, layout/filter bar 20px and status bar 14px.
 * Values come from the session; nothing is invented here.
 */
import { workspaceIcon } from "./workspace-icons.js";
import {
  getAvailableWorkspaceLocales,
  getWorkspaceLocaleDisplayName,
  translateWorkspaceUiText,
} from "./workspace-localization.js";

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
  productLine: { en: "Project Management", fa: "مدیریت پروژه" },
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
  ready: { en: "Ready", fa: "آماده" },
  home: { en: "Home", fa: "خانه" },
  homeTitle: { en: "Return to home page", fa: "بازگشت به صفحهٔ خانه" },
  language: { en: "Language", fa: "زبان" },
  languageTitle: { en: "Select workspace language", fa: "انتخاب زبان محیط کار" },
};

function pick(label: { en: string; fa: string }, locale: string): string {
  return translateWorkspaceUiText(locale, label.en, label.fa);
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
  const homeLabel = pick(L.home, locale);
  const languageLabel = pick(L.language, locale);
  const languages = getAvailableWorkspaceLocales();
  return `<div class="cp-titlebar" data-titlebar>
    <span class="cp-titlebar-brand"><span class="cp-titlebar-mark">C</span><strong>${esc(pick(L.product, locale))}</strong><span class="cp-titlebar-product">${esc(pick(L.productLine, locale))}</span></span>
    <span class="cp-titlebar-context" title="${esc(subtitle)}">${esc(subtitle)}</span>
    <span class="cp-titlebar-spacer"></span>
    <button type="button" class="cp-titlebar-action" data-workspace-home title="${esc(pick(L.homeTitle, locale))}" aria-label="${esc(pick(L.homeTitle, locale))}">${workspaceIcon("home")}<span>${esc(homeLabel)}</span></button>
    <label class="cp-titlebar-language" title="${esc(pick(L.languageTitle, locale))}">
      <span class="cp-titlebar-language-mark" aria-hidden="true">${workspaceIcon("language")}</span>
      <span class="cp-titlebar-language-name">${esc(languageLabel)}</span>
      <select data-workspace-language aria-label="${esc(pick(L.languageTitle, locale))}">
        ${languages.map((candidate) => `<option value="${esc(candidate)}"${candidate === locale ? " selected" : ""}>${esc(getWorkspaceLocaleDisplayName(candidate))}</option>`).join("")}
      </select>
    </label>
    <span class="cp-titlebar-session" data-titlebar-session>${esc(projectName || "—")}</span>
  </div>`;
}

function layoutButton(command: string, icon: string, label: string): string {
  return `<button type="button" class="cp-layoutbar-button" data-desktop-command="${esc(command)}" title="${esc(label)}">${workspaceIcon(icon)}<span>${esc(label)}</span></button>`;
}

export function renderLayoutBar(state: ChromeState): string {
  const locale = state.locale;
  const layoutName = state.project?.layout ?? "";
  const filterName = state.project?.filter ?? "";
  return `<div class="cp-layoutbar" data-layoutbar>
    <span class="cp-layoutbar-field"><span class="cp-layoutbar-key">${esc(pick(L.layout, locale))}:</span><strong>${esc(layoutName)}</strong></span>
    <span class="cp-layoutbar-field"><span class="cp-layoutbar-key">${esc(pick(L.filter, locale))}:</span><strong>${esc(filterName)}</strong></span>
    <span class="cp-layoutbar-spacer"></span>
    ${layoutButton("view.fields", "columns", pick(L.columns, locale))}
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
    <span class="cp-statusbar-cell cp-statusbar-end">${esc(pick(L.ready, locale))} · ${state.openWindowCount} ${esc(pick(L.windows, locale))}</span>
  </div>`;
}
