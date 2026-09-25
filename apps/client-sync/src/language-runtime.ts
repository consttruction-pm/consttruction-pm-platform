import {
  ClientLanguageManager,
  type LanguagePreference,
  type LanguageRegistryEntry,
  type ResolvedLanguage,
} from "./language.ts";

export class ClientLanguageRuntime {
  private manager: ClientLanguageManager | null = null;

  configure(
    registry: readonly LanguageRegistryEntry[],
    defaultLanguage: string,
    preference: LanguagePreference,
  ): ResolvedLanguage {
    this.manager = new ClientLanguageManager(registry, defaultLanguage, preference);
    return this.manager.resolve();
  }

  isConfigured(): boolean {
    return this.manager !== null;
  }

  current(): ResolvedLanguage {
    if (!this.manager) {
      throw new Error("LANGUAGE_RUNTIME_NOT_CONFIGURED");
    }
    return this.manager.resolve();
  }

  setPreferredLanguage(languageTag: string): ResolvedLanguage {
    if (!this.manager) {
      throw new Error("LANGUAGE_RUNTIME_NOT_CONFIGURED");
    }
    return this.manager.setPreferredLanguage(languageTag);
  }

  canRunOffline(languageTag: string): boolean {
    if (!this.manager) {
      return false;
    }
    return this.manager.canRunOffline(languageTag);
  }
}
