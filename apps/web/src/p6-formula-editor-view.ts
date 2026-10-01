import type { P6FormulaEditorState } from "./p6-formula-editor.js";

export type P6FormulaEditorViewLabels = {
  title: string;
  expression: string;
  validating: string;
  valid: string;
  invalid: string;
  dependencies: string;
  resultType: string;
};

export function renderP6FormulaEditor(
  state: P6FormulaEditorState,
  labels: P6FormulaEditorViewLabels,
): string {
  const validation = state.authoritative?.validation ?? null;
  const status = state.validating
    ? labels.validating
    : validation
      ? validation.valid ? labels.valid : labels.invalid
      : "";

  const dependencies = state.authoritative?.dependencies.field_ids ?? [];
  const resultType = state.authoritative?.result_type.data_type ?? "";

  return `<section class="cp-p6-formula-editor" aria-label="${escapeAttribute(labels.title)}">
    <h3>${escapeHtml(labels.title)}</h3>
    <label>
      <span>${escapeHtml(labels.expression)}</span>
      <textarea data-p6-formula-expression aria-describedby="p6-formula-status">${escapeHtml(state.expression)}</textarea>
    </label>
    <div id="p6-formula-status" role="status" aria-live="polite">${escapeHtml(status)}</div>
    ${validation && !validation.valid && validation.error_code
      ? `<div data-p6-formula-error="${escapeAttribute(validation.error_code)}">${escapeHtml(validation.message_key ?? validation.error_code)}</div>`
      : ""}
    <dl>
      <dt>${escapeHtml(labels.dependencies)}</dt>
      <dd data-p6-formula-dependencies>${escapeHtml(dependencies.join(", "))}</dd>
      <dt>${escapeHtml(labels.resultType)}</dt>
      <dd data-p6-formula-result-type>${escapeHtml(resultType)}</dd>
    </dl>
  </section>`;
}

function escapeHtml(value: string): string {
  return value.replace(/[&<>"']/g, (character) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[character]!));
}

function escapeAttribute(value: string): string {
  return escapeHtml(value);
}
