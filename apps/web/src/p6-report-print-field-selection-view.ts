import type { LayoutDefinition, P6Field } from "./p6-field-layout-foundation.js";
import type { P6ReportPrintSelection } from "./p6-report-print-field-selection.js";

export type P6ReportPrintFieldSelectionLabels = {
  title: string;
  selected: string;
  visible: string;
  reset: string;
};

export function renderP6ReportPrintFieldSelection(
  layout: LayoutDefinition,
  fields: readonly P6Field[],
  selection: P6ReportPrintSelection,
  labels: P6ReportPrintFieldSelectionLabels,
): string {
  const selected = new Set(selection.field_ids);
  const ordered = [...layout.columns].sort((a, b) => a.order - b.order);
  const items = ordered.map((column) => {
    const field = fields.find((candidate) => candidate.field_id === column.field_id);
    if (!field) return "";
    return `<label><input type="checkbox" data-p6-report-field-id="${escapeAttribute(field.field_id)}"${selected.has(field.field_id) ? " checked" : ""}>${escapeHtml(column.label ?? field.display_name)}</label>`;
  }).join("");
  return `<section class="cp-p6-report-print-fields" aria-label="${escapeAttribute(labels.title)}">
    <h3>${escapeHtml(labels.title)}</h3>
    <div data-p6-report-selected>${escapeHtml(labels.selected)}: ${selection.field_ids.length}</div>
    <div data-p6-report-visible>${escapeHtml(labels.visible)}: ${ordered.filter((column) => column.visible).length}</div>
    <div>${items}</div>
    <button type="button" data-p6-report-reset>${escapeHtml(labels.reset)}</button>
  </section>`;
}

function escapeHtml(value: string): string {
  return value.replace(/[&<>"']/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[character]!));
}
function escapeAttribute(value: string): string { return escapeHtml(value); }
