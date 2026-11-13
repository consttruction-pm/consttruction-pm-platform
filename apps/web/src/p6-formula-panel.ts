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
  readonlyReason: string;
  dataType: string;
  unit: string;
  version: string;
  apply: string;
  applyHint: string;
  inLayout: string;
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
    readonlyReason:
      "This session can read formula columns but not save them. A planner or project administrator role is required to create or change a formula column.",
    dataType: "Data type",
    unit: "Result unit",
    version: "Definition version",
    apply: "Show in grid",
    applyHint:
      "Adds the saved formula column to the activity layout. Values come from the server's next workspace read.",
    inLayout: "In layout",
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
    readonlyReason:
      "این نشست ستون‌های فرمول را فقط می‌خواند و نمی‌تواند ذخیره کند. برای ساخت یا تغییر ستون فرمول، نقش برنامه‌ریز یا مدیر پروژه لازم است.",
    dataType: "نوع داده",
    unit: "واحد نتیجه",
    version: "نسخهٔ تعریف",
    apply: "نمایش در جدول",
    applyHint:
      "ستون فرمول ذخیره‌شده را به چیدمان فعالیت‌ها اضافه می‌کند. مقادیر از خواندن بعدی محیط کار توسط سرور می‌آیند.",
    inLayout: "در چیدمان",
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

const FORMULA_ERROR_MESSAGES: Record<string, { en: string; fa: string }> = {
  UNKNOWN_FORMULA_FIELD: {
    en: "The expression references a field that is not registered for this view.",
    fa: "عبارت به فیلدی ارجاع می‌دهد که برای این نما ثبت نشده است.",
  },
  FORMULA_TYPE_MISMATCH: {
    en: "The operands have incompatible types. Check the data types named in the expression.",
    fa: "عملگرها نوع سازگار ندارند. نوع داده‌های نام‌برده در عبارت را بررسی کنید.",
  },
  FORMULA_SELF_REFERENCE: {
    en: "A formula column cannot reference itself.",
    fa: "یک ستون فرمول نمی‌تواند به خودش ارجاع دهد.",
  },
  FORMULA_COLUMN_SELF_REFERENCE: {
    en: "A formula column cannot reference itself.",
    fa: "یک ستون فرمول نمی‌تواند به خودش ارجاع دهد.",
  },
  DIVISION_BY_ZERO: {
    en: "The expression divides by zero. Guard the divisor before saving.",
    fa: "عبارت بر صفر تقسیم می‌کند. پیش از ذخیره، مقسوم‌علیه را محافظت کنید.",
  },
  FORMULA_MISSING_OPERAND: {
    en: "An operand is missing; the expression is incomplete.",
    fa: "یک عملوند جا افتاده است؛ عبارت کامل نیست.",
  },
  NUMERIC_OPERANDS_REQUIRED: {
    en: "This operation needs numeric operands. A text, date or enum field was used in arithmetic.",
    fa: "این عملگر به عملوند عددی نیاز دارد؛ از فیلد متنی، تاریخ یا شمارشی در محاسبه استفاده شده است.",
  },
  RESULT_TYPE_MISMATCH: {
    en: "The computed result type does not match the declared formula result type.",
    fa: "نوع نتیجهٔ محاسبه‌شده با نوع نتیجهٔ اعلام‌شدهٔ فرمول نمی‌خواند.",
  },
  FORMULA_INVALID: {
    en: "The shared calculation core rejected the expression.",
    fa: "هستهٔ محاسباتی مشترک عبارت را نپذیرفت.",
  },
  FORMULA_COLUMN_INVALID: {
    en: "The shared calculation core rejected the expression.",
    fa: "هستهٔ محاسباتی مشترک عبارت را نپذیرفت.",
  },
  FORMULA_COLUMN_ALREADY_EXISTS: {
    en: "A saved formula column already uses this ID with a different expression or title.",
    fa: "یک ستون فرمول ذخیره‌شده با همین شناسه و عبارت یا عنوان متفاوت وجود دارد.",
  },
  FORMULA_COLUMN_TITLE_REQUIRED: {
    en: "A column title is required.",
    fa: "عنوان ستون لازم است.",
  },
  FORMULA_COLUMN_EXPRESSION_REQUIRED: {
    en: "An expression is required.",
    fa: "عبارت لازم است.",
  },
  INVALID_FORMULA_COLUMN_ID: {
    en: "The formula column ID must start with formula. and use letters, digits, underscores or dots.",
    fa: "شناسهٔ ستون فرمول باید با formula. آغاز شود و فقط حرف، رقم، زیرخط یا نقطه داشته باشد.",
  },
  P6_FORMULA_VALIDATION_FAILED: {
    en: "The shared calculation core could not validate the expression.",
    fa: "هستهٔ محاسباتی مشترک نتوانست عبارت را اعتبارسنجی کند.",
  },
};

/** Plain-language explanation for an authoritative formula error code. */
export function describeFormulaValidationError(code: string, locale: string): string {
  const persian = locale.toLowerCase().startsWith("fa");
  const [base, ...rest] = code.split(":");
  const detail = rest.join(":");
  if (base === "FIELD_NOT_FOUND" && detail) {
    return persian
      ? `عبارت به فیلد «${detail}» ارجاع می‌دهد که برای این نما ثبت نشده است.`
      : `The expression references the field "${detail}", which is not registered for this view.`;
  }
  if (base.startsWith("EXPECTED_")) {
    const position = base.replace("EXPECTED_", "").replace(/_AT_?\d*$/, "");
    return persian
      ? "عبارت کامل نیست؛ یک عملوند یا عملگر جا افتاده است."
      : `The expression is incomplete${position ? ` (expected ${position.toLowerCase().replace(/_/g, " ")})` : ""}; an operand or operator is missing.`;
  }
  if (base === "UNSUPPORTED_P6_FORMULA_FIELD_TYPE" && detail) {
    return persian
      ? `فیلدهای از نوع «${detail}» در محاسبات عبارت پشتیبانی نمی‌شوند.`
      : `Fields of type "${detail}" cannot be used in an arithmetic expression.`;
  }
  const entry = FORMULA_ERROR_MESSAGES[base];
  if (entry) return persian ? entry.fa : entry.en;
  return persian
    ? "هستهٔ محاسباتی مشترک عبارت را نپذیرفت؛ کد خطا را ببینید."
    : "The shared calculation core rejected the expression; see the error code.";
}

export type FormulaEditorFormOptions = {
  /**
   * Saving and applying a column requires a planner or project administrator
   * role. When false the panel still validates expressions (a read-scoped call)
   * but explains why the lifecycle controls are absent.
   */
  canWrite?: boolean;
  /** Field ids currently present in the saved activity layout. */
  layoutFieldIds?: readonly string[];
};

export function renderFormulaEditorForm(
  fields: readonly P6Field[],
  labels: FormulaPanelLabels,
  options: FormulaEditorFormOptions = {},
): string {
  if (fields.length === 0) {
    return `<p class="cp-empty" role="status">${escapeHtml(labels.noFields)}</p>`;
  }
  const canWrite = options.canWrite !== false;
  const optionsHtml = fields
    .map(
      (field) =>
        `<option value="${escapeHtml(field.field_id)}">${escapeHtml(
          field.display_name || field.field_id,
        )} — ${escapeHtml(field.field_id)}</option>`,
    )
    .join("");
  const saveSection = canWrite
    ? `<section class="cp-formula-save-section">
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
    </section>`
    : `<p class="cp-formula-readonly" role="status" data-formula-readonly>${escapeHtml(
        labels.readonlyReason,
      )}</p>`;
  return `<p>${escapeHtml(labels.intro)}</p>
    <form class="cp-formula-form" data-formula-form>
      <label>${escapeHtml(labels.field)}
        <select name="context_field_id" data-formula-field>${optionsHtml}</select>
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
    ${saveSection}
    <section class="cp-formula-saved-list">
      <h5>${escapeHtml(labels.existing)}</h5>
      <ul data-formula-columns>${renderFormulaColumnList([], labels, options)}</ul>
    </section>`;
}

export type FormulaColumnListOptions = {
  canWrite?: boolean;
  layoutFieldIds?: readonly string[];
};

export function renderFormulaColumnList(
  records: readonly P6FormulaColumnRecord[],
  labels: FormulaPanelLabels,
  options: FormulaColumnListOptions = {},
): string {
  if (records.length === 0) {
    return `<li class="cp-empty">${escapeHtml(labels.noExisting)}</li>`;
  }
  const inLayout = new Set(options.layoutFieldIds ?? []);
  const canWrite = options.canWrite !== false;
  return records
    .map((record) => {
      const formula = record.formula;
      const isInLayout = inLayout.has(formula.formula_id);
      const dependencies = formula.dependencies.length
        ? formula.dependencies.map((item) => `<code>${escapeHtml(item)}</code>`).join(", ")
        : escapeHtml(labels.none);
      const unit = formula.result_unit
        ? `<span data-formula-unit>${escapeHtml(formula.result_unit)}</span>`
        : "";
      const action = !canWrite
        ? ""
        : isInLayout
          ? `<span class="cp-formula-in-layout" data-formula-in-layout>${escapeHtml(
              labels.inLayout,
            )}</span>`
          : `<button type="button" data-formula-apply="${escapeHtml(
              formula.formula_id,
            )}" title="${escapeHtml(labels.applyHint)}">${escapeHtml(labels.apply)}</button>`;
      return `<li data-formula-column="${escapeHtml(formula.formula_id)}">
        <strong>${escapeHtml(formula.title)}</strong>
        <code>${escapeHtml(formula.formula_id)}</code>
        <span data-formula-meta>
          <span data-formula-version>${escapeHtml(labels.version)} ${escapeHtml(
            formula.version,
          )}</span>
          <span data-formula-data-type>${escapeHtml(labels.dataType)}: ${escapeHtml(
            formula.data_type,
          )}</span>
          <span data-formula-result-type>${escapeHtml(labels.resultType)}: ${escapeHtml(
            formula.result_type,
          )}</span>
          ${unit}
        </span>
        <code>${escapeHtml(formula.expression)}</code>
        <small data-formula-dependencies>${escapeHtml(
          labels.dependencies,
        )}: ${dependencies}</small>
        ${action}
      </li>`;
    })
    .join("");
}

export function renderFormulaAuthoritativeResult(
  presentation: P6FormulaEditorPresentation,
  fieldId: string,
  labels: FormulaPanelLabels,
  locale = "en",
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
      <p data-formula-error-message>${escapeHtml(describeFormulaValidationError(code, locale))}</p>
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
   * Planner/project-administrator gate for saving and applying a column.
   * Defaults to true so a host that has already gated the panel keeps working.
   */
  canWrite?: boolean;
  /** Field ids currently present in the saved activity layout. */
  layoutFieldIds?: readonly string[];
  /**
   * Called after the server persisted the formula column. The host adds the
   * projected field to the saved activity layout and refreshes the workspace
   * read so the grid shows server-evaluated cells.
   */
  onCreated?: (record: P6FormulaColumnRecord) => Promise<void> | void;
  /**
   * Called when a saved column is applied to the current activity layout.
   * Presentation only: the host must never evaluate the expression locally.
   */
  onApply?: (record: P6FormulaColumnRecord) => Promise<void> | void;
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
  const canWrite = options.canWrite !== false;
  const layoutFieldIds = new Set(options.layoutFieldIds ?? []);
  panel.innerHTML = renderFormulaEditorForm(fields, labels, {
    canWrite,
    layoutFieldIds: [...layoutFieldIds],
  });
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
    )}</strong><p data-formula-error-message>${escapeHtml(
      describeFormulaValidationError(code, locale),
    )}</p><p><code>${escapeHtml(code)}</code></p></div>`;
  };

  const listHost = panel.querySelector<HTMLElement>("[data-formula-columns]");
  let savedRecords: readonly P6FormulaColumnRecord[] = [];
  const renderList = (): void => {
    if (!listHost) return;
    listHost.innerHTML = renderFormulaColumnList(savedRecords, labels, {
      canWrite,
      layoutFieldIds: [...layoutFieldIds],
    });
  };
  const refreshColumns = async (): Promise<void> => {
    if (!listHost) return;
    try {
      savedRecords = await columns.list();
      renderList();
    } catch (error) {
      const code = error instanceof Error ? error.message : String(error);
      listHost.innerHTML = `<li role="alert">${escapeHtml(labels.listError)} <code>${escapeHtml(
        code,
      )}</code></li>`;
    }
  };
  void refreshColumns();

  listHost?.addEventListener("click", async (event) => {
    const target = event.target as HTMLElement | null;
    const button = target?.closest<HTMLButtonElement>("[data-formula-apply]");
    if (!button || button.disabled) return;
    const formulaId = button.getAttribute("data-formula-apply");
    const record = savedRecords.find((item) => item.formula.formula_id === formulaId);
    if (!record || !options.onApply) return;
    button.disabled = true;
    try {
      await options.onApply(record);
      layoutFieldIds.add(record.formula.formula_id);
      renderList();
    } catch (error) {
      const code = error instanceof Error ? error.message : String(error);
      showError(labels.apply + ": " + code, code);
      button.disabled = false;
    }
  });

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
        locale,
      );
      const validation = presentation.validation;
      status.textContent = validation?.valid
        ? labels.valid
        : labels.invalid;
    } catch (error) {
      const code = error instanceof Error ? error.message : String(error);
      showError(labels.validationError, code);
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
        locale,
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
      if (options.onCreated) await options.onCreated(record);
      await refreshColumns();
    } catch (error) {
      const code = error instanceof Error ? error.message : String(error);
      showError(labels.saveError, code);
    } finally {
      saveButton.disabled = false;
    }
  });
}
