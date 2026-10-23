import type { WorkspaceLocale } from "./workspace-model.js";
import type { LanguagePackManifest } from "../../client-sync/src/language-pack-manifest.js";
import type { LanguagePackResource } from "../../client-sync/src/language-pack-resource-validation.js";

export type WorkspaceTextDirection = "ltr" | "rtl";
export type WorkspaceLocaleDefinition = {
  locale: WorkspaceLocale;
  displayName: string;
  direction: WorkspaceTextDirection;
  translations: Readonly<Record<string, string>>;
};

const localeDefinitions = new Map<string, WorkspaceLocaleDefinition>([
  ["en", { locale: "en", displayName: "English", direction: "ltr", translations: {} }],
  ["fa", { locale: "fa", displayName: "فارسی", direction: "rtl", translations: {} }],
]);

/** Register translations from a verified, activated language pack. Keys are stable IDs, not English labels. */
export function registerWorkspaceLocale(definition: WorkspaceLocaleDefinition): void {
  const locale = definition.locale.trim();
  if (!locale || !/^[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$/.test(locale)) {
    throw new Error("INVALID_WORKSPACE_LOCALE");
  }
  if (!definition.displayName.trim()) throw new Error("INVALID_WORKSPACE_LOCALE_DISPLAY_NAME");
  if (definition.direction !== "ltr" && definition.direction !== "rtl") {
    throw new Error("INVALID_WORKSPACE_LOCALE_DIRECTION");
  }
  for (const [key, value] of Object.entries(definition.translations)) {
    if (!key.trim() || typeof value !== "string" || !value.trim()) {
      throw new Error("INVALID_WORKSPACE_TRANSLATION");
    }
  }
  localeDefinitions.set(locale, Object.freeze({
    locale,
    displayName: definition.displayName.trim(),
    direction: definition.direction,
    translations: Object.freeze({ ...definition.translations }),
  }));
}

/** Parse the versioned UI-translation resource declared by a language-pack manifest. */
export function readWorkspaceLocaleDefinitionFromPack(
  manifest: LanguagePackManifest,
  resources: readonly LanguagePackResource[],
): WorkspaceLocaleDefinition | null {
  if (!manifest.capabilities.ui) return null;
  const resource = resources.find((item) => item.path === manifest.resources.translation);
  if (!resource) throw new Error("WORKSPACE_LOCALE_TRANSLATION_RESOURCE_MISSING");
  let value: unknown;
  try {
    value = JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(resource.bytes));
  } catch {
    throw new Error("INVALID_WORKSPACE_LOCALE_TRANSLATION_JSON");
  }
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new Error("INVALID_WORKSPACE_LOCALE_TRANSLATION_RESOURCE");
  }
  const record = value as Record<string, unknown>;
  if (record.schema_version !== "cubi-ui-translations.v1") {
    throw new Error("UNSUPPORTED_WORKSPACE_LOCALE_TRANSLATION_SCHEMA");
  }
  if (typeof record.display_name !== "string" || !record.display_name.trim()) {
    throw new Error("INVALID_WORKSPACE_LOCALE_DISPLAY_NAME");
  }
  if (record.direction !== "ltr" && record.direction !== "rtl") {
    throw new Error("INVALID_WORKSPACE_LOCALE_DIRECTION");
  }
  if (!record.translations || typeof record.translations !== "object" || Array.isArray(record.translations)) {
    throw new Error("INVALID_WORKSPACE_TRANSLATIONS");
  }
  const translations: Record<string, string> = {};
  for (const [key, translated] of Object.entries(record.translations as Record<string, unknown>)) {
    if (!key.trim() || typeof translated !== "string" || !translated.trim()) {
      throw new Error("INVALID_WORKSPACE_TRANSLATION");
    }
    translations[key] = translated;
  }
  return {
    locale: manifest.language_tag,
    displayName: record.display_name,
    direction: record.direction,
    translations,
  };
}

export function getWorkspaceLocaleDefinition(locale: WorkspaceLocale): WorkspaceLocaleDefinition | undefined {
  return localeDefinitions.get(locale);
}

export function getWorkspaceLocaleDirection(locale: WorkspaceLocale): WorkspaceTextDirection {
  return localeDefinitions.get(locale)?.direction ?? "ltr";
}

export function getWorkspaceLocaleDisplayName(locale: WorkspaceLocale): string {
  return localeDefinitions.get(locale)?.displayName ?? locale;
}

export function getAvailableWorkspaceLocales(): readonly WorkspaceLocale[] {
  return [...localeDefinitions.keys()];
}

export function translateWorkspaceText(locale: WorkspaceLocale, key: string, fallback: string): string {
  return localeDefinitions.get(locale)?.translations[key] ?? fallback;
}
