import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";
import { bindRegisterContextMenus } from "./workspace-register-context-menu.js";

/**
 * Project report register client.
 *
 * A definition selects one authoritative subject and an ordered subset of its
 * fields. A run is materialized and stored by the server; this module renders
 * the stored rows verbatim and never derives report facts in the browser.
 */

export const REPORT_API_VERSION = "p6-report-api.v1";

export const REPORT_SUBJECTS = ["activities", "resources", "risks"] as const;

export type ReportSubject = (typeof REPORT_SUBJECTS)[number];

export type ReportField = {
  key: string;
  label: string;
  dataType: string;
};

export type ReportCatalogueSubject = {
  subject: ReportSubject;
  label: string;
  fields: ReportField[];
};

export type ReportDefinition = {
  reportId: string;
  name: string;
  description: string;
  subject: ReportSubject;
  columns: string[];
  revision: number;
};

export type ReportRunSummary = {
  runId: string;
  reportId: string;
  reportRevision: number;
  projectRevision: number;
  subject: string;
  columns: string[];
  rowCount: number;
  generatedAt: string;
  generatedBy: string;
};

export type ReportRun = ReportRunSummary & {
  rows: Array<Record<string, unknown>>;
};

export type ReportInput = {
  reportId: string;
  name: string;
  description: string;
  subject: string;
  columns: string[];
};

export type ReportPageOptions = {
  transport: ApiTransport;
  context: ProjectContext;
  locale: string;
  canWrite: boolean;
};

export type ReportList = {
  catalogue: ReportCatalogueSubject[];
  reports: ReportDefinition[];
};

function text(locale: string, en: string, fa: string): string {
  return locale.split("-")[0] === "fa" ? fa : en;
}

function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function localError(code: string): ApiResult<never> {
  return {
    ok: false,
    error: {
      code,
      retryable: false,
      message_key: "error.request.invalid",
      available_actions: [],
    },
  };
}

function requiredText(value: unknown, code: string): string {
  if (typeof value !== "string" || !value.trim()) throw new Error(code);
  return value;
}

function reportPath(context: ProjectContext, reportId?: string, action?: string): string {
  const base = `/api/projects/${encodeURIComponent(context.project_id)}/reports`;
  if (!reportId) return base;
  return `${base}/${encodeURIComponent(reportId)}${action ? `/${action}` : ""}`;
}

function subjectOf(value: unknown): ReportSubject {
  if (typeof value !== "string" || !REPORT_SUBJECTS.includes(value as ReportSubject)) {
    throw new Error("INVALID_REPORT_SUBJECT");
  }
  return value as ReportSubject;
}

export function parseCatalogue(value: unknown): ReportCatalogueSubject[] {
  if (!Array.isArray(value)) throw new Error("INVALID_REPORT_CATALOGUE");
  const subjects: ReportCatalogueSubject[] = [];
  for (const entry of value) {
    if (!isRecord(entry)) throw new Error("INVALID_REPORT_CATALOGUE");
    const subject = subjectOf(entry.subject);
    const label = requiredText(entry.label, "INVALID_REPORT_CATALOGUE");
    if (!Array.isArray(entry.fields) || !entry.fields.length) {
      throw new Error("INVALID_REPORT_CATALOGUE");
    }
    const fields: ReportField[] = [];
    const keys = new Set<string>();
    for (const field of entry.fields) {
      if (!isRecord(field)) throw new Error("INVALID_REPORT_CATALOGUE");
      const key = requiredText(field.key, "INVALID_REPORT_CATALOGUE");
      if (keys.has(key)) throw new Error("INVALID_REPORT_CATALOGUE");
      keys.add(key);
      fields.push({
        key,
        label: requiredText(field.label, "INVALID_REPORT_CATALOGUE"),
        dataType: requiredText(field.data_type, "INVALID_REPORT_CATALOGUE"),
      });
    }
    subjects.push({ subject, label, fields });
  }
  if (new Set(subjects.map((item) => item.subject)).size !== subjects.length) {
    throw new Error("INVALID_REPORT_CATALOGUE");
  }
  return subjects;
}

function parseColumns(
  value: unknown,
  catalogue: ReportCatalogueSubject[],
  subject: ReportSubject,
): string[] {
  if (!Array.isArray(value) || !value.length) throw new Error("INVALID_REPORT_COLUMNS");
  const allowed = catalogue.find((item) => item.subject === subject)?.fields ?? [];
  const keys = new Set(allowed.map((field) => field.key));
  const columns: string[] = [];
  for (const column of value) {
    if (typeof column !== "string" || !keys.has(column) || columns.includes(column)) {
      throw new Error("INVALID_REPORT_COLUMNS");
    }
    columns.push(column);
  }
  return columns;
}

export function parseReportDefinition(
  value: unknown,
  catalogue: ReportCatalogueSubject[],
): ReportDefinition {
  if (!isRecord(value)) throw new Error("INVALID_REPORT_RECORD");
  if (value.contract_version !== REPORT_API_VERSION) {
    throw new Error("INVALID_REPORT_RESPONSE");
  }
  const reportId = requiredText(value.report_id, "INVALID_REPORT_RECORD");
  const subject = subjectOf(value.subject);
  const revision = value.record_revision;
  if (typeof revision !== "number" || !Number.isInteger(revision) || revision < 1) {
    throw new Error("INVALID_REPORT_RECORD");
  }
  return {
    reportId,
    name: requiredText(value.name, "INVALID_REPORT_RECORD"),
    description: typeof value.description === "string" ? value.description : "",
    subject,
    columns: parseColumns(value.columns, catalogue, subject),
    revision,
  };
}

export function parseReportList(value: unknown): ReportList {
  if (!isRecord(value)) throw new Error("INVALID_REPORT_LIST");
  if (value.contract_version !== REPORT_API_VERSION) {
    throw new Error("INVALID_REPORT_RESPONSE");
  }
  const catalogue = parseCatalogue(value.catalogue);
  if (!Array.isArray(value.reports)) throw new Error("INVALID_REPORT_LIST");
  const reports = value.reports.map((entry) => parseReportDefinition(entry, catalogue));
  if (new Set(reports.map((item) => item.reportId)).size !== reports.length) {
    throw new Error("INVALID_REPORT_LIST");
  }
  return { catalogue, reports };
}

function parseRunSummary(value: unknown): ReportRunSummary {
  if (!isRecord(value)) throw new Error("INVALID_REPORT_RUN");
  if (value.contract_version !== REPORT_API_VERSION) {
    throw new Error("INVALID_REPORT_RESPONSE");
  }
  const rowCount = value.row_count;
  if (typeof rowCount !== "number" || !Number.isInteger(rowCount) || rowCount < 0) {
    throw new Error("INVALID_REPORT_RUN");
  }
  const columns = value.columns;
  if (!Array.isArray(columns) || !columns.length || columns.some((item) => typeof item !== "string")) {
    throw new Error("INVALID_REPORT_RUN");
  }
  return {
    runId: requiredText(value.run_id, "INVALID_REPORT_RUN"),
    reportId: requiredText(value.report_id, "INVALID_REPORT_RUN"),
    reportRevision: Number(value.report_revision),
    projectRevision: Number(value.project_revision),
    subject: requiredText(value.subject, "INVALID_REPORT_RUN"),
    columns: columns as string[],
    rowCount,
    generatedAt: requiredText(value.generated_at, "INVALID_REPORT_RUN"),
    generatedBy: requiredText(value.generated_by, "INVALID_REPORT_RUN"),
  };
}

export function parseReportRun(value: unknown): ReportRun {
  const summary = parseRunSummary(value);
  if (!isRecord(value)) throw new Error("INVALID_REPORT_RUN");
  if (!Array.isArray(value.rows) || value.rows.length !== summary.rowCount) {
    throw new Error("INVALID_REPORT_RUN");
  }
  const expected = new Set(summary.columns);
  const rows = value.rows.map((row) => {
    if (!isRecord(row)) throw new Error("INVALID_REPORT_RUN");
    const keys = Object.keys(row);
    if (keys.length !== expected.size || keys.some((key) => !expected.has(key))) {
      throw new Error("INVALID_REPORT_RUN");
    }
    return row;
  });
  return { ...summary, rows };
}

export function parseRunList(value: unknown): ReportRunSummary[] {
  if (!isRecord(value)) throw new Error("INVALID_REPORT_RUN_LIST");
  if (value.contract_version !== REPORT_API_VERSION) {
    throw new Error("INVALID_REPORT_RESPONSE");
  }
  if (!Array.isArray(value.runs)) throw new Error("INVALID_REPORT_RUN_LIST");
  return value.runs.map((entry) => parseRunSummary(entry));
}

export async function loadReports(
  transport: ApiTransport,
  context: ProjectContext,
  filters: { subject: string; search: string },
): Promise<ApiResult<ReportList>> {
  const params = new URLSearchParams();
  if (filters.subject) params.set("subject", filters.subject);
  if (filters.search) params.set("search", filters.search);
  const suffix = params.toString() ? `?${params.toString()}` : "";
  const result = await transport.get<unknown>(`${reportPath(context)}${suffix}`, context);
  if (!result.ok) return result;
  try {
    return { ok: true, data: parseReportList(result.data) };
  } catch {
    return localError("INVALID_REPORT_LIST");
  }
}

export async function saveReport(
  transport: ApiTransport,
  context: ProjectContext,
  input: ReportInput,
  expectedRevision?: number,
): Promise<ApiResult<ReportDefinition>> {
  if (expectedRevision === undefined) {
    if (!transport.post) return localError("TRANSPORT_UNAVAILABLE");
    const result = await transport.post<Record<string, unknown>, unknown>(
      reportPath(context),
      {
        report_id: input.reportId,
        name: input.name,
        description: input.description,
        subject: input.subject,
        columns: input.columns,
        idempotency_key: `report-${input.reportId}-${Date.now()}`,
      },
      context,
    );
    if (!result.ok) return result;
    try {
      const catalogueResult = await transport.get<unknown>(reportPath(context), context);
      const catalogue = catalogueResult.ok ? parseReportList(catalogueResult.data).catalogue : [];
      return { ok: true, data: parseReportDefinition(result.data, catalogue) };
    } catch {
      return localError("INVALID_REPORT_RESPONSE");
    }
  }
  if (!transport.patch) return localError("TRANSPORT_UNAVAILABLE");
  const result = await transport.patch<Record<string, unknown>, unknown>(
    reportPath(context, input.reportId),
    {
      report_id: input.reportId,
      name: input.name,
      description: input.description,
      subject: input.subject,
      columns: input.columns,
      expected_revision: expectedRevision,
    },
    context,
  );
  if (!result.ok) return result;
  try {
    const listed = await loadReports(transport, context, { subject: "", search: "" });
    const catalogue = listed.ok ? listed.data.catalogue : [];
    return { ok: true, data: parseReportDefinition(result.data, catalogue) };
  } catch {
    return localError("INVALID_REPORT_RESPONSE");
  }
}

export async function deleteReport(
  transport: ApiTransport,
  context: ProjectContext,
  reportId: string,
  expectedRevision: number,
): Promise<ApiResult<{ deleted: boolean }>> {
  if (!transport.delete) return localError("TRANSPORT_UNAVAILABLE");
  const result = await transport.delete<Record<string, unknown>, unknown>(
    reportPath(context, reportId),
    { expected_revision: expectedRevision },
    context,
  );
  if (!result.ok) return result;
  const data = result.data;
  return { ok: true, data: { deleted: isRecord(data) && data.deleted === true } };
}

export async function runReport(
  transport: ApiTransport,
  context: ProjectContext,
  reportId: string,
): Promise<ApiResult<ReportRun>> {
  if (!transport.post) return localError("TRANSPORT_UNAVAILABLE");
  const result = await transport.post<Record<string, unknown>, unknown>(
    reportPath(context, reportId, "run"),
    {},
    context,
  );
  if (!result.ok) return result;
  try {
    return { ok: true, data: parseReportRun(result.data) };
  } catch {
    return localError("INVALID_REPORT_RUN");
  }
}

export async function loadReportRuns(
  transport: ApiTransport,
  context: ProjectContext,
  reportId: string,
): Promise<ApiResult<ReportRunSummary[]>> {
  const result = await transport.get<unknown>(reportPath(context, reportId, "runs"), context);
  if (!result.ok) return result;
  try {
    return { ok: true, data: parseRunList(result.data) };
  } catch {
    return localError("INVALID_REPORT_RUN_LIST");
  }
}

export async function loadReportRun(
  transport: ApiTransport,
  context: ProjectContext,
  reportId: string,
  runId: string,
): Promise<ApiResult<ReportRun>> {
  const result = await transport.get<unknown>(
    `${reportPath(context, reportId, "runs")}/${encodeURIComponent(runId)}`,
    context,
  );
  if (!result.ok) return result;
  try {
    return { ok: true, data: parseReportRun(result.data) };
  } catch {
    return localError("INVALID_REPORT_RUN");
  }
}

type PageState = {
  status: "loading" | "loaded" | "error";
  errorCode: string | null;
  catalogue: ReportCatalogueSubject[];
  reports: ReportDefinition[];
  filters: { subject: string; search: string };
  selectedId: string | null;
  mode: "browse" | "create" | "edit";
  editingRevision: number | null;
  draft: ReportInput;
  run: ReportRun | null;
  runStatus: "idle" | "loading" | "error";
  runs: ReportRunSummary[];
  runsStatus: "idle" | "loading" | "error";
  busy: boolean;
  notice: { kind: "ok" | "error"; message: string } | null;
};

function emptyDraft(): ReportInput {
  return { reportId: "", name: "", description: "", subject: "activities", columns: [] };
}

function draftFrom(item: ReportDefinition): ReportInput {
  return {
    reportId: item.reportId,
    name: item.name,
    description: item.description,
    subject: item.subject,
    columns: [...item.columns],
  };
}

function formatCell(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  return String(value);
}

export function mountWorkspaceReportsPage(host: HTMLElement, options: ReportPageOptions): void {
  if (host.dataset.reportsMounted === "true") return;
  host.dataset.reportsMounted = "true";
  const { transport, context, locale, canWrite } = options;
  const state: PageState = {
    status: "loading",
    errorCode: null,
    catalogue: [],
    reports: [],
    filters: { subject: "", search: "" },
    selectedId: null,
    mode: "browse",
    editingRevision: null,
    draft: emptyDraft(),
    run: null,
    runStatus: "idle",
    runs: [],
    runsStatus: "idle",
    busy: false,
    notice: null,
  };

  const say = (en: string, fa: string): string => text(locale, en, fa);
  const subjectLabel = (value: string): string =>
    ({
      activities: say("Activities", "فعالیت‌ها"),
      resources: say("Resources", "منابع"),
      risks: say("Risks", "ریسک‌ها"),
    })[value] ?? value;
  const selected = (): ReportDefinition | null =>
    state.reports.find((item) => item.reportId === state.selectedId) ?? null;
  const fieldsFor = (subject: string): ReportField[] =>
    state.catalogue.find((item) => item.subject === subject)?.fields ?? [];

  function renderRegister(): string {
    if (state.status === "loading") {
      return `<div class="cp-calendar-empty" role="status">${escapeHtml(say("Reading report definitions…", "در حال خواندن تعاریف گزارش…"))}</div>`;
    }
    if (state.status === "error") {
      return `<div class="cp-calendar-empty" role="alert">${escapeHtml(say("Reports could not be read", "خواندن گزارش‌ها ناموفق بود"))} (${escapeHtml(state.errorCode ?? "unknown")})</div>`;
    }
    if (!state.reports.length) {
      return `<div class="cp-calendar-empty" data-report-empty>${escapeHtml(say("No report definitions are stored for this project.", "هیچ تعریف گزارشی برای این پروژه ذخیره نشده است."))}</div>`;
    }
    const rows = state.reports.map((item) => {
      const active = item.reportId === state.selectedId;
      return `<tr data-report-row data-report-id="${escapeHtml(item.reportId)}" tabindex="0" role="button" aria-selected="${active}" class="${active ? "is-selected" : ""}"><td><strong>${escapeHtml(item.reportId)}</strong><br><span>${escapeHtml(item.name)}</span></td><td>${escapeHtml(subjectLabel(item.subject))}</td><td>${item.columns.length}</td><td>${item.revision}</td></tr>`;
    });
    return `<div class="cp-table-scroll"><table class="cp-register-table"><thead><tr><th>${escapeHtml(say("Report", "گزارش"))}</th><th>${escapeHtml(say("Subject", "موضوع"))}</th><th>${escapeHtml(say("Columns", "ستون‌ها"))}</th><th>${escapeHtml(say("Revision", "نسخه"))}</th></tr></thead><tbody>${rows.join("")}</tbody></table></div>`;
  }

  function renderRunPreview(): string {
    if (state.runStatus === "loading") {
      return `<p class="cp-register-notice">${escapeHtml(say("Running report…", "در حال اجرای گزارش…"))}</p>`;
    }
    if (state.runStatus === "error") {
      return `<p class="cp-register-notice" role="alert">${escapeHtml(say("The report run failed.", "اجرای گزارش ناموفق بود."))}</p>`;
    }
    if (!state.run) return "";
    const head = state.run.columns
      .map((column) => `<th scope="col">${escapeHtml(column)}</th>`)
      .join("");
    const body = state.run.rows
      .map(
        (row, index) =>
          `<tr data-report-run-row data-row-index="${index}">${state.run?.columns.map((column) => `<td>${escapeHtml(formatCell(row[column]))}</td>`).join("")}</tr>`,
      )
      .join("");
    return `<section class="cp-report-run-preview" data-report-run-preview>
      <header><strong>${escapeHtml(say("Report Output", "خروجی گزارش"))}</strong><span data-report-run-meta>${escapeHtml(state.run.runId)} · ${state.run.rowCount} ${escapeHtml(say("rows", "ردیف"))} · ${escapeHtml(say("definition revision", "نسخهٔ تعریف"))} ${state.run.reportRevision} · ${escapeHtml(say("project revision", "نسخهٔ پروژه"))} ${state.run.projectRevision}</span></header>
      <div class="cp-table-scroll"><table class="cp-register-table" data-report-run-table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>
    </section>`;
  }

  function renderRunHistory(): string {
    if (state.runsStatus === "loading") {
      return `<p class="cp-register-notice">${escapeHtml(say("Reading run history…", "در حال خواندن تاریخچهٔ اجرا…"))}</p>`;
    }
    if (state.runsStatus === "error") {
      return `<p class="cp-register-notice" role="alert">${escapeHtml(say("Run history could not be read.", "خواندن تاریخچهٔ اجرا ناموفق بود."))}</p>`;
    }
    if (!state.runs.length) {
      return `<p class="cp-register-notice">${escapeHtml(say("This report has not been run yet.", "این گزارش هنوز اجرا نشده است."))}</p>`;
    }
    const items = state.runs
      .map(
        (run) =>
          `<li><button type="button" data-report-run-item data-run-id="${escapeHtml(run.runId)}"><strong>${escapeHtml(run.runId)}</strong><span>${escapeHtml(run.generatedAt)} · ${run.rowCount} ${escapeHtml(say("rows", "ردیف"))} · ${escapeHtml(say("revision", "نسخه"))} ${run.reportRevision}</span></button></li>`,
      )
      .join("");
    return `<ul class="cp-register-history cp-report-run-history" data-report-run-history>${items}</ul>`;
  }

  function renderForm(): string {
    const editing = state.mode === "edit";
    const draft = state.draft;
    const subjectOptions = state.catalogue
      .map(
        (item) =>
          `<option value="${item.subject}" ${draft.subject === item.subject ? "selected" : ""}>${escapeHtml(subjectLabel(item.subject))}</option>`,
      )
      .join("");
    const fields = fieldsFor(draft.subject);
    const checkboxes = fields.length
      ? fields
          .map(
            (field) =>
              `<label class="cp-report-field"><input type="checkbox" data-report-field value="${escapeHtml(field.key)}" ${draft.columns.includes(field.key) ? "checked" : ""}> ${escapeHtml(field.label)}</label>`,
          )
          .join("")
      : `<p class="cp-register-notice">${escapeHtml(say("The field catalogue is not available.", "فهرست فیلدها در دسترس نیست."))}</p>`;
    return `<form data-report-form class="cp-expense-fields">
      <label>${escapeHtml(say("Report ID", "شناسه گزارش"))}<input name="report-id" value="${escapeHtml(draft.reportId)}" ${editing ? "readonly" : ""} required></label>
      <label>${escapeHtml(say("Name", "نام"))}<input name="report-name" value="${escapeHtml(draft.name)}" required></label>
      <label>${escapeHtml(say("Subject", "موضوع"))}<select name="report-subject" ${editing ? "disabled" : ""}>${subjectOptions}</select></label>
      <label class="cp-field-wide">${escapeHtml(say("Description", "شرح"))}<textarea name="report-description" rows="2">${escapeHtml(draft.description)}</textarea></label>
      <fieldset class="cp-report-fields cp-field-wide"><legend>${escapeHtml(say("Columns", "ستون‌ها"))}</legend>${checkboxes}</fieldset>
      <div class="cp-calendar-panel-actions"><button type="submit" data-report-action="save" ${state.busy ? "disabled" : ""}>${escapeHtml(editing ? say("Save report", "ذخیره گزارش") : say("Create report", "ایجاد گزارش"))}</button><button type="button" data-report-action="cancel">${escapeHtml(say("Cancel", "لغو"))}</button></div>
    </form>`;
  }

  function renderDetails(): string {
    if (state.mode !== "browse") return renderForm();
    const item = selected();
    if (!item) {
      return `<p>${escapeHtml(say("Select a report definition to run it, read its stored output and review its run history.", "برای اجرا، خواندن خروجی ذخیره‌شده و مرور تاریخچهٔ اجرا، یک تعریف گزارش را انتخاب کنید."))}</p>`;
    }
    const columns = fieldsFor(item.subject)
      .filter((field) => item.columns.includes(field.key))
      .map((field) => `<span class="cp-report-column" data-report-column="${escapeHtml(field.key)}">${escapeHtml(field.label)}</span>`)
      .join("");
    const actions = `${canWrite ? `<button type="button" data-report-edit="${escapeHtml(item.reportId)}">${escapeHtml(say("Edit report", "ویرایش گزارش"))}</button><button type="button" data-report-delete="${escapeHtml(item.reportId)}" data-report-revision="${item.revision}">${escapeHtml(say("Delete", "حذف"))}</button>` : ""}<button type="button" data-report-action="run" ${state.busy || state.runStatus === "loading" ? "disabled" : ""}>${escapeHtml(say("Run report", "اجرای گزارش"))}</button>`;
    return `<div class="cp-expense-fields">
      <label>${escapeHtml(say("Report ID", "شناسه گزارش"))}<input readonly value="${escapeHtml(item.reportId)}"></label>
      <label>${escapeHtml(say("Name", "نام"))}<input readonly value="${escapeHtml(item.name)}"></label>
      <label>${escapeHtml(say("Subject", "موضوع"))}<input readonly value="${escapeHtml(subjectLabel(item.subject))}"></label>
      <label>${escapeHtml(say("Revision", "نسخه"))}<input readonly value="${item.revision}"></label>
      <label class="cp-field-wide">${escapeHtml(say("Description", "شرح"))}<input readonly value="${escapeHtml(item.description || say("Not provided", "ارائه نشده"))}"></label>
      <div class="cp-field-wide"><strong>${escapeHtml(say("Columns", "ستون‌ها"))}</strong><div class="cp-report-columns">${columns}</div></div>
    </div>
    <div class="cp-calendar-panel-actions">${actions}</div>
    ${renderRunPreview()}
    <section class="cp-report-history"><header><strong>${escapeHtml(say("Run History", "تاریخچهٔ اجرا"))}</strong></header>${renderRunHistory()}</section>`;
  }

  function render(): void {
    host.innerHTML = `<div class="cp-register-toolbar"><strong>${escapeHtml(say("Project Reports", "گزارش‌های پروژه"))}</strong><div>${canWrite ? `<button type="button" data-report-action="new" ${state.busy ? "disabled" : ""}>${escapeHtml(say("New Report", "گزارش جدید"))}</button>` : ""}<button type="button" data-report-action="reload" ${state.busy ? "disabled" : ""}>${escapeHtml(say("Refresh", "به‌روزرسانی"))}</button></div></div>
      <div class="cp-register-filters">
        <label>${escapeHtml(say("Subject", "موضوع"))}<select name="report-subject-filter"><option value="">${escapeHtml(say("All subjects", "همهٔ موضوع‌ها"))}</option>${state.catalogue.map((item) => `<option value="${item.subject}" ${state.filters.subject === item.subject ? "selected" : ""}>${escapeHtml(subjectLabel(item.subject))}</option>`).join("")}</select></label>
        <label>${escapeHtml(say("Search", "جستجو"))}<input type="search" name="report-search-filter" value="${escapeHtml(state.filters.search)}" placeholder="${escapeHtml(say("ID or name", "شناسه یا نام"))}"></label>
      </div>
      <div class="cp-report-body"><div class="cp-report-register">${renderRegister()}</div><section class="cp-report-detail" data-report-detail><header><strong>${escapeHtml(say("Report Definition", "تعریف گزارش"))}</strong><span>${selected() ? escapeHtml(selected()?.reportId ?? "") : escapeHtml(say("No selection", "بدون انتخاب"))}</span></header><div class="cp-register-detail-content">${renderDetails()}</div></section></div>
      ${state.notice ? `<p class="cp-calendar-notice" data-report-notice data-state="${state.notice.kind}" role="status">${escapeHtml(state.notice.message)}</p>` : ""}`;
  }

  async function reloadReports(keepSelection: string | null): Promise<void> {
    state.status = "loading";
    render();
    const result = await loadReports(transport, context, state.filters);
    if (result.ok) {
      state.status = "loaded";
      state.errorCode = null;
      state.catalogue = result.data.catalogue;
      state.reports = result.data.reports;
      state.selectedId =
        keepSelection && result.data.reports.some((item) => item.reportId === keepSelection)
          ? keepSelection
          : null;
    } else {
      state.status = "error";
      state.errorCode = result.error.code;
    }
    render();
  }

  async function reloadRuns(id: string): Promise<void> {
    state.runsStatus = "loading";
    state.runs = [];
    render();
    const result = await loadReportRuns(transport, context, id);
    if (state.selectedId !== id) return;
    state.runsStatus = result.ok ? "idle" : "error";
    state.runs = result.ok ? result.data : [];
    render();
  }

  function selectReport(id: string): void {
    state.selectedId = id;
    state.mode = "browse";
    state.run = null;
    state.runStatus = "idle";
    state.notice = null;
    render();
    void reloadRuns(id);
  }

  function beginCreate(): void {
    state.selectedId = null;
    state.mode = "create";
    state.editingRevision = null;
    const subject = state.catalogue[0]?.subject ?? "activities";
    state.draft = { ...emptyDraft(), subject };
    state.notice = null;
    render();
  }

  function beginEdit(item: ReportDefinition): void {
    state.selectedId = item.reportId;
    state.mode = "edit";
    state.editingRevision = item.revision;
    state.draft = draftFrom(item);
    state.notice = null;
    render();
  }

  async function executeRun(id: string): Promise<void> {
    state.runStatus = "loading";
    state.run = null;
    render();
    const result = await runReport(transport, context, id);
    if (state.selectedId !== id) return;
    if (!result.ok) {
      state.runStatus = "error";
      state.notice = {
        kind: "error",
        message: `${say("Report was not run", "گزارش اجرا نشد")} (${result.error.code})`,
      };
      render();
      return;
    }
    state.runStatus = "idle";
    state.run = result.data;
    state.notice = { kind: "ok", message: say("Report run stored.", "اجرای گزارش ذخیره شد.") };
    render();
    void reloadRuns(id);
  }

  async function loadStoredRun(reportId: string, runId: string): Promise<void> {
    state.runStatus = "loading";
    state.run = null;
    render();
    const result = await loadReportRun(transport, context, reportId, runId);
    if (state.selectedId !== reportId) return;
    if (!result.ok) {
      state.runStatus = "error";
      state.notice = {
        kind: "error",
        message: `${say("Stored run could not be read", "خروجی ذخیره‌شده خوانده نشد")} (${result.error.code})`,
      };
      render();
      return;
    }
    state.runStatus = "idle";
    state.run = result.data;
    state.notice = null;
    render();
  }

  async function runDelete(id: string, expectedRevision: number): Promise<void> {
    state.busy = true;
    render();
    const result = await deleteReport(transport, context, id, expectedRevision);
    state.busy = false;
    if (!result.ok) {
      state.notice = {
        kind: "error",
        message: `${say("Report was not deleted", "گزارش حذف نشد")} (${result.error.code})`,
      };
      await reloadReports(id);
      return;
    }
    state.notice = { kind: "ok", message: say("Report deleted.", "گزارش حذف شد.") };
    state.selectedId = null;
    state.mode = "browse";
    state.run = null;
    state.runs = [];
    await reloadReports(null);
  }

  host.addEventListener("click", (event) => {
    const target = event.target as HTMLElement;
    if (!canWrite && target.closest<HTMLElement>("[data-report-edit],[data-report-delete]")) return;
    const edit = target.closest<HTMLElement>("[data-report-edit]")?.dataset.reportEdit;
    if (edit) {
      const item = state.reports.find((row) => row.reportId === edit);
      if (item) beginEdit(item);
      return;
    }
    const remove = target.closest<HTMLElement>("[data-report-delete]");
    if (remove?.dataset.reportDelete) {
      void runDelete(remove.dataset.reportDelete, Number(remove.dataset.reportRevision));
      return;
    }
    const runItem = target.closest<HTMLElement>("[data-report-run-item]");
    if (runItem?.dataset.runId && state.selectedId) {
      void loadStoredRun(state.selectedId, runItem.dataset.runId);
      return;
    }
    const row = target.closest<HTMLElement>("[data-report-row]");
    if (row?.dataset.reportId) {
      selectReport(row.dataset.reportId);
      return;
    }
    const action = target.closest<HTMLElement>("[data-report-action]")?.dataset.reportAction;
    if (!action) return;
    if (action === "new") {
      if (!canWrite) return;
      beginCreate();
    } else if (action === "cancel") {
      state.mode = "browse";
      state.editingRevision = null;
      state.notice = null;
      render();
    } else if (action === "reload") {
      void reloadReports(state.selectedId);
    } else if (action === "run") {
      if (state.selectedId) void executeRun(state.selectedId);
    }
  });

  host.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" && event.key !== " ") return;
    const target = event.target as HTMLElement;
    if (target.matches("input, select, textarea, button")) return;
    const row = target.closest<HTMLElement>("[data-report-row]");
    if (row?.dataset.reportId) {
      event.preventDefault();
      selectReport(row.dataset.reportId);
    }
  });

  host.addEventListener("input", (event) => {
    const target = event.target as HTMLInputElement | HTMLTextAreaElement;
    switch (target.name) {
      case "report-id": state.draft.reportId = target.value; break;
      case "report-name": state.draft.name = target.value; break;
      case "report-description": state.draft.description = target.value; break;
      default: break;
    }
  });

  host.addEventListener("change", (event) => {
    const target = event.target as HTMLSelectElement | HTMLInputElement;
    if (target.matches("[data-report-field]")) {
      const key = target.value;
      const checked = (target as HTMLInputElement).checked;
      const fields = fieldsFor(state.draft.subject).map((field) => field.key);
      const chosen = new Set(state.draft.columns);
      if (checked) chosen.add(key);
      else chosen.delete(key);
      state.draft.columns = fields.filter((field) => chosen.has(field));
      return;
    }
    switch (target.name) {
      case "report-subject": {
        const subject = target.value;
        state.draft.subject = subject;
        const allowed = new Set(fieldsFor(subject).map((field) => field.key));
        state.draft.columns = state.draft.columns.filter((column) => allowed.has(column));
        render();
        break;
      }
      case "report-subject-filter":
        state.filters.subject = target.value;
        void reloadReports(state.selectedId);
        break;
      case "report-search-filter":
        state.filters.search = target.value.trim();
        void reloadReports(state.selectedId);
        break;
      default: break;
    }
  });

  host.addEventListener("submit", (event) => {
    const form = event.target as HTMLFormElement;
    if (!form.matches("[data-report-form]")) return;
    event.preventDefault();
    if (state.busy || !canWrite) return;
    void (async () => {
      state.busy = true;
      render();
      const editing = state.mode === "edit";
      if (!state.draft.columns.length) {
        state.busy = false;
        state.notice = {
          kind: "error",
          message: say("Select at least one column.", "حداقل یک ستون انتخاب کنید."),
        };
        render();
        return;
      }
      const result = await saveReport(
        transport,
        context,
        state.draft,
        editing ? state.editingRevision ?? undefined : undefined,
      );
      state.busy = false;
      if (!result.ok) {
        state.notice = {
          kind: "error",
          message: `${say("Report was not saved", "گزارش ذخیره نشد")} (${result.error.code})`,
        };
        if (result.error.code === "REPORT_REVISION_CONFLICT") {
          state.mode = "browse";
          await reloadReports(state.draft.reportId);
          return;
        }
        render();
        return;
      }
      state.notice = { kind: "ok", message: say("Report saved.", "گزارش ذخیره شد.") };
      state.mode = "browse";
      state.editingRevision = null;
      await reloadReports(result.data.reportId);
      if (state.selectedId) void reloadRuns(result.data.reportId);
    })();
  });

  bindRegisterContextMenus(host, {
    locale,
    canWrite,
    menus: [
      {
        kind: "report-register",
        label: { en: "Project Report", fa: "گزارش پروژه" },
        rowSelector: "[data-report-row]",
        rowIdAttribute: "data-report-id",
        commands: [
          {
            command: "report-edit",
            label: { en: "Edit Report", fa: "ویرایش گزارش" },
            icon: "edit",
            // Edit, Delete and Run live in the report detail pane, which is
            // rendered for the selected row.
            scope: "host",
            control: "[data-report-edit]",
            requiresWrite: true,
          },
          {
            command: "report-delete",
            label: { en: "Delete Report", fa: "حذف گزارش" },
            icon: "delete",
            scope: "host",
            control: "[data-report-delete]",
            requiresWrite: true,
            separatorBefore: true,
          },
          {
            command: "report-run",
            label: { en: "Run Report", fa: "اجرای گزارش" },
            icon: "progress",
            scope: "host",
            control: '[data-report-action="run"]',
          },
        ],
      },
    ],
  });

  void reloadReports(null);
}
