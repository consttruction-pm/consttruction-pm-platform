export type LanguagePackManifest = {
  package_id: string; language_tag: string; version: string;
  app_compatibility: { min_version: string; max_version: string | null };
  artifact: { format: "zip" | "zstd" | "tar.zst"; compressed_size_bytes: number; download_uri: string; delta_from: string | null };
  resources: { translation: string; glossary: string; help: string; reports: string; voice_input: string | null; voice_output: string | null; offline_ai_model: string | null };
  integrity: { checksum: string; signature: string; signing_key_id: string | null };
  capabilities: { ui: boolean; help: boolean; ai_text: boolean; voice_input: boolean; voice_output: boolean; offline_ai: boolean };
};

const REQUIRED = ["package_id", "language_tag", "version", "app_compatibility", "artifact", "resources", "integrity", "capabilities"] as const;

export function validateLanguagePackManifest(value: unknown): LanguagePackManifest {
  if (!isRecord(value) || REQUIRED.some((key) => !(key in value))) throw new Error("INVALID_LANGUAGE_PACK_MANIFEST");
  requireString(value.package_id, "INVALID_LANGUAGE_PACK_PACKAGE_ID");
  requireString(value.language_tag, "INVALID_LANGUAGE_PACK_LANGUAGE_TAG");
  requirePattern(value.version, /^\d+\.\d+\.\d+$/, "INVALID_LANGUAGE_PACK_VERSION");

  const compatibility = requireRecord(value.app_compatibility, "INVALID_LANGUAGE_PACK_COMPATIBILITY");
  requireString(compatibility.min_version, "INVALID_LANGUAGE_PACK_COMPATIBILITY");
  requireStringOrNull(compatibility.max_version, "INVALID_LANGUAGE_PACK_COMPATIBILITY");
  rejectUnknown(compatibility, ["min_version", "max_version"], "INVALID_LANGUAGE_PACK_COMPATIBILITY");

  const artifact = requireRecord(value.artifact, "INVALID_LANGUAGE_PACK_ARTIFACT");
  if (artifact.format !== "zip" && artifact.format !== "zstd" && artifact.format !== "tar.zst") throw new Error("INVALID_LANGUAGE_PACK_ARTIFACT");
  if (!Number.isSafeInteger(artifact.compressed_size_bytes) || artifact.compressed_size_bytes < 0) throw new Error("INVALID_LANGUAGE_PACK_ARTIFACT");
  requireString(artifact.download_uri, "INVALID_LANGUAGE_PACK_ARTIFACT");
  try { new URL(artifact.download_uri); } catch { throw new Error("INVALID_LANGUAGE_PACK_ARTIFACT"); }
  requireStringOrNull(artifact.delta_from, "INVALID_LANGUAGE_PACK_ARTIFACT");
  rejectUnknown(artifact, ["format", "compressed_size_bytes", "download_uri", "delta_from"], "INVALID_LANGUAGE_PACK_ARTIFACT");

  const resources = requireRecord(value.resources, "INVALID_LANGUAGE_PACK_RESOURCES");
  for (const key of ["translation", "glossary", "help", "reports"] as const) requireString(resources[key], "INVALID_LANGUAGE_PACK_RESOURCES");
  for (const key of ["voice_input", "voice_output", "offline_ai_model"] as const) requireStringOrNull(resources[key], "INVALID_LANGUAGE_PACK_RESOURCES");
  rejectUnknown(resources, ["translation", "glossary", "help", "reports", "voice_input", "voice_output", "offline_ai_model"], "INVALID_LANGUAGE_PACK_RESOURCES");

  const integrity = requireRecord(value.integrity, "INVALID_LANGUAGE_PACK_INTEGRITY");
  requirePattern(integrity.checksum, /^sha256:[0-9a-fA-F]{64}$/, "INVALID_LANGUAGE_PACK_CHECKSUM");
  requireString(integrity.signature, "INVALID_LANGUAGE_PACK_SIGNATURE");
  requireStringOrNull(integrity.signing_key_id, "INVALID_LANGUAGE_PACK_INTEGRITY");
  rejectUnknown(integrity, ["checksum", "signature", "signing_key_id"], "INVALID_LANGUAGE_PACK_INTEGRITY");

  const capabilities = requireRecord(value.capabilities, "INVALID_LANGUAGE_PACK_CAPABILITIES");
  for (const key of ["ui", "help", "ai_text", "voice_input", "voice_output", "offline_ai"] as const) {
    if (typeof capabilities[key] !== "boolean") throw new Error("INVALID_LANGUAGE_PACK_CAPABILITIES");
  }
  rejectUnknown(capabilities, ["ui", "help", "ai_text", "voice_input", "voice_output", "offline_ai"], "INVALID_LANGUAGE_PACK_CAPABILITIES");
  return value as LanguagePackManifest;
}

function isRecord(value: unknown): value is Record<string, unknown> { return typeof value === "object" && value !== null && !Array.isArray(value); }
function requireRecord(value: unknown, error: string): Record<string, unknown> { if (!isRecord(value)) throw new Error(error); return value; }
function requireString(value: unknown, error: string): asserts value is string { if (typeof value !== "string" || value.length === 0) throw new Error(error); }
function requireStringOrNull(value: unknown, error: string): asserts value is string | null { if (value !== null && (typeof value !== "string" || value.length === 0)) throw new Error(error); }
function requirePattern(value: unknown, pattern: RegExp, error: string): asserts value is string { requireString(value, error); if (!pattern.test(value)) throw new Error(error); }
function rejectUnknown(record: Record<string, unknown>, allowed: readonly string[], error: string): void { if (Object.keys(record).some((key) => !allowed.includes(key))) throw new Error(error); }
