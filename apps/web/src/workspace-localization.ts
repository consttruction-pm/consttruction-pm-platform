import type { WorkspaceLocale } from "./workspace-model.js";
import type { LanguagePackManifest } from "../../client-sync/src/language-pack-manifest.js";
import type { LanguagePackResource } from "../../client-sync/src/language-pack-resource-validation.js";
import { translateUiString, translateColumnLabel } from "./workspace-ui-translations.js";
import { catalogSize, translateCatalogString } from "./workspace-locale-catalogs.js";

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
  ["de", { locale: "de", displayName: "Deutsch", direction: "ltr", translations: {} }],
  ["zh", { locale: "zh", displayName: "中文", direction: "ltr", translations: {} }],
  ["ar", { locale: "ar", displayName: "العربية", direction: "rtl", translations: {} }],
  ["fr", { locale: "fr", displayName: "Français", direction: "ltr", translations: {} }],
  ["ja", { locale: "ja", displayName: "日本語", direction: "ltr", translations: {} }],
  ["ko", { locale: "ko", displayName: "한국어", direction: "ltr", translations: {} }],
  ["ru", { locale: "ru", displayName: "Русский", direction: "ltr", translations: {} }],
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
  if (!/^[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$/.test(manifest.language_tag)) {
    throw new Error("INVALID_WORKSPACE_LOCALE");
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

/**
 * True only when selecting this locale actually changes UI text. English and
 * Persian are built in; German and Chinese use the shared dictionary; Arabic,
 * French, Japanese, Korean and Russian ship baseline interface catalogs. A
 * locale only becomes selectable once one of those sources exists, so the
 * selector never presents an untranslated locale as complete.
 */
export function hasWorkspaceUiTranslations(locale: WorkspaceLocale): boolean {
  const definition = localeDefinitions.get(locale);
  if (!definition) return false;
  if (Object.keys(definition.translations).length > 0) return true;
  const base = locale.split("-")[0].toLowerCase();
  if (base === "en" || base === "fa" || base === "de" || base === "zh") return true;
  return catalogSize(locale) > 0;
}

export function translateWorkspaceText(locale: WorkspaceLocale, key: string, fallback: string): string {
  return localeDefinitions.get(locale)?.translations[key] ?? fallback;
}

/**
 * Translate a UI sentence that already carries an English and Persian form.
 * A verified language pack wins, then the built-in Persian text, then the
 * shared German/Chinese dictionary and the baseline interface catalogs; an
 * untranslated sentence falls back to its English source so no raw key ever
 * reaches the screen.
 */
export function translateWorkspaceUiText(locale: WorkspaceLocale, english: string, persian: string): string {
  const packed = translateWorkspaceText(locale, `ui.${english}`, "");
  if (packed) return packed;
  const base = locale.split("-")[0].toLowerCase();
  if (base === "fa") return persian;
  if (base === "de" || base === "zh") return translateUiString(locale, english) ?? english;
  return translateCatalogString(locale, english) ?? english;
}

/** Translate a persisted English presentation label for the active locale. */
export function localizeWorkspaceLabel(locale: WorkspaceLocale, english: string): string {
  return translateWorkspaceText(locale, `column.label.${english}`, "") || translateColumnLabel(locale, english);
}
