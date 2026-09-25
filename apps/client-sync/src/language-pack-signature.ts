import type { LanguagePackDownloadManifest, LanguagePackVerifier } from "./language-pack-download.js";

export type LanguagePackSigningKeyStatus = "active" | "retired" | "revoked";

export type LanguagePackSigningKey = {
  keyId: string;
  algorithm: "Ed25519";
  publicKeyBase64Url: string;
  status: LanguagePackSigningKeyStatus;
  notBefore?: string | null;
  notAfter?: string | null;
};

export interface LanguagePackSignatureCrypto {
  digestSha256(data: Uint8Array): Promise<Uint8Array>;
  verifyEd25519(
    publicKey: Uint8Array,
    signature: Uint8Array,
    message: Uint8Array,
  ): Promise<boolean>;
}

export class LanguagePackSigningKeyRegistry {
  private readonly keys = new Map<string, LanguagePackSigningKey>();

  constructor(keys: readonly LanguagePackSigningKey[]) {
    for (const key of keys) {
      validateKey(key);
      if (this.keys.has(key.keyId)) {
        throw new Error("DUPLICATE_LANGUAGE_PACK_SIGNING_KEY_ID");
      }
      this.keys.set(key.keyId, Object.freeze({ ...key }));
    }
  }

  resolve(keyId: string, now: Date = new Date()): LanguagePackSigningKey {
    const key = this.keys.get(keyId);
    if (!key) throw new Error("LANGUAGE_PACK_SIGNING_KEY_NOT_FOUND");
    if (key.status === "revoked") {
      throw new Error("LANGUAGE_PACK_SIGNING_KEY_REVOKED");
    }

    const timestamp = now.getTime();
    if (key.notBefore && timestamp < parseTime(key.notBefore)) {
      throw new Error("LANGUAGE_PACK_SIGNING_KEY_NOT_YET_VALID");
    }
    if (key.notAfter && timestamp > parseTime(key.notAfter)) {
      throw new Error("LANGUAGE_PACK_SIGNING_KEY_EXPIRED");
    }

    return key;
  }
}

export class RegistryBackedLanguagePackSignatureVerifier
  implements LanguagePackVerifier
{
  constructor(
    private readonly registry: LanguagePackSigningKeyRegistry,
    private readonly crypto: LanguagePackSignatureCrypto,
    private readonly clock: () => Date = () => new Date(),
  ) {}

  async verify(
    artifact: Uint8Array,
    manifest: LanguagePackDownloadManifest,
  ): Promise<boolean> {
    if (!manifest.signature.startsWith("ed25519.v1:")) return false;
    if (!manifest.checksum.startsWith("sha256:")) return false;
    if (
      manifest.compressedSizeBytes !== artifact.byteLength
    ) {
      return false;
    }

    const digest = await this.crypto.digestSha256(artifact);
    const checksum = [...digest]
      .map((value) => value.toString(16).padStart(2, "0"))
      .join("");
    if (
      checksum.toLowerCase() !==
      manifest.checksum.slice("sha256:".length).toLowerCase()
    ) {
      return false;
    }

    const parsed = parseSignature(manifest.signature);
    const key = this.registry.resolve(parsed.keyId, this.clock());
    if (key.algorithm !== "Ed25519") return false;

    const signedMessage = canonicalSigningMessage(manifest);
    return this.crypto.verifyEd25519(
      decodeBase64Url(key.publicKeyBase64Url),
      parsed.signature,
      new TextEncoder().encode(signedMessage),
    );
  }
}

export function canonicalSigningMessage(
  manifest: LanguagePackDownloadManifest,
): string {
  const resource = manifest.resourcePaths;
  return [
    "construction-pm-language-pack-signature-v1",
    "package_id=" + canonicalField(manifest.packageId),
    "language_tag=" + canonicalField(manifest.languageTag),
    "version=" + canonicalField(manifest.version),
    "min_app_version=" + canonicalField(manifest.minAppVersion),
    "max_app_version=" + canonicalField(manifest.maxAppVersion ?? ""),
    "compressed_size_bytes=" + String(manifest.compressedSizeBytes),
    "checksum=" + canonicalField(manifest.checksum),
    "resource_translation=" + canonicalField(resource?.translation ?? ""),
    "resource_glossary=" + canonicalField(resource?.glossary ?? ""),
    "resource_help=" + canonicalField(resource?.help ?? ""),
    "resource_reports=" + canonicalField(resource?.reports ?? ""),
  ].join("\n");
}

function parseSignature(value: string): {
  keyId: string;
  signature: Uint8Array;
} {
  const parts = value.split(":");
  if (parts.length !== 3 || parts[0] !== "ed25519.v1" || !parts[1] || !parts[2]) {
    throw new Error("INVALID_LANGUAGE_PACK_SIGNATURE");
  }
  return {
    keyId: parts[1]!,
    signature: decodeBase64Url(parts[2]!),
  };
}

function decodeBase64Url(value: string): Uint8Array {
  if (!/^[A-Za-z0-9_-]*$/.test(value) || value.length % 4 === 1) {
    throw new Error("INVALID_LANGUAGE_PACK_SIGNATURE_ENCODING");
  }

  const alphabet =
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";
  const output: number[] = [];
  let buffer = 0;
  let bits = 0;

  for (const character of value) {
    const digit = alphabet.indexOf(character);
    if (digit < 0) {
      throw new Error("INVALID_LANGUAGE_PACK_SIGNATURE_ENCODING");
    }
    buffer = (buffer << 6) | digit;
    bits += 6;
    if (bits >= 8) {
      bits -= 8;
      output.push((buffer >>> bits) & 0xff);
      buffer &= (1 << bits) - 1;
    }
  }

  return new Uint8Array(output);
}

async function sha256Hex(bytes: Uint8Array): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(digest)]
    .map((value) => value.toString(16).padStart(2, "0"))
    .join("");
}

function validateKey(key: LanguagePackSigningKey): void {
  if (!key.keyId || key.algorithm !== "Ed25519" || !key.publicKeyBase64Url) {
    throw new Error("INVALID_LANGUAGE_PACK_SIGNING_KEY");
  }
  if (key.notBefore) parseTime(key.notBefore);
  if (key.notAfter) parseTime(key.notAfter);
  const bytes = decodeBase64Url(key.publicKeyBase64Url);
  if (bytes.byteLength !== 32) {
    throw new Error("INVALID_ED25519_PUBLIC_KEY_LENGTH");
  }
}

function parseTime(value: string): number {
  const time = Date.parse(value);
  if (!Number.isFinite(time)) {
    throw new Error("INVALID_LANGUAGE_PACK_SIGNING_KEY_TIME");
  }
  return time;
}

function canonicalField(value: string): string {
  return value.replaceAll("\r", "\\r").replaceAll("\n", "\\n");
}
