import type { ProjectContext } from "./client.js";
import type { ApiTransport } from "./client.js";
import type { P6Field } from "./p6-field-layout-foundation.js";
import {
  createP6FormulaAuthority,
  createP6FormulaColumnClient,
  type P6FormulaColumnRecord,
} from "./p6-formula-api.js";
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
  saveSection: string;
  saveTitle: string;
  saveId: string;
  saveIdPlaceholder: string;
  save: string;
  saving: string;
  saved: string;
  saveError: string;
  existing: string;
  noExisting: string;
  listError: string;
};

const LABELS: Record<"en" | "fa", FormulaPanelLabels> = {
  en: {
    title: "Formula editor",
    intro:
      "Validate an expression against the shared calculation core, then save it as a computed Activity column. The server evaluates the column; the grid never evaluates an expression in the browser.",
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
    saveSection: "Save as an activity column",
    saveTitle: "Column title",
    saveId: "Formula column ID",
    saveIdPlaceholder: "formula.my_column",
    save: "Save formula column",
    saving: "Saving through the shared formula service…",
    saved: "Formula column saved. The activity grid shows server-evaluated values.",
    saveError: "The formula column could not be saved",
    existing: "Saved formula columns",
    noExisting: "No formula columns are saved for this project.",
    listError: "Saved formula columns could not be loaded",
  },
  fa: {
    title: "ویرایشگر فرمول",
    intro:
      "عبارت را با هستهٔ محاسباتی مشترک اعتبارسنجی کنید، سپس آن را به‌عنوان ستون محاسبه‌شدهٔ فعالیت ذخیره کنید. مقدار ستون فقط در سرور محاسبه می‌شود و جدول هیچ عبارتی را در مرورگر ارزیابی نمی‌کند.",
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
    saveSection: "ذخیره به‌عنوان ستون فعالیت",
    saveTitle: "عنوان ستون",
    saveId: "شناسهٔ ستون فرمول",
    saveIdPlaceholder: "formula.my_column",
    save: "ذخیرهٔ ستون فرمول",
    saving: "در حال ذخیره با سرویس مشترک فرمول…",
    saved: "ستون فرمول ذخیره شد. جدول فعالیت مقادیر محاسبه‌شدهٔ سرور را نمایش می‌دهد.",
    saveError: "ستون فرمول ذخیره نشد",
    existing: "ستون‌های فرمول ذخیره‌شده",
    noExisting: "هیچ ستون فرمولی برای این پروژه ذخیره نشده است.",
    listError: "ستون‌های فرمول ذخیره‌شده بارگذاری نشد",
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
    <div data-formula-result></div>
    <section class="cp-formula-save-section">
      <h4>${escapeHtml(labels.saveSection)}</h4>
      <form class="cp-formula-save-form" data-formula-save-form>
        <label>${escapeHtml(labels.saveTitle)}
          <input name="title" data-formula-title maxlength="120" autocomplete="off" required>
        </label>
        <label>${escapeHtml(labels.saveId)}
          <input name="formula_id" data-formula-id placeholder="${escapeHtml(
            labels.saveIdPlaceholder,
          )}" autocomplete="off" required>
        </label>
        <button type="submit" data-formula-save>${escapeHtml(labels.save)}</button>
      </form>
    </section>
    <section class="cp-formula-saved-list">
      <h5>${escapeHtml(labels.existing)}</h5>
      <ul data-formula-columns>${renderFormulaColumnList([], labels)}</ul>
    </section>`;
}

export function renderFormulaColumnList(
  records: readonly P6FormulaColumnRecord[],
  labels: FormulaPanelLabels,
): string {
  if (records.length === 0) {
    return `<li class="cp-empty">${escapeHtml(labels.noExisting)}</li>`;
  }
  return records
    .map((record) => {
      const formula = record.formula;
      return `<li data-formula-column="${escapeHtml(formula.formula_id)}">
        <strong>${escapeHtml(formula.title)}</strong>
        <code>${escapeHtml(formula.formula_id)}</code>
        <span>${escapeHtml(formula.data_type)}</span>
        <code>${escapeHtml(formula.expression)}</code>
      </li>`;
    })
    .join("");
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

export type FormulaPanelOptions = {
  /**
   * Called after the server persisted the formula column. The host adds the
   * projected field to the saved activity layout and refreshes the workspace
   * read so the grid shows server-evaluated cells.
   */
  onCreated?: (record: P6FormulaColumnRecord) => Promise<void> | void;
};

export function mountFormulaEditorPanel(
  workspace: HTMLElement,
  transport: ApiTransport,
  context: ProjectContext,
  locale: string,
  fields: readonly P6Field[],
  options: FormulaPanelOptions = {},
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
  const columns = createP6FormulaColumnClient(transport, context);
  let editor = createP6FormulaEditor(fieldSelect.value, authority, expression.value);

  const showError = (message: string, code: string): void => {
    status.textContent = message;
    result.innerHTML = `<div role="alert" class="cp-formula-invalid"><strong>${escapeHtml(
      message,
    )}</strong><p><code>${escapeHtml(code)}</code></p></div>`;
  };

  const listHost = panel.querySelector<HTMLElement>("[data-formula-columns]");
  const refreshColumns = async (): Promise<void> => {
    if (!listHost) return;
    try {
      listHost.innerHTML = renderFormulaColumnList(await columns.list(), labels);
    } catch (error) {
      const code = error instanceof Error ? error.message : String(error);
      listHost.innerHTML = `<li role="alert">${escapeHtml(labels.listError)} <code>${escapeHtml(
        code,
      )}</code></li>`;
    }
  };
  void refreshColumns();

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

  const saveForm = panel.querySelector<HTMLFormElement>("[data-formula-save-form]");
  const titleInput = panel.querySelector<HTMLInputElement>("[data-formula-title]");
  const idInput = panel.querySelector<HTMLInputElement>("[data-formula-id]");
  const saveButton = panel.querySelector<HTMLButtonElement>("[data-formula-save]");
  if (!saveForm || !titleInput || !idInput || !saveButton) return;

  saveForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    saveButton.disabled = true;
    status.textContent = labels.saving;
    result.innerHTML = "";
    try {
      // Saving is gated by the authoritative validator so a broken expression
      // is never persisted as a column.
      editor.setExpression(expression.value);
      const validationState = await editor.validate();
      const presentation = getP6FormulaEditorPresentation(validationState);
      result.innerHTML = renderFormulaAuthoritativeResult(
        presentation,
        fieldSelect.value,
        labels,
      );
      if (!presentation.validation?.valid) {
        status.textContent = labels.invalid;
        return;
      }
      const record = await columns.create({
        formula_id: idInput.value.trim(),
        title: titleInput.value.trim(),
        expression: expression.value,
      });
      status.textContent = labels.saved;
      await refreshColumns();
      if (options.onCreated) await options.onCreated(record);
    } catch (error) {
      const code = error instanceof Error ? error.message : String(error);
      showError(labels.saveError, code);
    } finally {
      saveButton.disabled = false;
    }
  });
}
