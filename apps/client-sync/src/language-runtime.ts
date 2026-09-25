import {
  ClientLanguageManager,
  type LanguagePreference,
  type LanguageRegistryEntry,
  type ResolvedLanguage,
} from "./language.ts";
import type { LanguagePackStore, CachedLanguagePack } from "./language-pack-store.ts";
import type { LanguageCapabilitySet } from "./language.ts";

function itemCapable(item: CachedLanguagePack): LanguageCapabilitySet {
  // Storage confirms integrity; capability metadata is supplied by the registry.
  // Until the registry-to-store projection is wired, only deterministic UI/help
  // can be considered locally available here.
  return {
    ui: true,
    help: true,
    aiText: false,
    voiceInput: false,
    voiceOutput: false,
    offlineAi: false,
  };
}

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
    const installed = await this.packStore.list();
    this.manager?.setInstalledPacks(
      installed.map((item) => ({
        languageTag: item.languageTag,
        version: item.version,
        active: true,
        verified: item.verified,
        capabilities: itemCapable(item),
      })),
    );
  }

  async installedPacks() {
    if (!this.packStore) {
      throw new Error("LANGUAGE_PACK_STORE_NOT_CONFIGURED");
    }
    return this.packStore.list();
  }
}
