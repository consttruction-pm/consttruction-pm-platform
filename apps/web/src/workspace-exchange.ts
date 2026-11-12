import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";

/**
 * Project CSV exchange client.
 *
 * Exports are read-only snapshots of the authoritative activity, resource and
 * risk facts. Imports are limited to the resource master: the file is parsed
 * and validated on the server first, and only a valid preview can be applied.
 */

export const EXCHANGE_API_VERSION = "p6-exchange-api.v1";

export type ExchangeTab = "export" | "import" | "history";

export type ExchangeDataset = {
  dataset: string;
  columns: string[];
  importable: boolean;
};

export type ExchangeCatalogue = {
  datasets: ExchangeDataset[];
  maxImportChars: number;
};

export type ExchangeExport = {
  dataset: string;
  columns: string[];
  rows: Record<string, unknown>[];
  rowCount: number;
  content: string;
  projectRevision: number;
  generatedAt: string;
};

export type ExchangeRowError = {
  row: number;
  field: string;
  code: string;
};

export type ExchangeImportResult = {
  dataset: string;
  columns: string[];
  rowCount: number;
  accepted: number;
  rejected: number;
  valid: boolean;
  errors: ExchangeRowError[];
  rows: Record<string, unknown>[];
  created: string[];
  runId: string | null;
  replayed: boolean;
};

export type ExchangeImportRun = {
  runId: string;
  dataset: string;
  mode: string;
  rowCount: number;
  accepted: number;
  rejected: number;
  occurredAt: string;
  actorId: string;
  idempotencyKey: string | null;
};

export type ExchangePageOptions = {
  transport: ApiTransport;
  context: ProjectContext;
  locale: string;
  canWrite: boolean;
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

function integer(value: unknown, code: string): number {
  if (typeof value !== "number" || !Number.isInteger(value) || value < 0) {
    throw new Error(code);
  }
  return value;
}

function exchangePath(context: ProjectContext, suffix: string): string {
  return `/api/projects/${encodeURIComponent(context.project_id)}/exchange${suffix}`;
}

function stringList(value: unknown, code: string): string[] {
  if (!Array.isArray(value)) throw new Error(code);
  return value.map((item) => requiredText(item, code));
}

export function parseCatalogue(value: unknown): ExchangeCatalogue {
  if (!isRecord(value) || value.contract_version !== EXCHANGE_API_VERSION) {
    throw new Error("INVALID_EXCHANGE_CATALOGUE");
  }
  if (!Array.isArray(value.datasets)) throw new Error("INVALID_EXCHANGE_CATALOGUE");
  const datasets: ExchangeDataset[] = value.datasets.map((entry) => {
    if (!isRecord(entry) || typeof entry.importable !== "boolean") {
      throw new Error("INVALID_EXCHANGE_CATALOGUE");
    }
    return {
      dataset: requiredText(entry.dataset, "INVALID_EXCHANGE_CATALOGUE"),
      columns: stringList(entry.columns, "INVALID_EXCHANGE_CATALOGUE"),
      importable: entry.importable,
    };
  });
  if (new Set(datasets.map((entry) => entry.dataset)).size !== datasets.length) {
    throw new Error("INVALID_EXCHANGE_CATALOGUE");
  }
  return {
    datasets,
    maxImportChars: integer(value.max_import_chars, "INVALID_EXCHANGE_CATALOGUE"),
  };
}

export function parseExport(value: unknown): ExchangeExport {
  if (!isRecord(value) || value.contract_version !== EXCHANGE_API_VERSION) {
    throw new Error("INVALID_EXCHANGE_EXPORT");
  }
  if (!Array.isArray(value.rows)) throw new Error("INVALID_EXCHANGE_EXPORT");
  const rows = value.rows.map((row) => {
    if (!isRecord(row)) throw new Error("INVALID_EXCHANGE_EXPORT");
    return row;
  });
  const rowCount = integer(value.row_count, "INVALID_EXCHANGE_EXPORT");
  if (rowCount < rows.length) throw new Error("INVALID_EXCHANGE_EXPORT");
  return {
    dataset: requiredText(value.dataset, "INVALID_EXCHANGE_EXPORT"),
    columns: stringList(value.columns, "INVALID_EXCHANGE_EXPORT"),
    rows,
    rowCount,
    content: requiredText(value.content, "INVALID_EXCHANGE_EXPORT"),
    projectRevision: integer(value.project_revision, "INVALID_EXCHANGE_EXPORT"),
    generatedAt: requiredText(value.generated_at, "INVALID_EXCHANGE_EXPORT"),
  };
}

export function parseImportResult(value: unknown): ExchangeImportResult {
  if (!isRecord(value) || value.contract_version !== EXCHANGE_API_VERSION) {
    throw new Error("INVALID_EXCHANGE_IMPORT");
  }
  if (typeof value.valid !== "boolean" || !Array.isArray(value.errors)) {
    throw new Error("INVALID_EXCHANGE_IMPORT");
  }
  const errors: ExchangeRowError[] = value.errors.map((entry) => {
    if (!isRecord(entry)) throw new Error("INVALID_EXCHANGE_IMPORT");
    return {
      row: integer(entry.row, "INVALID_EXCHANGE_IMPORT"),
      field: requiredText(entry.field, "INVALID_EXCHANGE_IMPORT"),
      code: requiredText(entry.code, "INVALID_EXCHANGE_IMPORT"),
    };
  });
  const rows = Array.isArray(value.rows)
    ? value.rows.map((row) => {
        if (!isRecord(row)) throw new Error("INVALID_EXCHANGE_IMPORT");
        return row;
      })
    : [];
  const created = Array.isArray(value.created)
    ? stringList(value.created, "INVALID_EXCHANGE_IMPORT")
    : [];
  return {
    dataset: requiredText(value.dataset, "INVALID_EXCHANGE_IMPORT"),
    columns: stringList(value.columns, "INVALID_EXCHANGE_IMPORT"),
    rowCount: integer(value.row_count, "INVALID_EXCHANGE_IMPORT"),
    accepted: integer(value.accepted, "INVALID_EXCHANGE_IMPORT"),
    rejected: integer(value.rejected, "INVALID_EXCHANGE_IMPORT"),
    valid: value.valid,
    errors,
    rows,
    created,
    runId: typeof value.run_id === "string" ? value.run_id : null,
    replayed: value.replayed === true,
  };
}

export function parseImportRuns(value: unknown): ExchangeImportRun[] {
  if (!isRecord(value) || value.contract_version !== EXCHANGE_API_VERSION) {
    throw new Error("INVALID_EXCHANGE_RUNS");
  }
  if (!Array.isArray(value.runs)) throw new Error("INVALID_EXCHANGE_RUNS");
  return value.runs.map((entry) => {
    if (!isRecord(entry)) throw new Error("INVALID_EXCHANGE_RUNS");
    return {
      runId: requiredText(entry.run_id, "INVALID_EXCHANGE_RUNS"),
      dataset: requiredText(entry.dataset, "INVALID_EXCHANGE_RUNS"),
      mode: requiredText(entry.mode, "INVALID_EXCHANGE_RUNS"),
      rowCount: integer(entry.row_count, "INVALID_EXCHANGE_RUNS"),
      accepted: integer(entry.accepted, "INVALID_EXCHANGE_RUNS"),
      rejected: integer(entry.rejected, "INVALID_EXCHANGE_RUNS"),
      occurredAt: requiredText(entry.occurred_at, "INVALID_EXCHANGE_RUNS"),
      actorId: requiredText(entry.actor_id, "INVALID_EXCHANGE_RUNS"),
      idempotencyKey:
        typeof entry.idempotency_key === "string" ? entry.idempotency_key : null,
    };
  });
}

export async function loadCatalogue(
  transport: ApiTransport,
  context: ProjectContext,
): Promise<ApiResult<ExchangeCatalogue>> {
  const result = await transport.get<unknown>(exchangePath(context, "/datasets"), context);
  if (!result.ok) return result;
  try {
    return { ok: true, data: parseCatalogue(result.data) };
  } catch {
    return localError("INVALID_EXCHANGE_CATALOGUE");
  }
}

export async function exportDataset(
  transport: ApiTransport,
  context: ProjectContext,
  dataset: string,
): Promise<ApiResult<ExchangeExport>> {
  const result = await transport.get<unknown>(
    `${exchangePath(context, "/export")}?dataset=${encodeURIComponent(dataset)}`,
    context,
  );
  if (!result.ok) return result;
  try {
    return { ok: true, data: parseExport(result.data) };
  } catch {
    return localError("INVALID_EXCHANGE_EXPORT");
  }
}

export async function previewImport(
  transport: ApiTransport,
  context: ProjectContext,
  dataset: string,
  content: string,
): Promise<ApiResult<ExchangeImportResult>> {
  const result = await transport.post<Record<string, unknown>, unknown>(
    exchangePath(context, "/import/preview"),
    { dataset, content },
    context,
  );
  if (!result.ok) return result;
  try {
    return { ok: true, data: parseImportResult(result.data) };
  } catch {
    return localError("INVALID_EXCHANGE_IMPORT");
  }
}

export async function applyImport(
  transport: ApiTransport,
  context: ProjectContext,
  dataset: string,
  content: string,
  idempotencyKey: string,
): Promise<ApiResult<ExchangeImportResult>> {
  const result = await transport.post<Record<string, unknown>, unknown>(
    exchangePath(context, "/import"),
    { dataset, content, idempotency_key: idempotencyKey },
    context,
  );
  if (!result.ok) return result;
  try {
    return { ok: true, data: parseImportResult(result.data) };
  } catch {
    return localError("INVALID_EXCHANGE_IMPORT");
  }
}

export async function loadImportRuns(
  transport: ApiTransport,
  context: ProjectContext,
): Promise<ApiResult<ExchangeImportRun[]>> {
  const result = await transport.get<unknown>(exchangePath(context, "/imports"), context);
  if (!result.ok) return result;
  try {
    return { ok: true, data: parseImportRuns(result.data) };
  } catch {
    return localError("INVALID_EXCHANGE_RUNS");
  }
}

export function mountWorkspaceExchangePage(
  host: HTMLElement,
  options: ExchangePageOptions,
): void {
  const { transport, context, locale, canWrite } = options;
  const say = (en: string, fa: string) => text(locale, en, fa);

  const state: {
    status: "loading" | "ready" | "error";
    tab: ExchangeTab;
    catalogue: ExchangeCatalogue | null;
    exportDataset: string;
    exported: ExchangeExport | null;
    exporting: boolean;
    importDataset: string;
    content: string;
    preview: ExchangeImportResult | null;
    applying: boolean;
    runs: ExchangeImportRun[];
    busy: boolean;
    errorCode: string | null;
    notice: { kind: "ok" | "warn" | "error"; message: string } | null;
  } = {
    status: "loading",
    tab: "export",
    catalogue: null,
    exportDataset: "resources",
    exported: null,
    exporting: false,
    importDataset: "resources",
    content: "",
    preview: null,
    applying: false,
    runs: [],
    busy: false,
    errorCode: null,
    notice: null,
  };
  let idempotencyKey = "";
  let downloadUrl: string | null = null;

  function importableDatasets(): ExchangeDataset[] {
    return (state.catalogue?.datasets ?? []).filter((entry) => entry.importable);
  }

  async function loadAll(): Promise<void> {
    state.status = "loading";
    render();
    const catalogue = await loadCatalogue(transport, context);
    if (!catalogue.ok) {
      state.status = "error";
      state.errorCode = catalogue.error.code;
      render();
      return;
    }
    state.catalogue = catalogue.data;
    if (!state.catalogue.datasets.some((entry) => entry.dataset === state.exportDataset)) {
      state.exportDataset = state.catalogue.datasets[0]?.dataset ?? "";
    }
    const importable = importableDatasets();
    if (!importable.some((entry) => entry.dataset === state.importDataset)) {
      state.importDataset = importable[0]?.dataset ?? "";
    }
    const runs = await loadImportRuns(transport, context);
    state.runs = runs.ok ? runs.data : [];
    state.status = "ready";
    state.errorCode = null;
    render();
  }

  async function doExport(): Promise<void> {
    if (!state.exportDataset || state.exporting) return;
    state.exporting = true;
    state.notice = null;
    render();
    const result = await exportDataset(transport, context, state.exportDataset);
    state.exporting = false;
    if (!result.ok) {
      state.notice = {
        kind: "error",
        message: `${say("Export failed", "خروجی ناموفق بود")} (${result.error.code})`,
      };
    } else {
      state.exported = result.data;
      state.notice = {
        kind: "ok",
        message: `${result.data.rowCount} ${say("rows exported", "ردیف صادر شد")}`,
      };
    }
    render();
  }

  async function doValidate(): Promise<void> {
    if (!state.importDataset || state.busy) return;
    if (!state.content.trim()) {
      state.notice = {
        kind: "warn",
        message: say("Paste or choose a CSV file first.", "ابتدا فایل CSV را جای‌گذاری یا انتخاب کنید."),
      };
      render();
      return;
    }
    state.busy = true;
    state.notice = null;
    render();
    const result = await previewImport(
      transport,
      context,
      state.importDataset,
      state.content,
    );
    state.busy = false;
    if (!result.ok) {
      state.preview = null;
      state.notice = {
        kind: "error",
        message: `${say("Validation failed", "اعتبارسنجی ناموفق بود")} (${result.error.code})`,
      };
    } else {
      state.preview = result.data;
      idempotencyKey = newIdempotencyKey();
      state.notice = {
        kind: result.data.valid ? "ok" : "warn",
        message: result.data.valid
          ? say("File is valid and ready to import.", "فایل معتبر و آمادهٔ ورود است.")
          : say("The file has errors; fix them before importing.", "فایل خطا دارد؛ پیش از ورود آن را اصلاح کنید."),
      };
    }
    render();
  }

  async function doApply(): Promise<void> {
    if (!state.preview?.valid || state.applying) return;
    if (!canWrite) {
      state.notice = {
        kind: "error",
        message: say(
          "Your role cannot import data.",
          "نقش شما اجازهٔ ورود داده را ندارد.",
        ),
      };
      render();
      return;
    }
    state.applying = true;
    render();
    const result = await applyImport(
      transport,
      context,
      state.importDataset,
      state.content,
      idempotencyKey,
    );
    state.applying = false;
    if (!result.ok) {
      state.notice = {
        kind: "error",
        message: `${say("Import failed", "ورود ناموفق بود")} (${result.error.code})`,
      };
    } else {
      state.preview = result.data;
      state.notice = {
        kind: result.data.valid ? "ok" : "error",
        message: result.data.valid
          ? `${result.data.replayed ? say("Replayed import", "ورود بازپخش‌شده") : say("Imported", "وارد شد")} ${result.data.created.length} ${say("resources", "منبع")}`
          : say("The server rejected the file.", "سرور فایل را رد کرد."),
      };
      if (result.data.valid) {
        const runs = await loadImportRuns(transport, context);
        if (runs.ok) state.runs = runs.data;
      }
    }
    render();
  }

  function newIdempotencyKey(): string {
    const cryptoObject = (globalThis as { crypto?: Crypto }).crypto;
    if (cryptoObject?.randomUUID) return cryptoObject.randomUUID();
    return `exchange-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
  }

  function renderTabs(): string {
    const tabs: { key: ExchangeTab; en: string; fa: string }[] = [
      { key: "export", en: "Export", fa: "خروجی" },
      { key: "import", en: "Import", fa: "ورود" },
      { key: "history", en: "Import history", fa: "تاریخچهٔ ورود" },
    ];
    return `<div class="cp-register-tabs" role="tablist">${tabs
      .map(
        (tab) =>
          `<button type="button" role="tab" data-exchange-tab="${tab.key}" aria-selected="${state.tab === tab.key}" class="${state.tab === tab.key ? "is-active" : ""}">${escapeHtml(say(tab.en, tab.fa))}</button>`,
      )
      .join("")}</div>`;
  }

  function renderExport(): string {
    const options = (state.catalogue?.datasets ?? [])
      .map(
        (entry) =>
          `<option value="${escapeHtml(entry.dataset)}" ${state.exportDataset === entry.dataset ? "selected" : ""}>${escapeHtml(entry.dataset)}</option>`,
      )
      .join("");
    const meta = state.exported
      ? `<p class="cp-register-notice" data-exchange-export-meta>${escapeHtml(say("Rows", "ردیف"))}: <strong>${state.exported.rowCount}</strong> · ${escapeHtml(say("project revision", "نسخهٔ پروژه"))} ${state.exported.projectRevision} · ${escapeHtml(state.exported.generatedAt)}</p>
        <div class="cp-table-scroll"><table class="cp-register-table" data-exchange-export-table><thead><tr>${state.exported.columns.map((column) => `<th>${escapeHtml(column)}</th>`).join("")}</tr></thead><tbody>${state.exported.rows
          .map(
            (row) =>
              `<tr>${state.exported!.columns.map((column) => `<td>${escapeHtml(row[column] === null || row[column] === undefined ? "" : String(row[column]))}</td>`).join("")}</tr>`,
          )
          .join("")}</tbody></table></div>`
      : `<div class="cp-calendar-empty">${escapeHtml(say("Choose a dataset and export it to preview the CSV rows.", "یک مجموعه داده انتخاب و برای پیش‌نمایش ردیف‌های CSV آن را صادر کنید."))}</div>`;
    return `<div class="cp-register-filters"><label>${escapeHtml(say("Dataset", "مجموعه داده"))}<select name="exchange-dataset" data-exchange-dataset>${options}</select></label>
      <button type="button" data-exchange-action="export" ${state.exporting ? "disabled" : ""}>${escapeHtml(say("Export CSV", "خروجی CSV"))}</button>
      ${state.exported ? `<button type="button" data-exchange-action="download">${escapeHtml(say("Download", "بارگیری"))}</button>` : ""}</div>
      ${meta}`;
  }

  function renderImport(): string {
    const options = importableDatasets()
      .map(
        (entry) =>
          `<option value="${escapeHtml(entry.dataset)}" ${state.importDataset === entry.dataset ? "selected" : ""}>${escapeHtml(entry.dataset)}</option>`,
      )
      .join("");
    const disabled = canWrite ? "" : "disabled";
    const errors = state.preview?.errors ?? [];
    const summary = state.preview
      ? `<p class="cp-register-notice" data-exchange-import-summary data-valid="${state.preview.valid}" data-accepted="${state.preview.accepted}" data-rejected="${state.preview.rejected}">${escapeHtml(say("Rows", "ردیف"))}: ${state.preview.rowCount} · ${escapeHtml(say("accepted", "پذیرفته"))}: ${state.preview.accepted} · ${escapeHtml(say("rejected", "رد"))}: ${state.preview.rejected}</p>
        ${
          errors.length
            ? `<div class="cp-table-scroll"><table class="cp-register-table" data-exchange-errors><thead><tr><th>${escapeHtml(say("Row", "ردیف"))}</th><th>${escapeHtml(say("Field", "فیلد"))}</th><th>${escapeHtml(say("Code", "کد"))}</th></tr></thead><tbody>${errors
                .map(
                  (error) =>
                    `<tr data-exchange-error-row data-row="${error.row}" data-field="${escapeHtml(error.field)}" data-code="${escapeHtml(error.code)}"><td>${error.row}</td><td>${escapeHtml(error.field)}</td><td><code>${escapeHtml(error.code)}</code></td></tr>`,
                )
                .join("")}</tbody></table></div>`
            : ""
        }
        ${
          state.preview.created.length
            ? `<p class="cp-register-notice" data-exchange-created>${escapeHtml(say("Created", "ایجاد شد"))}: ${state.preview.created.map((id) => escapeHtml(id)).join(", ")}</p>`
            : ""
        }`
      : "";
    return `<div class="cp-register-filters"><label>${escapeHtml(say("Import dataset", "مجموعه دادهٔ ورود"))}<select name="exchange-import-dataset" data-exchange-import-dataset ${disabled}>${options}</select></label>
      <label>${escapeHtml(say("CSV file", "فایل CSV"))}<input type="file" accept=".csv,text/csv" data-exchange-file ${disabled}></label></div>
      <label class="cp-report-field">${escapeHtml(say("CSV content", "محتوای CSV"))}<textarea name="exchange-content" data-exchange-content rows="6" ${disabled} placeholder="resource_id,name,...">${escapeHtml(state.content)}</textarea></label>
      <div class="cp-calendar-panel-actions">
        <button type="button" data-exchange-action="validate" ${state.busy ? "disabled" : ""}>${escapeHtml(say("Validate file", "اعتبارسنجی فایل"))}</button>
        <button type="button" data-exchange-action="apply" ${state.preview?.valid && canWrite && !state.applying ? "" : "disabled"}>${escapeHtml(say("Apply import", "اعمال ورود"))}</button>
      </div>
      ${summary}`;
  }

  function renderHistory(): string {
    if (!state.runs.length) {
      return `<div class="cp-calendar-empty" data-exchange-history-empty>${escapeHtml(say("No import runs have been recorded for this project.", "هیچ اجرای ورودی برای این پروژه ثبت نشده است."))}</div>`;
    }
    return `<div class="cp-table-scroll"><table class="cp-register-table" data-exchange-history><thead><tr><th>${escapeHtml(say("Run", "اجرا"))}</th><th>${escapeHtml(say("Dataset", "مجموعه"))}</th><th>${escapeHtml(say("Mode", "حالت"))}</th><th>${escapeHtml(say("Rows", "ردیف"))}</th><th>${escapeHtml(say("Accepted", "پذیرفته"))}</th><th>${escapeHtml(say("Rejected", "رد"))}</th><th>${escapeHtml(say("When", "زمان"))}</th></tr></thead><tbody>${state.runs
      .map(
        (run) =>
          `<tr data-exchange-run-row data-run-id="${escapeHtml(run.runId)}"><td><code>${escapeHtml(run.runId)}</code></td><td>${escapeHtml(run.dataset)}</td><td>${escapeHtml(run.mode)}</td><td>${run.rowCount}</td><td>${run.accepted}</td><td>${run.rejected}</td><td>${escapeHtml(run.occurredAt)}</td></tr>`,
      )
      .join("")}</tbody></table></div>`;
  }

  function render(): void {
    if (state.status === "loading") {
      host.innerHTML = `<div class="cp-register-toolbar"><strong>${escapeHtml(say("Import / Export", "ورود / خروجی"))}</strong></div><div class="cp-calendar-empty" role="status">${escapeHtml(say("Reading exchange datasets…", "در حال خواندن مجموعه‌های داده…"))}</div>`;
      return;
    }
    if (state.status === "error") {
      host.innerHTML = `<div class="cp-register-toolbar"><strong>${escapeHtml(say("Import / Export", "ورود / خروجی"))}</strong><div><button type="button" data-exchange-action="reload">${escapeHtml(say("Refresh", "به‌روزرسانی"))}</button></div></div><div class="cp-calendar-empty" role="alert">${escapeHtml(say("Exchange datasets could not be read", "خواندن مجموعه‌های داده ناموفق بود"))} (${escapeHtml(state.errorCode ?? "unknown")})</div>`;
      return;
    }
    const body =
      state.tab === "export"
        ? renderExport()
        : state.tab === "import"
          ? renderImport()
          : renderHistory();
    host.innerHTML = `<div class="cp-register-toolbar"><strong>${escapeHtml(say("Import / Export", "ورود / خروجی"))}</strong><div><button type="button" data-exchange-action="reload">${escapeHtml(say("Refresh", "به‌روزرسانی"))}</button></div></div>
      ${renderTabs()}
      <div class="cp-admin-body" data-exchange-body data-exchange-active-tab="${state.tab}">${body}</div>
      ${state.notice ? `<p class="cp-calendar-notice" data-exchange-notice data-state="${state.notice.kind}" role="status">${escapeHtml(state.notice.message)}</p>` : ""}`;
  }

  host.addEventListener("click", (event) => {
    const target = event.target as HTMLElement;
    const tab = target.closest<HTMLElement>("[data-exchange-tab]")
      ?.dataset.exchangeTab as ExchangeTab | undefined;
    if (tab) {
      state.tab = tab;
      state.notice = null;
      render();
      return;
    }
    const action = target.closest<HTMLElement>("[data-exchange-action]")?.dataset
      .exchangeAction;
    if (action === "reload") {
      void loadAll();
    } else if (action === "export") {
      void doExport();
    } else if (action === "download") {
      if (state.exported) {
        if (downloadUrl) URL.revokeObjectURL(downloadUrl);
        const blob = new Blob([state.exported.content], {
          type: "text/csv;charset=utf-8",
        });
        downloadUrl = URL.createObjectURL(blob);
        const anchor = document.createElement("a");
        anchor.href = downloadUrl;
        anchor.download = `${state.exported.dataset}.csv`;
        host.appendChild(anchor);
        anchor.click();
        anchor.remove();
      }
    } else if (action === "validate") {
      void doValidate();
    } else if (action === "apply") {
      void doApply();
    }
  });

  host.addEventListener("input", (event) => {
    const target = event.target as HTMLTextAreaElement;
    if (target.matches("[data-exchange-content]")) {
      state.content = target.value;
      state.preview = null;
    }
  });

  host.addEventListener("change", (event) => {
    const target = event.target as HTMLInputElement | HTMLSelectElement;
    if (target.matches("[data-exchange-dataset]")) {
      state.exportDataset = target.value;
      state.exported = null;
      render();
      return;
    }
    if (target.matches("[data-exchange-import-dataset]")) {
      state.importDataset = target.value;
      state.preview = null;
      render();
      return;
    }
    if (target.matches("[data-exchange-file]")) {
      const file = (target as HTMLInputElement).files?.[0];
      if (!file) return;
      const reader = new FileReader();
      reader.addEventListener("load", () => {
        state.content = String(reader.result ?? "");
        state.preview = null;
        render();
      });
      reader.addEventListener("error", () => {
        state.notice = {
          kind: "error",
          message: say("The selected file could not be read.", "فایل انتخاب‌شده خوانده نشد."),
        };
        render();
      });
      reader.readAsText(file);
    }
  });

  void loadAll();
}
