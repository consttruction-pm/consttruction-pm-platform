import type { ProjectContext } from "./client.js";
import type { ApiTransport } from "./client.js";
import type { P6Field } from "./p6-field-layout-foundation.js";
import { createP6FormulaAuthority } from "./p6-formula-api.js";
import { createP6FormulaEditor } from "./p6-formula-editor.js";
import {
  getP6FormulaEditorPresentation,
  type P6FormulaEditorPresentation,
} from "./p6-formula-editor-view.js";

export type FormulaPanelLabels = {
  title: string;
  intro: string;
  field: string;
  expression: string;
  expressionPlaceholder: string;
  validate: string;
  validating: string;
  idle: string;
  valid: string;
  invalid: string;
  validationError: string;
  dependencies: string;
  resultType: string;
  none: string;
  noFields: string;
};

const LABELS: Record<"en" | "fa", FormulaPanelLabels> = {
  en: {
    title: "Formula editor",
    intro:
      "Validate an expression against the shared calculation core. Validation is read-only: it does not save, recalculate or change activity dates.",
    field: "Context field",
    expression: "Expression",
    expressionPlaceholder: "Example: [activity.duration_percent_complete] / 100",
    validate: "Validate",
    validating: "Validating with the shared calculation core…",
    idle: "Enter an expression and validate it to see the authoritative result.",
    valid: "Valid expression",
    invalid: "Expression is not valid",
    validationError: "Validation could not be completed",
    dependencies: "Referenced fields",
    resultType: "Result type",
    none: "None",
    noFields: "No registered fields are available for formula validation.",
  },
  fa: {
    title: "ویرایشگر فرمول",
    intro:
      "عبارت را با هستهٔ محاسباتی مشترک اعتبارسنجی کنید. اعتبارسنجی فقط خواندنی است: ذخیره، محاسبهٔ مجدد یا تغییر تاریخ فعالیت انجام نمی‌دهد.",
    field: "فیلد زمینه",
    expression: "عبارت",
    expressionPlaceholder: "مثال: [activity.duration_percent_complete] / 100",
    validate: "اعتبارسنجی",
    validating: "در حال اعتبارسنجی با هستهٔ محاسباتی مشترک…",
    idle: "عبارت را وارد و اعتبارسنجی کنید تا نتیجهٔ مرجع نمایش داده شود.",
    valid: "عبارت معتبر است",
    invalid: "عبارت معتبر نیست",
    validationError: "اعتبارسنجی کامل نشد",
    dependencies: "فیلدهای ارجاع‌شده",
    resultType: "نوع نتیجه",
    none: "هیچ",
    noFields: "هیچ فیلد ثبت‌شده‌ای برای اعتبارسنجی فرمول در دسترس نیست.",
  },
};

export function getFormulaPanelLabels(locale: string): FormulaPanelLabels {
  return locale.toLowerCase().startsWith("fa") ? LABELS.fa : LABELS.en;
}

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

export function renderFormulaEditorForm(
  fields: readonly P6Field[],
  labels: FormulaPanelLabels,
): string {
  if (fields.length === 0) {
    return `<p class="cp-empty" role="status">${escapeHtml(labels.noFields)}</p>`;
  }
  const options = fields
    .map(
      (field) =>
        `<option value="${escapeHtml(field.field_id)}">${escapeHtml(
          field.display_name || field.field_id,
        )} — ${escapeHtml(field.field_id)}</option>`,
    )
    .join("");
  return `<p>${escapeHtml(labels.intro)}</p>
    <form class="cp-formula-form" data-formula-form>
      <label>${escapeHtml(labels.field)}
        <select name="context_field_id" data-formula-field>${options}</select>
      </label>
      <label>${escapeHtml(labels.expression)}
        <textarea name="expression" data-formula-expression rows="3" spellcheck="false" placeholder="${escapeHtml(
          labels.expressionPlaceholder,
        )}"></textarea>
      </label>
      <button type="submit" data-formula-validate>${escapeHtml(labels.validate)}</button>
    </form>
    <p data-formula-status role="status">${escapeHtml(labels.idle)}</p>
    <div data-formula-result></div>`;
}

export function renderFormulaAuthoritativeResult(
  presentation: P6FormulaEditorPresentation,
  fieldId: string,
  labels: FormulaPanelLabels,
): string {
  if (presentation.validating) {
    return `<p role="status">${escapeHtml(labels.validating)}</p>`;
  }
  const validation = presentation.validation;
  if (!validation) {
    return `<p role="status">${escapeHtml(labels.idle)}</p>`;
  }
  if (!validation.valid) {
    const code = validation.error_code ?? "FORMULA_INVALID";
    return `<div role="alert" class="cp-formula-invalid">
      <strong>${escapeHtml(labels.invalid)}</strong>
      <p><code>${escapeHtml(code)}</code></p>
    </div>`;
  }
  const dependencies = presentation.dependencyFieldIds.length
    ? presentation.dependencyFieldIds.map((item) => `<code>${escapeHtml(item)}</code>`).join(", ")
    : escapeHtml(labels.none);
  return `<div class="cp-formula-valid">
    <p role="status"><strong>${escapeHtml(labels.valid)}</strong> <code>${escapeHtml(
      fieldId,
    )}</code></p>
    <p><span>${escapeHtml(labels.dependencies)}</span> ${dependencies}</p>
    <p><span>${escapeHtml(labels.resultType)}</span> <code>${escapeHtml(
      presentation.resultDataType ?? labels.none,
    )}</code></p>
  </div>`;
}

export function mountFormulaEditorPanel(
  workspace: HTMLElement,
  transport: ApiTransport,
  context: ProjectContext,
  locale: string,
  fields: readonly P6Field[],
): void {
  const panel = workspace.querySelector<HTMLElement>(
    "#cp-formula-editor [data-formula-editor]",
  );
  if (!panel) return;
  const labels = getFormulaPanelLabels(locale);
  panel.innerHTML = renderFormulaEditorForm(fields, labels);
  const form = panel.querySelector<HTMLFormElement>("[data-formula-form]");
  if (!form) return;
  const fieldSelect = form.querySelector<HTMLSelectElement>("[data-formula-field]");
  const expression = form.querySelector<HTMLTextAreaElement>(
    "[data-formula-expression]",
  );
  const submit = form.querySelector<HTMLButtonElement>("[data-formula-validate]");
  const status = panel.querySelector<HTMLElement>("[data-formula-status]");
  const result = panel.querySelector<HTMLElement>("[data-formula-result]");
  if (!fieldSelect || !expression || !submit || !status || !result) return;

  const authority = createP6FormulaAuthority(transport, context);
  let editor = createP6FormulaEditor(fieldSelect.value, authority, expression.value);

  const reset = () => {
    status.textContent = labels.idle;
    result.innerHTML = "";
  };
  fieldSelect.addEventListener("change", () => {
    editor = createP6FormulaEditor(fieldSelect.value, authority, expression.value);
    reset();
  });
  expression.addEventListener("input", () => {
    editor.setExpression(expression.value);
    reset();
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    editor.setExpression(expression.value);
    submit.disabled = true;
    status.textContent = labels.validating;
    result.innerHTML = "";
    try {
      const state = await editor.validate();
      const presentation = getP6FormulaEditorPresentation(state);
      result.innerHTML = renderFormulaAuthoritativeResult(
        presentation,
        fieldSelect.value,
        labels,
      );
      const validation = presentation.validation;
      status.textContent = validation?.valid
        ? labels.valid
        : labels.invalid;
    } catch (error) {
      const code = error instanceof Error ? error.message : String(error);
      status.textContent = labels.validationError;
      result.innerHTML = `<div role="alert" class="cp-formula-invalid"><strong>${escapeHtml(
        labels.validationError,
      )}</strong><p><code>${escapeHtml(code)}</code></p></div>`;
    } finally {
      submit.disabled = false;
    }
  });
}
