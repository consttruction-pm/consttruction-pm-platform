import {
  ClientLanguageManager,
  type LanguagePreference,
  type LanguageRegistryEntry,
  type ResolvedLanguage,
} from "./language.ts";
import type { LanguagePackStore } from "./language-pack-store.ts";

export class ClientLanguageRuntime {
  private manager: ClientLanguageManager | null = null;

  constructor(private readonly packStore: LanguagePackStore | null = null) {}

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

  canUseLanguageOffline(languageTag: string): boolean {
    if (!this.manager) {
      return false;
    }
    return this.manager.canRunOffline(languageTag);
  }

  async cacheVerifiedPack(pack: Parameters<LanguagePackStore["put"]>[0]): Promise<void> {
    if (!this.packStore) {
      throw new Error("LANGUAGE_PACK_STORE_NOT_CONFIGURED");
    }
    await this.packStore.put(pack);
  }

  async installedPacks() {
    if (!this.packStore) {
      throw new Error("LANGUAGE_PACK_STORE_NOT_CONFIGURED");
    }
    return this.packStore.list();
  }
}
