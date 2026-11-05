/**
 * Layout option dialogs for the Activities window. They edit the same state the
 * inline controls use (grouping, sorting, timescale, relationships) plus two
 * purely visual preferences (row density, bar tone). Every control applies
 * immediately; there is no decorative option without an effect.
 */
import type { ChromeLayoutState } from "./workspace-chrome.js";
import { translateWorkspaceUiText } from "./workspace-localization.js";

export type DesktopSortColumn = { id: string; label: string };

export type DesktopLayoutPatch = {
  groupBy?: "wbs" | "none";
  sortColumnId?: string | null;
  sortDirection?: "asc" | "desc";
  ganttScale?: ChromeLayoutState["ganttScale"];
  showRelationships?: boolean;
  density?: ChromeLayoutState["density"];
  rowHeight?: number;
  fontSize?: number;
  barHeight?: number;
  barTone?: "crimson" | "vermilion" | "amber";
};

export type DialogOptions = {
  locale: string;
  layout: ChromeLayoutState;
  sortColumns: DesktopSortColumn[];
  sortColumnId: string | null;
  sortDirection: "asc" | "desc";
  rowHeight: number;
  fontSize: number;
  barHeight: number;
  barTone: DesktopLayoutPatch["barTone"];
};

function t(locale: string, en: string, persian: string): string {
  return translateWorkspaceUiText(locale, en, persian);
}

function esc(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function buttons(locale: string, includeDefault = false): string {
  return `<div class="cp-dialog-buttons">
    <button type="submit" class="cp-dialog-primary" data-dialog-ok>${esc(t(locale, "OK", "تأیید"))}</button>
    <button type="button" data-dialog-cancel>${esc(t(locale, "Cancel", "لغو"))}</button>
    ${includeDefault ? `<button type="button" data-dialog-default>${esc(t(locale, "Default", "پیش‌فرض"))}</button>` : ""}
    <button type="button" data-dialog-help title="${esc(t(locale, "Keyboard help", "راهنمای کلیدها"))}">${esc(t(locale, "Help", "راهنما"))}</button>
  </div>`;
}

function shell(locale: string, id: string, title: string, body: string, includeDefault = false): string {
  return `<dialog class="cp-desktop-dialog cp-option-dialog" data-desktop-dialog="${id}" aria-labelledby="cp-dialog-${id}-heading">
    <form method="dialog" data-dialog-form="${id}">
      <h2 id="cp-dialog-${id}-heading">${esc(title)}</h2>
      <div class="cp-dialog-body">${body}</div>
      ${buttons(locale, includeDefault)}
    </form>
  </dialog>`;
}

export function renderLayoutDialogs(options: DialogOptions): string {
  const { locale, layout } = options;
  const groupSort = `<fieldset class="cp-dialog-group">
      <legend>${esc(t(locale, "Group by", "گروه‌بندی بر اساس"))}</legend>
      <label class="cp-dialog-row"><span>${esc(t(locale, "Group levels", "سطوح گروه"))}</span>
        <select name="groupBy">
          <option value="wbs"${layout.groupBy === "wbs" ? " selected" : ""}>WBS</option>
          <option value="none"${layout.groupBy === "none" ? " selected" : ""}>${esc(t(locale, "No grouping", "بدون گروه‌بندی"))}</option>
        </select>
      </label>
    </fieldset>
    <fieldset class="cp-dialog-group">
      <legend>${esc(t(locale, "Sort", "ترتیب"))}</legend>
      <label class="cp-dialog-row"><span>${esc(t(locale, "Field", "فیلد"))}</span>
        <select name="sortColumnId">
          <option value=""${options.sortColumnId ? "" : " selected"}>${esc(t(locale, "No sort", "بدون ترتیب"))}</option>
          ${options.sortColumns.map((column) => `<option value="${esc(column.id)}"${options.sortColumnId === column.id ? " selected" : ""}>${esc(column.label)}</option>`).join("")}
        </select>
      </label>
      <div class="cp-dialog-radios" role="radiogroup" aria-label="${esc(t(locale, "Sort order", "جهت ترتیب"))}">
        <label><input type="radio" name="sortDirection" value="asc"${options.sortDirection === "asc" ? " checked" : ""}> ${esc(t(locale, "Ascending", "صعودی"))}</label>
        <label><input type="radio" name="sortDirection" value="desc"${options.sortDirection === "desc" ? " checked" : ""}> ${esc(t(locale, "Descending", "نزولی"))}</label>
      </div>
    </fieldset>`;

  const timescale = `<fieldset class="cp-dialog-group">
      <legend>${esc(t(locale, "Timescale format", "قالب مقیاس زمانی"))}</legend>
      <label class="cp-dialog-row"><span>${esc(t(locale, "Scale", "مقیاس"))}</span>
        <select name="ganttScale">
          ${(["year", "quarter", "month", "week", "day"] as const).map((scale) => `<option value="${scale}"${layout.ganttScale === scale ? " selected" : ""}>${esc(t(locale, scale[0].toUpperCase() + scale.slice(1), { year: "سال", quarter: "فصل", month: "ماه", week: "هفته", day: "روز" }[scale]))}</option>`).join("")}
        </select>
      </label>
      <label class="cp-dialog-check"><input type="checkbox" name="showRelationships"${layout.showRelationships ? " checked" : ""}> ${esc(t(locale, "Show relationship lines", "نمایش خطوط روابط"))}</label>
    </fieldset>`;

  const bars = `<fieldset class="cp-dialog-group">
      <legend>${esc(t(locale, "Bar chart", "نمودار میله‌ای"))}</legend>
      <label class="cp-dialog-row"><span>${esc(t(locale, "Bar height", "ارتفاع میله"))}</span>
        <input type="range" name="barHeight" min="12" max="24" step="2" value="${options.barHeight}">
      </label>
      <label class="cp-dialog-row"><span>${esc(t(locale, "Critical tone", "رنگ مسیر بحرانی"))}</span>
        <select name="barTone">
          <option value="crimson"${options.barTone === "crimson" ? " selected" : ""}>Crimson</option>
          <option value="vermilion"${options.barTone === "vermilion" ? " selected" : ""}>Vermilion</option>
          <option value="amber"${options.barTone === "amber" ? " selected" : ""}>Amber</option>
        </select>
      </label>
    </fieldset>`;

  const fontRow = `<fieldset class="cp-dialog-group">
      <legend>${esc(t(locale, "Table font and row", "قلم و ردیف جدول"))}</legend>
      <label class="cp-dialog-row"><span>${esc(t(locale, "Font size", "اندازهٔ قلم"))}</span>
        <select name="fontSize">
          ${[10, 11, 12, 13].map((size) => `<option value="${size}"${options.fontSize === size ? " selected" : ""}>${size} px</option>`).join("")}
        </select>
      </label>
      <label class="cp-dialog-row"><span>${esc(t(locale, "Row height", "ارتفاع ردیف"))}</span>
        <input type="number" name="rowHeight" min="18" max="34" step="1" value="${options.rowHeight}">
      </label>
    </fieldset>`;

  return [
    shell(locale, "group-sort", t(locale, "Group and Sort", "گروه‌بندی و ترتیب"), groupSort, true),
    shell(locale, "timescale", t(locale, "Timescale", "مقیاس زمانی"), timescale),
    shell(locale, "bars", t(locale, "Bars", "میله‌ها"), bars),
    shell(locale, "font-row", t(locale, "Table Font and Row", "قلم و ردیف جدول"), fontRow),
  ].join("");
}

export function readLayoutPatch(form: HTMLFormElement | FormData): DesktopLayoutPatch {
  const data = form instanceof FormData ? form : new FormData(form);
  const patch: DesktopLayoutPatch = {};
  const groupBy = data.get("groupBy");
  if (groupBy === "wbs" || groupBy === "none") patch.groupBy = groupBy;
  if (data.has("sortColumnId")) {
    const value = String(data.get("sortColumnId") ?? "");
    patch.sortColumnId = value || null;
  }
  const direction = data.get("sortDirection");
  if (direction === "asc" || direction === "desc") patch.sortDirection = direction;
  const scale = data.get("ganttScale");
  if (scale === "day" || scale === "week" || scale === "month" || scale === "quarter" || scale === "year") {
    patch.ganttScale = scale;
  }
  if (data.has("showRelationships")) patch.showRelationships = data.get("showRelationships") === "on";
  const density = data.get("density");
  if (density === "compact" || density === "comfortable") patch.density = density;
  const rowHeightValue = data.get("rowHeight");
  const rowHeight = Number(rowHeightValue);
  if (typeof rowHeightValue === "string" && rowHeightValue.trim() !== "" && Number.isFinite(rowHeight)) {
    patch.rowHeight = Math.min(34, Math.max(18, Math.round(rowHeight)));
  }
  const fontSizeValue = data.get("fontSize");
  const fontSize = Number(fontSizeValue);
  if (typeof fontSizeValue === "string" && fontSizeValue.trim() !== "" && Number.isFinite(fontSize)) {
    patch.fontSize = Math.min(13, Math.max(10, Math.round(fontSize)));
  }
  const heightValue = data.get("barHeight");
  const height = Number(heightValue);
  if (typeof heightValue === "string" && heightValue.trim() !== "" && Number.isFinite(height)) {
    patch.barHeight = Math.min(24, Math.max(12, height));
  }
  const tone = data.get("barTone");
  if (tone === "crimson" || tone === "vermilion" || tone === "amber") patch.barTone = tone;
  return patch;
}

export function defaultLayoutPatch(): DesktopLayoutPatch {
  return { groupBy: "wbs", sortColumnId: "wbs", sortDirection: "asc", ganttScale: "day", showRelationships: true, density: "compact", rowHeight: 22, fontSize: 11, barHeight: 16, barTone: "crimson" };
}
