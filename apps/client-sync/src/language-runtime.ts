import {
  ClientLanguageManager,
  type LanguagePreference,
  type LanguageRegistryEntry,
  type ResolvedLanguage,
} from "./language.ts";
import type { LanguagePackStore } from "./language-pack-store.ts";
import type { LanguagePreferenceStore } from "./language-preference-store.ts";
import type { LanguagePackResourceManifestStore } from "./language-pack-resource-manifest-store.ts";
import {
  LanguagePackDownloadService,
  type LanguagePackDownloadManifest,
  type LanguagePackDownloadProgress,
  type LanguagePackDownloadTransport,
  type LanguagePackVerifier,
} from "./language-pack-download.ts";

export class ClientLanguageRuntime {
  private manager: ClientLanguageManager | null = null;

  constructor(
    private readonly packStore: LanguagePackStore | null = null,
    private readonly preferenceStore: LanguagePreferenceStore | null = null,
    private readonly resourceManifestStore: LanguagePackResourceManifestStore | null = null,
  ) {}

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

  async persistPreferredLanguage(languageTag: string): Promise<ResolvedLanguage> {
    const resolved = this.setPreferredLanguage(languageTag);
    if (!this.preferenceStore) {
      throw new Error("LANGUAGE_PREFERENCE_STORE_NOT_CONFIGURED");
    }
    await this.preferenceStore.save(languageTag);
    return resolved;
  }

  async restorePreferredLanguage(): Promise<ResolvedLanguage> {
    if (!this.manager) {
      throw new Error("LANGUAGE_RUNTIME_NOT_CONFIGURED");
    }
    if (!this.preferenceStore) {
      throw new Error("LANGUAGE_PREFERENCE_STORE_NOT_CONFIGURED");
    }

    const saved = await this.preferenceStore.load();
    if (!saved) {
      return this.manager.resolve();
    }
    return this.manager.setPreferredLanguage(saved);
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
    this.manager?.syncInstalledPackState(
      installed.map((item) => ({
        languageTag: item.languageTag,
        version: item.version,
        verified: item.verified,
      })),
    );
  }

  async installedPacks() {
    if (!this.packStore) {
      throw new Error("LANGUAGE_PACK_STORE_NOT_CONFIGURED");
    }
    return this.packStore.list();
  }

  async downloadAndCacheLanguagePack(
    manifest: LanguagePackDownloadManifest,
    transport: LanguagePackDownloadTransport,
    verifier: LanguagePackVerifier,
    onProgress?: (progress: LanguagePackDownloadProgress) => void,
  ): Promise<void> {
    if (!this.packStore) {
      throw new Error("LANGUAGE_PACK_STORE_NOT_CONFIGURED");
    }

    const artifact = await new LanguagePackDownloadService(
      transport,
      verifier,
    ).downloadVerified(manifest, onProgress);

    await this.packStore.put({
      packageId: manifest.packageId,
      languageTag: manifest.languageTag,
      version: manifest.version,
      verified: true,
      artifact,
    });

    if (manifest.resourcePaths && this.resourceManifestStore) {
      await this.resourceManifestStore.put({
        packageId: manifest.packageId,
        languageTag: manifest.languageTag,
        version: manifest.version,
        resources: { ...manifest.resourcePaths },
      });
    }

    const installed = await this.packStore.list();
    this.manager?.syncInstalledPackState(
      installed.map((item) => ({
        languageTag: item.languageTag,
        version: item.version,
        verified: item.verified,
      })),
    );
  }
}

  async cachedResourceManifest(
    packageId: string,
    version: string,
  ) {
    if (!this.resourceManifestStore) {
      throw new Error("LANGUAGE_RESOURCE_MANIFEST_STORE_NOT_CONFIGURED");
    }
    return this.resourceManifestStore.get(packageId, version);
  }
