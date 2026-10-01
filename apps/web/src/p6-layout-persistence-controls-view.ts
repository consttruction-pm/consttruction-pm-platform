import type { LayoutScope } from "./p6-field-layout-foundation.js";

export type P6LayoutPersistenceControlsLabels = {
  title: string;
  load: string;
  save: string;
  scope: string;
};

export function renderP6LayoutPersistenceControls(
  scope: LayoutScope,
  labels: P6LayoutPersistenceControlsLabels,
): string {
  return `<section class="cp-p6-layout-persistence" aria-label="${escapeHtml(labels.title)}">
    <div class="cp-p6-layout-persistence-heading">
      <strong>${escapeHtml(labels.title)}</strong>
      <span>${escapeHtml(labels.scope)}: ${escapeHtml(scope)}</span>
    </div>
    <div class="cp-p6-layout-persistence-actions">
      <button type="button" data-p6-layout-load>${escapeHtml(labels.load)}</button>
      <button type="button" data-p6-layout-save>${escapeHtml(labels.save)}</button>
    </div>
  </section>`;
}

function escapeHtml(value: string): string {
  return value.replace(/[&<>"']/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[character] ?? character);
}
