export type LanguagePackManifest = {
  package_id: string; language_tag: string; version: string;
  app_compatibility: { min_version: string; max_version: string | null };
  artifact: { format: "zip" | "zstd" | "tar.zst"; compressed_size_bytes: number; download_uri: string; delta_from: string | null };
  resources: { translation: string; glossary: string; help: string; reports: string; voice_input: string | null; voice_output: string | null; offline_ai_model: string | null };
  integrity: { checksum: string; signature: string; signing_key_id: string | null };
  capabilities: { ui: boolean; help: boolean; ai_text: boolean; voice_input: boolean; voice_output: boolean; offline_ai: boolean };
  typography: {
    font_family: string;
    fallback_families: string[];
    font_style: "normal" | "italic" | "oblique";
    font_weight: number;
    line_height: string;
    letter_spacing: string;
    font_feature_settings: string;
    font_variant_ligatures: string;
    font_kerning: "auto" | "normal" | "none";
    font_resources: readonly {
      family: string;
      uri: string;
      format: "woff2" | "woff" | "ttf" | "otf";
      weight: number;
      style: "normal" | "italic" | "oblique";
      unicode_range?: string;
    }[];
  };
};

const REQUIRED = ["package_id", "language_tag", "version", "app_compatibility", "artifact", "resources", "integrity", "capabilities", "typography"] as const;

export function validateLanguagePackManifest(value: unknown): LanguagePackManifest {
  if (!isRecord(value) || REQUIRED.some((key) => !(key in value))) throw new Error("INVALID_LANGUAGE_PACK_MANIFEST");
  rejectUnknown(value, REQUIRED, "INVALID_LANGUAGE_PACK_MANIFEST");
  requireString(value.package_id, "INVALID_LANGUAGE_PACK_PACKAGE_ID");
  requireString(value.language_tag, "INVALID_LANGUAGE_PACK_LANGUAGE_TAG");
  requirePattern(value.version, /^\d+\.\d+\.\d+$/, "INVALID_LANGUAGE_PACK_VERSION");

  const compatibility = requireRecord(value.app_compatibility, "INVALID_LANGUAGE_PACK_COMPATIBILITY");
  requireString(compatibility.min_version, "INVALID_LANGUAGE_PACK_COMPATIBILITY");
  requireStringOrNull(compatibility.max_version, "INVALID_LANGUAGE_PACK_COMPATIBILITY");
  rejectUnknown(compatibility, ["min_version", "max_version"], "INVALID_LANGUAGE_PACK_COMPATIBILITY");

  const artifact = requireRecord(value.artifact, "INVALID_LANGUAGE_PACK_ARTIFACT");
  if (artifact.format !== "zip" && artifact.format !== "zstd" && artifact.format !== "tar.zst") throw new Error("INVALID_LANGUAGE_PACK_ARTIFACT");
  const compressedSize = artifact.compressed_size_bytes;
  if (typeof compressedSize !== "number" || !Number.isSafeInteger(compressedSize) || compressedSize < 0) throw new Error("INVALID_LANGUAGE_PACK_ARTIFACT");
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

  const typography = requireRecord(value.typography, "INVALID_LANGUAGE_PACK_TYPOGRAPHY");
  requireString(typography.font_family, "INVALID_LANGUAGE_PACK_TYPOGRAPHY");
  if (!Array.isArray(typography.fallback_families) || typography.fallback_families.some((font) => typeof font !== "string" || font.length === 0)) throw new Error("INVALID_LANGUAGE_PACK_TYPOGRAPHY");
  if (typography.font_style !== "normal" && typography.font_style !== "italic" && typography.font_style !== "oblique") throw new Error("INVALID_LANGUAGE_PACK_TYPOGRAPHY");
  if (typeof typography.font_weight !== "number" || !Number.isInteger(typography.font_weight) || typography.font_weight < 1 || typography.font_weight > 1000) throw new Error("INVALID_LANGUAGE_PACK_TYPOGRAPHY");
  requireString(typography.line_height, "INVALID_LANGUAGE_PACK_TYPOGRAPHY");
  if (typeof typography.letter_spacing !== "string" || typeof typography.font_feature_settings !== "string" || typeof typography.font_variant_ligatures !== "string") throw new Error("INVALID_LANGUAGE_PACK_TYPOGRAPHY");
  if (typography.font_kerning !== "auto" && typography.font_kerning !== "normal" && typography.font_kerning !== "none") throw new Error("INVALID_LANGUAGE_PACK_TYPOGRAPHY");
  if (!Array.isArray(typography.font_resources)) throw new Error("INVALID_LANGUAGE_PACK_TYPOGRAPHY");
  for (const font of typography.font_resources) {
    if (!isRecord(font)) throw new Error("INVALID_LANGUAGE_PACK_TYPOGRAPHY");
    if (typeof font.family !== "string" || typeof font.uri !== "string" || typeof font.format !== "string" || typeof font.weight !== "number" || !Number.isInteger(font.weight) || font.weight < 1 || font.weight > 1000 || typeof font.style !== "string") throw new Error("INVALID_LANGUAGE_PACK_TYPOGRAPHY");
    try { new URL(font.uri); } catch { throw new Error("INVALID_LANGUAGE_PACK_TYPOGRAPHY"); }
    if (!["woff2", "woff", "ttf", "otf"].includes(font.format)) throw new Error("INVALID_LANGUAGE_PACK_TYPOGRAPHY");
    if (!["normal", "italic", "oblique"].includes(font.style)) throw new Error("INVALID_LANGUAGE_PACK_TYPOGRAPHY");
    if (font.unicode_range !== undefined && typeof font.unicode_range !== "string") throw new Error("INVALID_LANGUAGE_PACK_TYPOGRAPHY");
    rejectUnknown(font, ["family", "uri", "format", "weight", "style", "unicode_range"], "INVALID_LANGUAGE_PACK_TYPOGRAPHY");
  }
  rejectUnknown(typography, ["font_family", "fallback_families", "font_style", "font_weight", "line_height", "letter_spacing", "font_feature_settings", "font_variant_ligatures", "font_kerning", "font_resources"], "INVALID_LANGUAGE_PACK_TYPOGRAPHY");
  return value as LanguagePackManifest;
}

function isRecord(value: unknown): value is Record<string, unknown> { return typeof value === "object" && value !== null && !Array.isArray(value); }
function requireRecord(value: unknown, error: string): Record<string, unknown> { if (!isRecord(value)) throw new Error(error); return value; }
function requireString(value: unknown, error: string): asserts value is string { if (typeof value !== "string" || value.length === 0) throw new Error(error); }
function requireStringOrNull(value: unknown, error: string): asserts value is string | null { if (value !== null && (typeof value !== "string" || value.length === 0)) throw new Error(error); }
function requirePattern(value: unknown, pattern: RegExp, error: string): asserts value is string { requireString(value, error); if (!pattern.test(value)) throw new Error(error); }
function rejectUnknown(record: Record<string, unknown>, allowed: readonly string[], error: string): void { if (Object.keys(record).some((key) => !allowed.includes(key))) throw new Error(error); }
