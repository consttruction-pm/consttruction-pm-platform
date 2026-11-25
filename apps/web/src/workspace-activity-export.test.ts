import assert from "node:assert/strict";
import test from "node:test";

import type { ApiResult, ApiTransport, DownloadedBinary, ProjectContext } from "./client.js";
import {
  ACTIVITY_EXPORT_FILENAME_FALLBACK,
  activitiesExportPath,
  downloadActivityWorkbook,
  exportFilename,
  sha256Hex,
} from "./workspace-activity-export.js";

const CONTEXT: ProjectContext = { tenant_id: "t1", project_id: "project/1", revision: 7 };

async function expectedDigest(text: string): Promise<string> {
  const digest = await sha256Hex(new TextEncoder().encode(text).buffer as ArrayBuffer);
  assert.ok(digest, "test runtime must expose WebCrypto SHA-256");
  return digest;
}

function transportReturning(
  binary: Partial<DownloadedBinary>,
  body = "xlsx-bytes",
): ApiTransport {
  return {
    get: async () => ({ ok: false, error: { code: "UNUSED", retryable: false, message_key: "error.api", available_actions: [] } }),
    post: async () => ({ ok: false, error: { code: "UNUSED", retryable: false, message_key: "error.api", available_actions: [] } }),
    download: async (path: string): Promise<ApiResult<DownloadedBinary>> => {
      assert.equal(path, activitiesExportPath(CONTEXT));
      return {
        ok: true,
        data: {
          blob: new Blob([body]),
          contentType: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
          contentDisposition: 'attachment; filename="activities.xlsx"',
          contentSha256: "",
          documentVersion: "",
          ...binary,
        },
      };
    },
  } as ApiTransport;
}

test("activities export targets the authoritative exchange workbook route", () => {
  // The dataset and format are server contracts, not presentation choices.
  assert.equal(
    activitiesExportPath(CONTEXT),
    "/api/projects/project%2F1/exchange/export?dataset=activities&format=xlsx",
  );
});

test("export filename prefers the server disposition and never keeps a path", () => {
  assert.equal(exportFilename('attachment; filename="activities.xlsx"'), "activities.xlsx");
  assert.equal(
    exportFilename("attachment; filename*=UTF-8''%D9%81%D8%B9%D8%A7%D9%84%DB%8C%D8%AA.xlsx"),
    "فعالیت.xlsx",
  );
  assert.equal(exportFilename(""), ACTIVITY_EXPORT_FILENAME_FALLBACK);
  assert.equal(exportFilename('attachment; filename="../../etc/passwd"'), ".._.._etc_passwd");
  // A hostile extended form must not escape the download name either.
  assert.equal(
    exportFilename("attachment; filename*=UTF-8''..%2F..%2Fetc%2Fpasswd"),
    ".._.._etc_passwd",
  );
  assert.equal(exportFilename('attachment; filename="."'), ACTIVITY_EXPORT_FILENAME_FALLBACK);
});

test("a workbook whose bytes match the declared digest is returned for saving", async () => {
  const digest = await expectedDigest("xlsx-bytes");
  const result = await downloadActivityWorkbook(transportReturning({ contentSha256: digest }), CONTEXT);
  assert.equal(result.ok, true);
  if (!result.ok) return;
  assert.equal(result.data.filename, "activities.xlsx");
  assert.equal(result.data.byteSize, 10);
  assert.equal(result.data.sha256, digest);
});

test("a digest mismatch is reported and the bytes are not offered", async () => {
  const result = await downloadActivityWorkbook(
    transportReturning({ contentSha256: "0".repeat(64) }),
    CONTEXT,
  );
  assert.equal(result.ok, false);
  if (result.ok) return;
  assert.equal(result.error.code, "ACTIVITY_EXPORT_DIGEST_MISMATCH");
});

test("an empty body never becomes a saved workbook", async () => {
  const result = await downloadActivityWorkbook(transportReturning({}, ""), CONTEXT);
  assert.equal(result.ok, false);
  if (result.ok) return;
  assert.equal(result.error.code, "ACTIVITY_EXPORT_EMPTY");
});

test("a transport without binary download reports the unsupported seam", async () => {
  const transport = {
    get: async () => ({ ok: false, error: { code: "UNUSED", retryable: false, message_key: "error.api", available_actions: [] } }),
    post: async () => ({ ok: false, error: { code: "UNUSED", retryable: false, message_key: "error.api", available_actions: [] } }),
  } as unknown as ApiTransport;
  const result = await downloadActivityWorkbook(transport, CONTEXT);
  assert.equal(result.ok, false);
  if (result.ok) return;
  assert.equal(result.error.code, "TRANSPORT_DOWNLOAD_UNSUPPORTED");
});

test("server failures surface their own code instead of a fabricated success", async () => {
  const transport = {
    get: async () => ({ ok: false, error: { code: "UNUSED", retryable: false, message_key: "error.api", available_actions: [] } }),
    post: async () => ({ ok: false, error: { code: "UNUSED", retryable: false, message_key: "error.api", available_actions: [] } }),
    download: async () => ({
      ok: false as const,
      error: { code: "EXCHANGE_DATASET_NOT_FOUND", retryable: false, message_key: "error.request.invalid", available_actions: [] },
    }),
  } as unknown as ApiTransport;
  const result = await downloadActivityWorkbook(transport, CONTEXT);
  assert.equal(result.ok, false);
  if (result.ok) return;
  assert.equal(result.error.code, "EXCHANGE_DATASET_NOT_FOUND");
});
