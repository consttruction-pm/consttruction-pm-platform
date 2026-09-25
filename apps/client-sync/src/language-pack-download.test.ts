import assert from "node:assert/strict";
import test from "node:test";

import {
  LanguagePackDownloadService,
  type LanguagePackDownloadManifest,
} from "./language-pack-download.ts";

const manifest: LanguagePackDownloadManifest = {
  packageId: "construction-pm.language.fa",
  languageTag: "fa",
  version: "1.0.0",
  minAppVersion: "0.1.0",
  maxAppVersion: null,
  compressedSizeBytes: 3,
  downloadUri: "https://example.invalid/fa.zip",
  checksum: "sha256:test",
  signature: "signature",
};

test("downloads, verifies and reports progress", async () => {
  const phases: string[] = [];
  const service = new LanguagePackDownloadService(
    {
      async download(_uri, onChunk) {
        const data = new Uint8Array([1, 2, 3]);
        onChunk?.(new Uint8Array([1]));
        onChunk?.(new Uint8Array([2, 3]));
        return data;
      },
    },
    {
      async verify(artifact, received) {
        return artifact.length === 3 && received.packageId === manifest.packageId;
      },
    },
  );

  const result = await service.downloadVerified(manifest, (progress) => {
    phases.push(progress.phase);
  });

  assert.deepEqual([...result], [1, 2, 3]);
  assert.deepEqual(phases, ["downloading", "downloading", "downloading", "verifying", "cached"]);
});

test("rejects unverified downloads", async () => {
  const service = new LanguagePackDownloadService(
    {
      async download() {
        return new Uint8Array([1]);
      },
    },
    {
      async verify() {
        return false;
      },
    },
  );

  await assert.rejects(
    service.downloadVerified(manifest),
    /LANGUAGE_PACK_VERIFICATION_FAILED/,
  );
});
