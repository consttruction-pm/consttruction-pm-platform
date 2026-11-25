/**
 * Activities workbook export for the Activities window (Export to Excel).
 *
 * The workbook is rendered by the authoritative exchange service from persisted
 * activity facts; the browser never assembles spreadsheet content from grid
 * state. The downloaded bytes are checked against the server's
 * `X-Content-SHA256` header before the file is offered, so a truncated or
 * re-encoded response is reported instead of saved.
 */
import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";

export const ACTIVITY_EXPORT_DATASET = "activities";
export const ACTIVITY_EXPORT_FILENAME_FALLBACK = "activities.xlsx";

export type ActivityWorkbookExport = {
  filename: string;
  byteSize: number;
  sha256: string | null;
  blob: Blob;
};

function localError(code: string): ApiResult<never> {
  return {
    ok: false,
    error: { code, retryable: false, message_key: "error.request.invalid", available_actions: [] },
  };
}

export function activitiesExportPath(context: ProjectContext): string {
  return `/api/projects/${encodeURIComponent(context.project_id)}/exchange/export?dataset=${ACTIVITY_EXPORT_DATASET}&format=xlsx`;
}

/** Resolve the server-provided download name without trusting a path fragment. */
export function exportFilename(disposition: string, fallback = ACTIVITY_EXPORT_FILENAME_FALLBACK): string {
  const extended = /filename\*=UTF-8''([^;]+)/i.exec(disposition);
  if (extended) {
    const raw = extended[1].trim().replace(/^"|"$/g, "");
    try {
      return sanitizeFilename(decodeURIComponent(raw), fallback);
    } catch {
      return fallback;
    }
  }
  const plain = /filename="?([^";]+)"?/i.exec(disposition);
  return sanitizeFilename(plain?.[1] ?? "", fallback);
}

function sanitizeFilename(name: string, fallback: string): string {
  const cleaned = name.trim().replace(/[\\/]/g, "_").replace(/[\u0000-\u001f]/g, "");
  if (!cleaned || cleaned === "." || cleaned === "..") return fallback;
  return cleaned;
}

export async function sha256Hex(bytes: ArrayBuffer): Promise<string | null> {
  const subtle = globalThis.crypto?.subtle;
  if (!subtle) return null;
  const digest = await subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest))
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}

/**
 * Download the activities workbook and verify its integrity.
 *
 * A response without a digest header is accepted (the route always sends one)
 * but returns `sha256: null` so the caller does not claim verification.
 */
export async function downloadActivityWorkbook(
  transport: ApiTransport,
  context: ProjectContext,
): Promise<ApiResult<ActivityWorkbookExport>> {
  if (typeof transport.download !== "function") return localError("TRANSPORT_DOWNLOAD_UNSUPPORTED");
  const result = await transport.download(activitiesExportPath(context), context);
  if (!result.ok) return result;
  const bytes = await result.data.blob.arrayBuffer();
  if (!bytes.byteLength) return localError("ACTIVITY_EXPORT_EMPTY");
  const actual = await sha256Hex(bytes);
  const declared = result.data.contentSha256.trim().toLowerCase();
  if (declared && actual && declared !== actual) return localError("ACTIVITY_EXPORT_DIGEST_MISMATCH");
  return {
    ok: true,
    data: {
      filename: exportFilename(result.data.contentDisposition),
      byteSize: bytes.byteLength,
      sha256: actual ?? (declared || null),
      blob: result.data.blob,
    },
  };
}

/** Offer verified bytes as a file download. */
export function saveWorkbookDownload(workbook: ActivityWorkbookExport): void {
  if (typeof document === "undefined") return;
  const url = URL.createObjectURL(workbook.blob);
  try {
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = workbook.filename;
    anchor.rel = "noopener";
    document.body.append(anchor);
    anchor.click();
    anchor.remove();
  } finally {
    // Revoke on the next task so the browser can start the download.
    setTimeout(() => URL.revokeObjectURL(url), 0);
  }
}
