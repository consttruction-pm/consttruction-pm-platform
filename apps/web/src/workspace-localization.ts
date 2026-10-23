import type { WorkspaceLocale } from "./workspace-model.js";

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
  if (!locale || !/^[a-z]{2,3}(?:-[A-Z]{2})?$/.test(locale)) {
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
