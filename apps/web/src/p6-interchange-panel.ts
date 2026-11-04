import type { ApiTransport, ProjectContext } from "./client.js";
import {
  createP6InterchangeClient,
  type InterchangeExportDocument,
  type InterchangeExportResult,
  type InterchangeImportResultWithAudit,
  type InterchangeImportRow,
  type InterchangeImportBatchList,
  type InterchangeImportBatchDetail,
} from "./p6-interchange-api.js";

export type InterchangePanelActivity = {
  id: string;
  name: string;
};

export type InterchangePanelLabels = {
  intro: string;
  format: string;
  formatValue: string;
  activities: string;
  export: string;
  exportIntro: string;
  exporting: string;
  exportEmpty: string;
  exportReady: string;
  download: string;
  importTitle: string;
  importIntro: string;
  importPlaceholder: string;
  chooseFile: string;
  importAction: string;
  importing: string;
  importEmptyInput: string;
  importReady: string;
  importNoRows: string;
  row: string;
  canonicalValues: string;
  warnings: string;
  providerObject: string;
  none: string;
  nonScalar: string;
  showingRows: string;
  error: string;
  permissionDenied: string;
  sessionExpired: string;
  requestInvalid: string;
  mappingRegistryEmpty: string;
  networkError: string;
  readFileError: string;
  importAuditTitle: string;
  importAuditRecorded: string;
  importAuditNotConfigured: string;
  importTargetNotApplied: string;
  importBatchId: string;
  importSourceHash: string;
  importHistoryTitle: string;
  importHistoryRefresh: string;
  importHistoryLoading: string;
  importHistoryFailed: string;
  importHistoryEmpty: string;
  importHistoryNotConfigured: string;
  importHistoryOpen: string;
  importHistoryRows: string;
  importHistoryWarnings: string;
  importHistoryFormat: string;
  importHistoryImportedAt: string;
  importHistoryImportedBy: string;
  importEvidenceTitle: string;
  importEvidenceMappings: string;
  importEvidenceRows: string;
  importEvidenceSourceFields: string;
  importEvidenceCanonicalFields: string;
  importEvidencePreservedFields: string;
  importEvidenceHashes: string;
  importEvidenceNoValues: string;
};

const LABELS: Record<"en" | "fa", InterchangePanelLabels> = {
  en: {
    intro:
      "Export the loaded activities through the project's registered provider mapping, or map an imported provider document back to canonical fields. Import is read-only: it does not change activities, dates or the schedule.",
    format: "Provider format",
    formatValue: "Provider XML (registered mapping)",
    activities: "loaded activities",
    export: "Export activities",
    exportIntro:
      "Generate a provider document from the loaded activity facts. Export is read-only.",
    exporting: "Exporting through the server codec…",
    exportEmpty: "No activities are loaded to export.",
    exportReady: "The server generated the export document.",
    download: "Download document",
    importTitle: "Map an imported document",
    importIntro:
      "Paste a provider XML document or choose a file. The server maps rows through the registered project mapping and returns canonical values and loss warnings.",
    importPlaceholder: "Paste provider XML here",
    chooseFile: "Choose file",
    importAction: "Map document",
    importing: "Mapping through the server codec…",
    importEmptyInput: "Enter or choose a provider document first.",
    importReady: "rows mapped by the server codec",
    importNoRows: "The document contained no rows.",
    row: "Row",
    canonicalValues: "Canonical values",
    warnings: "Warnings",
    providerObject: "Provider object",
    none: "None",
    nonScalar: "Non-scalar value",
    showingRows: "Showing the first rows of the mapped document.",
    error: "Import / export failed",
    permissionDenied: "The server denied this operation for the current role.",
    sessionExpired: "The session is no longer valid. Reload and sign in again.",
    requestInvalid: "The server rejected this document or request.",
    mappingRegistryEmpty: "No provider mapping is registered for this project.",
    networkError: "The server could not be reached. Try again.",
    readFileError: "The selected file could not be read.",
    importAuditTitle: "Import audit receipt",
    importAuditRecorded: "The parse evidence was saved to the project ledger.",
    importAuditNotConfigured: "The import ledger is not configured in this environment.",
    importTargetNotApplied: "Parsed and mapped only — no project activities or resources were changed.",
    importBatchId: "Batch ID",
    importSourceHash: "Source SHA-256",
    importHistoryTitle: "Import history",
    importHistoryRefresh: "Refresh history",
    importHistoryLoading: "Loading project import history…",
    importHistoryFailed: "Project import history could not be loaded.",
    importHistoryEmpty: "No import batches have been recorded for this project.",
    importHistoryNotConfigured: "The import ledger is not configured for this project environment.",
    importHistoryOpen: "View evidence",
    importHistoryRows: "Rows",
    importHistoryWarnings: "Warnings",
    importHistoryFormat: "Format",
    importHistoryImportedAt: "Imported at",
    importHistoryImportedBy: "Imported by",
    importEvidenceTitle: "Immutable import evidence",
    importEvidenceMappings: "Mapping snapshot",
    importEvidenceRows: "Row evidence",
    importEvidenceSourceFields: "Source fields",
    importEvidenceCanonicalFields: "Canonical fields",
    importEvidencePreservedFields: "Preserved extension fields",
    importEvidenceHashes: "Value hashes only; raw source values are not stored.",
    importEvidenceNoValues: "No rows were recorded.",
  },
  fa: {
    intro:
      "فعالیت‌های بارگذاری‌شده را با نگاشت ثبت‌شدهٔ پروژه صادر کنید، یا سند ورودی ارائه‌دهنده را به فیلدهای متعارف نگاشت کنید. ورود فقط خواندنی است: فعالیت‌ها، تاریخ‌ها و زمان‌بندی را تغییر نمی‌دهد.",
    format: "قالب ارائه‌دهنده",
    formatValue: "XML ارائه‌دهنده (نگاشت ثبت‌شده)",
    activities: "فعالیت بارگذاری‌شده",
    export: "خروجی فعالیت‌ها",
    exportIntro:
      "سند ارائه‌دهنده را از واقعیت‌های فعالیت‌های بارگذاری‌شده تولید کنید. خروجی فقط خواندنی است.",
    exporting: "در حال خروجی با کدک سرور…",
    exportEmpty: "فعالیتی برای خروجی بارگذاری نشده است.",
    exportReady: "سند خروجی توسط سرور تولید شد.",
    download: "بارگیری سند",
    importTitle: "نگاشت سند ورودی",
    importIntro:
      "سند XML ارائه‌دهنده را جای‌گذاری کنید یا فایل را انتخاب کنید. سرور ردیف‌ها را با نگاشت ثبت‌شدهٔ پروژه تبدیل می‌کند و مقادیر متعارف و هشدارهای افت را برمی‌گرداند.",
    importPlaceholder: "XML ارائه‌دهنده را اینجا جای‌گذاری کنید",
    chooseFile: "انتخاب فایل",
    importAction: "نگاشت سند",
    importing: "در حال نگاشت با کدک سرور…",
    importEmptyInput: "ابتدا سند ارائه‌دهنده را وارد یا انتخاب کنید.",
    importReady: "ردیف توسط کدک سرور نگاشت شد",
    importNoRows: "سند هیچ ردیفی نداشت.",
    row: "ردیف",
    canonicalValues: "مقادیر متعارف",
    warnings: "هشدارها",
    providerObject: "شیء ارائه‌دهنده",
    none: "هیچ",
    nonScalar: "مقدار غیرساده",
    showingRows: "تنها ردیف‌های نخست سند نگاشت‌شده نمایش داده می‌شود.",
    error: "ورود / خروجی ناموفق بود",
    permissionDenied: "سرور این عملیات را برای نقش فعلی مجاز ندانست.",
    sessionExpired: "نشست معتبر نیست. صفحه را دوباره بارگذاری و وارد شوید.",
    requestInvalid: "سرور این سند یا درخواست را رد کرد.",
    mappingRegistryEmpty: "هیچ نگاشتی برای این پروژه ثبت نشده است.",
    networkError: "سرور در دسترس نبود. دوباره تلاش کنید.",
    readFileError: "فایل انتخاب‌شده خوانده نشد.",
    importAuditTitle: "رسید ممیزی ورود اطلاعات",
    importAuditRecorded: "شواهد Parse در دفتر پروژه ذخیره شد.",
    importAuditNotConfigured: "دفتر ثبت ورود اطلاعات در این محیط پیکربندی نشده است.",
    importTargetNotApplied: "فقط Parse و نگاشت انجام شد؛ هیچ فعالیت یا منبع پروژه‌ای تغییر نکرد.",
    importBatchId: "شناسهٔ نوبت ورود",
    importSourceHash: "هش SHA-256 منبع",
    importHistoryTitle: "تاریخچهٔ ورود اطلاعات",
    importHistoryRefresh: "بازخوانی تاریخچه",
    importHistoryLoading: "در حال خواندن تاریخچهٔ ورود پروژه…",
    importHistoryFailed: "خواندن تاریخچهٔ ورود پروژه ممکن نشد.",
    importHistoryEmpty: "هنوز نوبت ورودی برای این پروژه ثبت نشده است.",
    importHistoryNotConfigured: "دفتر ثبت ورود اطلاعات برای محیط این پروژه پیکربندی نشده است.",
    importHistoryOpen: "مشاهدهٔ شواهد",
    importHistoryRows: "ردیف‌ها",
    importHistoryWarnings: "هشدارها",
    importHistoryFormat: "قالب",
    importHistoryImportedAt: "زمان ورود",
    importHistoryImportedBy: "واردکننده",
    importEvidenceTitle: "شواهد تغییرناپذیر ورود",
    importEvidenceMappings: "تصویر نگاشت‌ها",
    importEvidenceRows: "شواهد ردیف‌ها",
    importEvidenceSourceFields: "فیلدهای منبع",
    importEvidenceCanonicalFields: "فیلدهای متعارف",
    importEvidencePreservedFields: "فیلدهای افزونهٔ حفظ‌شده",
    importEvidenceHashes: "فقط هش مقادیر نگهداری می‌شود؛ مقادیر خام منبع ذخیره نمی‌شوند.",
    importEvidenceNoValues: "ردیفی ثبت نشده است.",
  },
};

const OBJECT_EXTENSION_KEY = "p6.primavera.xml.object";
const MAX_RENDERED_ROWS = 50;
const downloadUrls = new WeakMap<HTMLElement, string>();

export function getInterchangePanelLabels(locale: string): InterchangePanelLabels {
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

function formatValue(value: unknown, labels: InterchangePanelLabels): string {
  if (value === null || value === undefined) return labels.none;
  if (
    typeof value === "string" ||
    typeof value === "number" ||
    typeof value === "boolean"
  ) {
    return escapeHtml(String(value));
  }
  return escapeHtml(labels.nonScalar);
}

export function describeInterchangeError(
  code: string,
  labels: InterchangePanelLabels,
): string {
  const normalized = code.toLowerCase();
  if (
    normalized.includes("authorization") ||
    normalized.includes("permission") ||
    normalized.includes("not_authorized")
  ) {
    return labels.permissionDenied;
  }
  if (normalized.includes("session")) return labels.sessionExpired;
  if (normalized === "mapping_registry_empty") return labels.mappingRegistryEmpty;
  if (normalized === "network_error") return labels.networkError;
  return labels.requestInvalid;
}

function renderError(code: string, labels: InterchangePanelLabels): string {
  return `<div role="alert" class="cp-interchange-error">
    <strong>${escapeHtml(labels.error)}</strong>
    <p>${escapeHtml(describeInterchangeError(code, labels))}</p>
    <p><code>${escapeHtml(code)}</code></p>
  </div>`;
}

export function renderInterchangePanel(
  activities: readonly InterchangePanelActivity[],
  labels: InterchangePanelLabels,
): string {
  const exportBody = activities.length
    ? `<form data-interchange-export-form>
        <p>${escapeHtml(labels.exportIntro)}</p>
        <button type="submit" data-interchange-export>${escapeHtml(labels.export)}</button>
      </form>`
    : `<p class="cp-empty" role="status">${escapeHtml(labels.exportEmpty)}</p>`;
  return `<p>${escapeHtml(labels.intro)}</p>
    <p class="cp-interchange-meta">
      <span>${escapeHtml(labels.format)}: <strong>${escapeHtml(labels.formatValue)}</strong></span>
      <span data-interchange-activity-count="${activities.length}">${activities.length} ${escapeHtml(labels.activities)}</span>
    </p>
    ${exportBody}
    <p data-interchange-export-status role="status"></p>
    <div data-interchange-export-result></div>
    <h3>${escapeHtml(labels.importTitle)}</h3>
    <p>${escapeHtml(labels.importIntro)}</p>
    <form data-interchange-import-form>
      <label>${escapeHtml(labels.importPlaceholder)}
        <textarea data-interchange-input rows="6" spellcheck="false" placeholder="${escapeHtml(
          labels.importPlaceholder,
        )}"></textarea>
      </label>
      <label class="cp-interchange-file">${escapeHtml(labels.chooseFile)}
        <input type="file" data-interchange-file accept=".xml,application/xml,text/xml">
      </label>
      <button type="submit" data-interchange-import>${escapeHtml(labels.importAction)}</button>
    </form>
    <p data-interchange-import-status role="status"></p>
    <div data-interchange-import-result></div>
    <section class="cp-interchange-history" data-interchange-history-section>
      <header><h3>${escapeHtml(labels.importHistoryTitle)}</h3>
        <button type="button" data-interchange-history-refresh>${escapeHtml(labels.importHistoryRefresh)}</button>
      </header>
      <p data-interchange-history-status role="status"></p>
      <div data-interchange-history-list></div>
      <div data-interchange-history-detail></div>
    </section>`;
}

export function renderInterchangeExportResult(
  result: InterchangeExportResult,
  activityCount: number,
  labels: InterchangePanelLabels,
): string {
  return `<div class="cp-interchange-success">
    <p class="cp-interchange-meta">
      <span>${activityCount} ${escapeHtml(labels.activities)}</span>
      <span>${escapeHtml(result.document.encoding.toUpperCase())} · ${result.document.data.length}</span>
    </p>
    <a data-interchange-download download>${escapeHtml(labels.download)}</a>
  </div>`;
}

function renderImportRow(
  row: InterchangeImportRow,
  index: number,
  labels: InterchangePanelLabels,
): string {
  const values = Object.entries(row.values)
    .sort(([left], [right]) => left.localeCompare(right))
    .map(
      ([key, value]) =>
        `<div><code>${escapeHtml(key)}</code> <span>${formatValue(
          value,
          labels,
        )}</span></div>`,
    )
    .join("");
  const objectName = row.extensions[OBJECT_EXTENSION_KEY];
  const objectLine =
    typeof objectName === "string" && objectName
      ? `<div><span>${escapeHtml(labels.providerObject)}</span> <code>${escapeHtml(
          objectName,
        )}</code></div>`
      : "";
  const warnings = row.warnings.length
    ? `<ul>${row.warnings
        .map((warning) => `<li><code>${escapeHtml(warning)}</code></li>`)
        .join("")}</ul>`
    : escapeHtml(labels.none);
  return `<tr>
    <td>${index + 1}</td>
    <td>${values || escapeHtml(labels.none)}${objectLine}</td>
    <td>${warnings}</td>
  </tr>`;
}

export function renderInterchangeImportResult(
  result: InterchangeImportResultWithAudit,
  labels: InterchangePanelLabels,
): string {
  const audit = result.import_audit;
  const auditMarkup = !audit
    ? ""
    : audit.status === "recorded"
      ? `<section class="cp-interchange-audit-receipt is-recorded">
          <h4>${escapeHtml(labels.importAuditTitle)}</h4>
          <p>${escapeHtml(labels.importAuditRecorded)}</p>
          <strong>${escapeHtml(labels.importTargetNotApplied)}</strong>
          <dl>
            <div><dt>${escapeHtml(labels.importBatchId)}</dt><dd><code>${escapeHtml(audit.batch_id ?? "—")}</code></dd></div>
            <div><dt>${escapeHtml(labels.importSourceHash)}</dt><dd><code>${escapeHtml(audit.source_sha256 ?? "—")}</code></dd></div>
          </dl>
        </section>`
      : `<section class="cp-interchange-audit-receipt">
          <h4>${escapeHtml(labels.importAuditTitle)}</h4>
          <p>${escapeHtml(labels.importAuditNotConfigured)}</p>
        </section>`;
  if (result.rows.length === 0) {
    return `<div class="cp-interchange-success">${auditMarkup}<p role="status">${escapeHtml(
      labels.importNoRows,
    )}</p></div>`;
  }
  const rendered = result.rows.slice(0, MAX_RENDERED_ROWS);
  const truncated =
    result.rows.length > MAX_RENDERED_ROWS
      ? `<p class="cp-interchange-meta">${escapeHtml(labels.showingRows)}</p>`
      : "";
  return `<div class="cp-interchange-success">
    ${auditMarkup}
    <p role="status"><strong>${result.rows.length}</strong> ${escapeHtml(
      labels.importReady,
    )}</p>
    ${truncated}
    <div class="cp-table-wrap">
      <table class="cp-interchange-table">
        <thead><tr>
          <th scope="col">${escapeHtml(labels.row)}</th>
          <th scope="col">${escapeHtml(labels.canonicalValues)}</th>
          <th scope="col">${escapeHtml(labels.warnings)}</th>
        </tr></thead>
        <tbody>${rendered
          .map((row, index) => renderImportRow(row, index, labels))
          .join("")}</tbody>
      </table>
    </div>
  </div>`;
}


export function renderInterchangeImportBatchList(
  result: InterchangeImportBatchList,
  labels: InterchangePanelLabels,
): string {
  if (result.status === "not_configured") {
    return `<p class="cp-empty" role="status">${escapeHtml(labels.importHistoryNotConfigured)}</p>`;
  }
  if (result.batches.length === 0) {
    return `<p class="cp-empty" role="status">${escapeHtml(labels.importHistoryEmpty)}</p>`;
  }
  return `<div class="cp-table-wrap"><table class="cp-interchange-table">
    <thead><tr>
      <th>${escapeHtml(labels.importBatchId)}</th>
      <th>${escapeHtml(labels.importHistoryFormat)}</th>
      <th>${escapeHtml(labels.importHistoryImportedAt)}</th>
      <th>${escapeHtml(labels.importHistoryImportedBy)}</th>
      <th>${escapeHtml(labels.importHistoryRows)}</th>
      <th>${escapeHtml(labels.importHistoryWarnings)}</th>
      <th></th>
    </tr></thead>
    <tbody>${result.batches.map((batch) => `<tr>
      <td><code>${escapeHtml(batch.batch_id)}</code></td>
      <td>${escapeHtml(batch.format)}</td>
      <td>${escapeHtml(batch.imported_at)}</td>
      <td>${escapeHtml(batch.imported_by)}</td>
      <td>${escapeHtml(String(batch.row_count))}</td>
      <td>${escapeHtml(String(batch.warning_count))}</td>
      <td><button type="button" data-interchange-batch-id="${escapeHtml(batch.batch_id)}">${escapeHtml(labels.importHistoryOpen)}</button></td>
    </tr>`).join("")}</tbody>
  </table></div>`;
}

function isInterchangeRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function renderInterchangeImportBatchDetail(
  detail: InterchangeImportBatchDetail,
  labels: InterchangePanelLabels,
): string {
  const batch = detail.batch;
  const mappingRows = batch.mapping_snapshot.map((mapping) => `<tr>
    <td><code>${escapeHtml(String(mapping.mapping_id ?? "—"))}</code></td>
    <td>${escapeHtml(String(mapping.source_field ?? "—"))}</td>
    <td>${escapeHtml(String(mapping.canonical_field ?? "—"))}</td>
    <td>${escapeHtml(String(mapping.status ?? "—"))}</td>
  </tr>`).join("");
  const rowCards = batch.row_summaries.map((row) => {
    const warnings = Array.isArray(row.warnings) ? row.warnings : [];
    const preserved = Array.isArray(row.preserved_extension_fields) ? row.preserved_extension_fields : [];
    const source = Array.isArray(row.source_fields) ? row.source_fields : [];
    const canonical = Array.isArray(row.canonical_fields) ? row.canonical_fields : [];
    const hashes = isInterchangeRecord(row.source_value_hashes) ? Object.entries(row.source_value_hashes) : [];
    return `<article class="cp-interchange-row-evidence">
      <strong>${escapeHtml(labels.row)} ${escapeHtml(String(Number(row.row_index ?? 0) + 1))}</strong>
      <dl>
        <div><dt>${escapeHtml(labels.importEvidenceSourceFields)}</dt><dd>${escapeHtml(source.join(", ") || labels.none)}</dd></div>
        <div><dt>${escapeHtml(labels.importEvidenceCanonicalFields)}</dt><dd>${escapeHtml(canonical.join(", ") || labels.none)}</dd></div>
        <div><dt>${escapeHtml(labels.importEvidencePreservedFields)}</dt><dd>${escapeHtml(preserved.join(", ") || labels.none)}</dd></div>
      </dl>
      <ul>${warnings.length ? warnings.map((warning) => `<li><code>${escapeHtml(String(warning))}</code></li>`).join("") : `<li>${escapeHtml(labels.none)}</li>`}</ul>
      <details><summary>${escapeHtml(labels.importEvidenceHashes)}</summary>
        <pre>${escapeHtml(JSON.stringify(Object.fromEntries(hashes), null, 2))}</pre>
      </details>
    </article>`;
  }).join("");
  return `<section class="cp-interchange-batch-detail">
    <h4>${escapeHtml(labels.importEvidenceTitle)}</h4>
    <p><strong>${escapeHtml(batch.target_application_status)}</strong></p>
    <p><code>${escapeHtml(batch.source_sha256)}</code></p>
    <h5>${escapeHtml(labels.importEvidenceMappings)}</h5>
    <div class="cp-table-wrap"><table class="cp-interchange-table"><thead><tr>
      <th>ID</th><th>${escapeHtml(labels.importEvidenceSourceFields)}</th><th>${escapeHtml(labels.importEvidenceCanonicalFields)}</th><th>Status</th>
    </tr></thead><tbody>${mappingRows}</tbody></table></div>
    <h5>${escapeHtml(labels.importEvidenceRows)}</h5>
    ${rowCards || `<p>${escapeHtml(labels.importEvidenceNoValues)}</p>`}
  </section>`;
}

function documentBytes(document: InterchangeExportDocument): ArrayBuffer {
  if (document.encoding === "utf-8") {
    return new TextEncoder().encode(document.data).buffer as ArrayBuffer;
  }
  const binary = atob(document.data);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }
  return bytes.buffer as ArrayBuffer;
}

function attachDownload(
  panel: HTMLElement,
  link: HTMLAnchorElement,
  document: InterchangeExportDocument,
  context: ProjectContext,
): void {
  const previous = downloadUrls.get(panel);
  if (previous) URL.revokeObjectURL(previous);
  const url = URL.createObjectURL(
    new Blob([documentBytes(document)], { type: "application/xml" }),
  );
  downloadUrls.set(panel, url);
  const safeProject = context.project_id.replace(/[^A-Za-z0-9._-]/g, "_");
  link.href = url;
  link.download = `activities-${safeProject}-r${context.revision}.xml`;
}

function errorCode(error: unknown): string {
  if (error instanceof Error && error.message) return error.message;
  return String(error || "INTERCHANGE_FAILED");
}

export function mountInterchangePanel(
  workspace: HTMLElement,
  transport: ApiTransport,
  context: ProjectContext,
  locale: string,
  activities: readonly InterchangePanelActivity[],
): void {
  const panel = workspace.querySelector<HTMLElement>(
    "#cp-interchange [data-interchange-panel]",
  );
  if (!panel) return;
  const previousUrl = downloadUrls.get(panel);
  if (previousUrl) {
    URL.revokeObjectURL(previousUrl);
    downloadUrls.delete(panel);
  }
  const labels = getInterchangePanelLabels(locale);
  panel.innerHTML = renderInterchangePanel(activities, labels);
  const client = createP6InterchangeClient(transport, context);

  const exportForm = panel.querySelector<HTMLFormElement>(
    "[data-interchange-export-form]",
  );
  const exportButton = panel.querySelector<HTMLButtonElement>(
    "[data-interchange-export]",
  );
  const exportStatus = panel.querySelector<HTMLElement>(
    "[data-interchange-export-status]",
  );
  const exportResult = panel.querySelector<HTMLElement>(
    "[data-interchange-export-result]",
  );
  if (exportForm && exportButton && exportStatus && exportResult) {
    exportForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (activities.length === 0) return;
      exportButton.disabled = true;
      panel.setAttribute("aria-busy", "true");
      exportStatus.textContent = labels.exporting;
      exportResult.innerHTML = "";
      try {
        const values = activities.map((activity) => ({
          "activity.id": activity.id,
          "activity.name": activity.name,
        }));
        const extensions = activities.map(() => ({
          [OBJECT_EXTENSION_KEY]: "Activity",
        }));
        const result = await client.exportDocument(values, extensions);
        exportResult.innerHTML = renderInterchangeExportResult(
          result,
          activities.length,
          labels,
        );
        exportStatus.textContent = labels.exportReady;
        const link = exportResult.querySelector<HTMLAnchorElement>(
          "[data-interchange-download]",
        );
        if (link) attachDownload(panel, link, result.document, context);
      } catch (error) {
        const code = errorCode(error);
        exportStatus.textContent = labels.error;
        exportResult.innerHTML = renderError(code, labels);
      } finally {
        exportButton.disabled = false;
        panel.removeAttribute("aria-busy");
      }
    });
  }

  const importHistoryStatus = panel.querySelector<HTMLElement>(
    "[data-interchange-history-status]",
  );
  const importHistoryList = panel.querySelector<HTMLElement>(
    "[data-interchange-history-list]",
  );
  const importHistoryDetail = panel.querySelector<HTMLElement>(
    "[data-interchange-history-detail]",
  );
  const importHistoryRefresh = panel.querySelector<HTMLButtonElement>(
    "[data-interchange-history-refresh]",
  );
  const loadImportHistory = async (): Promise<void> => {
    if (!importHistoryStatus || !importHistoryList || !importHistoryDetail) return;
    if (importHistoryRefresh) importHistoryRefresh.disabled = true;
    importHistoryStatus.textContent = labels.importHistoryLoading;
    importHistoryList.innerHTML = "";
    importHistoryDetail.innerHTML = "";
    try {
      const result = await client.listImportBatches();
      importHistoryList.innerHTML = renderInterchangeImportBatchList(result, labels);
      if (result.status === "not_configured") {
        importHistoryStatus.textContent = labels.importHistoryNotConfigured;
      } else {
        importHistoryStatus.textContent = "";
      }
      for (const button of importHistoryList.querySelectorAll<HTMLButtonElement>(
        "[data-interchange-batch-id]",
      )) {
        button.addEventListener("click", async () => {
          const batchId = button.dataset.interchangeBatchId;
          if (!batchId || !importHistoryStatus || !importHistoryDetail) return;
          button.disabled = true;
          importHistoryStatus.textContent = labels.importHistoryLoading;
          importHistoryDetail.innerHTML = "";
          try {
            const detail = await client.getImportBatch(batchId);
            importHistoryDetail.innerHTML = renderInterchangeImportBatchDetail(detail, labels);
            importHistoryStatus.textContent = "";
          } catch (error) {
            importHistoryStatus.textContent = labels.importHistoryFailed;
            importHistoryDetail.innerHTML = renderError(errorCode(error), labels);
          } finally {
            button.disabled = false;
          }
        });
      }
    } catch (error) {
      importHistoryStatus.textContent = labels.importHistoryFailed;
      importHistoryList.innerHTML = renderError(errorCode(error), labels);
    } finally {
      if (importHistoryRefresh) importHistoryRefresh.disabled = false;
    }
  };
  importHistoryRefresh?.addEventListener("click", () => {
    void loadImportHistory();
  });
  void loadImportHistory();

  const importForm = panel.querySelector<HTMLFormElement>(
    "[data-interchange-import-form]",
  );
  const input = panel.querySelector<HTMLTextAreaElement>(
    "[data-interchange-input]",
  );
  const fileInput = panel.querySelector<HTMLInputElement>(
    "[data-interchange-file]",
  );
  const importButton = panel.querySelector<HTMLButtonElement>(
    "[data-interchange-import]",
  );
  const importStatus = panel.querySelector<HTMLElement>(
    "[data-interchange-import-status]",
  );
  const importResult = panel.querySelector<HTMLElement>(
    "[data-interchange-import-result]",
  );
  if (importForm && input && importButton && importStatus && importResult) {
    const resetImport = () => {
      importStatus.textContent = "";
      importResult.innerHTML = "";
    };
    input.addEventListener("input", resetImport);
    fileInput?.addEventListener("change", async () => {
      const file = fileInput.files?.[0];
      if (!file) return;
      try {
        input.value = await file.text();
        resetImport();
      } catch {
        importStatus.textContent = labels.error;
        importResult.innerHTML = renderError("INTERCHANGE_FILE_READ_FAILED", labels);
      }
    });

    importForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const document = input.value;
      if (!document.trim()) {
        importStatus.textContent = labels.error;
        importResult.innerHTML = renderError("INTERCHANGE_IMPORT_EMPTY", labels);
        return;
      }
      importButton.disabled = true;
      panel.setAttribute("aria-busy", "true");
      importStatus.textContent = labels.importing;
      importResult.innerHTML = "";
      try {
        const result = await client.importDocument(document);
        importStatus.textContent = `${result.rows.length} ${labels.importReady}`;
        importResult.innerHTML = renderInterchangeImportResult(result, labels);
        await loadImportHistory();
      } catch (error) {
        const code = errorCode(error);
        importStatus.textContent = labels.error;
        importResult.innerHTML = renderError(code, labels);
      } finally {
        importButton.disabled = false;
        panel.removeAttribute("aria-busy");
      }
    });
  }
}
