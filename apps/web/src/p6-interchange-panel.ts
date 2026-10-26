import type { ApiTransport, ProjectContext } from "./client.js";
import {
  createP6InterchangeClient,
  type InterchangeExportDocument,
  type InterchangeExportResult,
  type InterchangeImportResult,
  type InterchangeImportRow,
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
    <div data-interchange-import-result></div>`;
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
  result: InterchangeImportResult,
  labels: InterchangePanelLabels,
): string {
  if (result.rows.length === 0) {
    return `<div class="cp-interchange-success"><p role="status">${escapeHtml(
      labels.importNoRows,
    )}</p></div>`;
  }
  const rendered = result.rows.slice(0, MAX_RENDERED_ROWS);
  const truncated =
    result.rows.length > MAX_RENDERED_ROWS
      ? `<p class="cp-interchange-meta">${escapeHtml(labels.showingRows)}</p>`
      : "";
  return `<div class="cp-interchange-success">
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
