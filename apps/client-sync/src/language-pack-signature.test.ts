import assert from "node:assert/strict";
import { webcrypto } from "node:crypto";
import test from "node:test";

import {
  LanguagePackSigningKeyRegistry,
  RegistryBackedLanguagePackSignatureVerifier,
  canonicalSigningMessage,
  type LanguagePackSigningKey,
} from "./language-pack-signature.js";
import type { LanguagePackDownloadManifest } from "./language-pack-download.js";

const subtle = webcrypto.subtle;

function base64Url(bytes: Uint8Array): string {
  return Buffer.from(bytes)
    .toString("base64")
    .replaceAll("+", "-")
    .replaceAll("/", "_")
    .replaceAll("=", "");
}

async function makeKeyPair(): Promise<{
  publicKey: string;
  privateKey: CryptoKey;
}> {
  const pair = await subtle.generateKey(
    { name: "Ed25519" },
    true,
    ["sign", "verify"],
  );
  const publicKey = new Uint8Array(
    await subtle.exportKey("raw", pair.publicKey),
  );
  return { publicKey: base64Url(publicKey), privateKey: pair.privateKey };
}

async function signManifest(
  privateKey: CryptoKey,
  manifest: LanguagePackDownloadManifest,
): Promise<string> {
  const signature = new Uint8Array(
    await subtle.sign(
      { name: "Ed25519" },
      privateKey,
      new TextEncoder().encode(canonicalSigningMessage(manifest)),
    ),
  );
  return "ed25519.v1:key-2026:" + base64Url(signature);
}

test("registry-backed language pack signature verifier accepts a valid rotated key", async () => {
  const keyPair = await makeKeyPair();
  const key: LanguagePackSigningKey = {
    keyId: "key-2026",
    algorithm: "Ed25519",
    publicKeyBase64Url: keyPair.publicKey,
    status: "active",
    notBefore: "2026-01-01T00:00:00Z",
    notAfter: "2027-01-01T00:00:00Z",
  };
  const artifact = new TextEncoder().encode("language-pack");
  const checksumBytes = new Uint8Array(
    await subtle.digest("SHA-256", artifact),
  );
  const checksum =
    "sha256:" +
    [...checksumBytes]
      .map((value) => value.toString(16).padStart(2, "0"))
      .join("");

  const manifest: LanguagePackDownloadManifest = {
    packageId: "construction-pm.language.fa",
    languageTag: "fa",
    version: "1.2.0",
    minAppVersion: "0.1.0",
    maxAppVersion: null,
    compressedSizeBytes: artifact.byteLength,
    downloadUri: "https://example.invalid/fa.zip",
    checksum,
    signature: "",
    resourcePaths: {
      translation: "translations.json",
      glossary: "glossary.json",
      help: "help.json",
      reports: "reports.json",
    },
  };
  manifest.signature = await signManifest(keyPair.privateKey, manifest);

  const verifier = new RegistryBackedLanguagePackSignatureVerifier(
    new LanguagePackSigningKeyRegistry([key]),
    {
      async verifyEd25519(publicKey, signature, message) {
        const imported = await subtle.importKey(
          "raw",
          publicKey,
          { name: "Ed25519" },
          false,
          ["verify"],
        );
        return subtle.verify(
          { name: "Ed25519" },
          imported,
          signature,
          message,
        );
      },
    },
    () => new Date("2026-09-25T00:00:00Z"),
  );

  assert.equal(await verifier.verify(artifact, manifest), true);
});

test("signature verification rejects revoked keys", async () => {
  const keyPair = await makeKeyPair();
  const key: LanguagePackSigningKey = {
    keyId: "key-revoked",
    algorithm: "Ed25519",
    publicKeyBase64Url: keyPair.publicKey,
    status: "revoked",
  };
  const registry = new LanguagePackSigningKeyRegistry([key]);

  assert.throws(
    () => registry.resolve("key-revoked"),
    /LANGUAGE_PACK_SIGNING_KEY_REVOKED/,
  );
});

test("signature message binds resource paths", () => {
  const base: LanguagePackDownloadManifest = {
    packageId: "construction-pm.language.en",
    languageTag: "en",
    version: "1.0.0",
    minAppVersion: "0.1.0",
    maxAppVersion: null,
    compressedSizeBytes: 10,
    downloadUri: "https://example.invalid/en.zip",
    checksum: "sha256:" + "a".repeat(64),
    signature: "ed25519.v1:key:placeholder",
    resourcePaths: {
      translation: "translations.json",
      glossary: "glossary.json",
      help: "help.json",
      reports: "reports.json",
    },
  };
  const changed = {
    ...base,
    resourcePaths: {
      ...base.resourcePaths!,
      reports: "different-reports.json",
    },
  };

  assert.notEqual(
    canonicalSigningMessage(base),
    canonicalSigningMessage(changed),
  );
});
