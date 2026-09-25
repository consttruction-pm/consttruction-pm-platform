import type { LanguagePreferenceStore } from "../../client-sync/src/language-preference-store.js";

const KEY = "construction-pm.preferred-language";

export class WebLanguagePreferenceStore implements LanguagePreferenceStore {
  constructor(private readonly storage: Storage = localStorage) {}

  async load(): Promise<string | null> {
    return this.storage.getItem(KEY);
  }

  async save(languageTag: string): Promise<void> {
    if (!languageTag.trim()) {
      throw new Error("INVALID_LANGUAGE_PREFERENCE");
    }
    this.storage.setItem(KEY, languageTag.trim());
  }
}
