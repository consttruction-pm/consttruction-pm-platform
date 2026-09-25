import {
  LanguageCatalogService,
  type LanguageCatalogItem,
} from "./language-catalog.ts";
import { ClientLanguageRuntime } from "./language-runtime.ts";
import type {
  LanguagePackDownloadManifest,
  LanguagePackDownloadProgress,
  LanguagePackDownloadTransport,
  LanguagePackVerifier,
} from "./language-pack-download.ts";
import type { LanguageRegistryEntry } from "./language.ts";
import type { LanguagePackStore } from "./language-pack-store.ts";

export type LanguageManagerState = {
  selectedLanguage: string;
  items: readonly LanguageCatalogItem[];
};

export class LanguageManagerController {
  private readonly catalog: LanguageCatalogService;

  constructor(
    private readonly runtime: ClientLanguageRuntime,
    registry: readonly LanguageRegistryEntry[],
    private readonly store: LanguagePackStore,
  ) {
    this.catalog = new LanguageCatalogService(registry, store);
  }

  async refresh(): Promise<LanguageManagerState> {
    const current = this.runtime.current();
    return {
      selectedLanguage: current.languageTag,
      items: await this.catalog.list(),
    };
  }

  select(languageTag: string) {
    return this.runtime.setPreferredLanguage(languageTag);
  }

  async persistSelection(languageTag: string) {
    return this.runtime.persistPreferredLanguage(languageTag);
  }

  async removeInstalledPack(
    packageId: string,
    version: string,
  ): Promise<LanguageManagerState> {
    const current = this.runtime.current();
    if (current.packVersion === version) {
      throw new Error("CANNOT_REMOVE_ACTIVE_LANGUAGE_PACK");
    }
    await this.store.remove(packageId, version);
    return this.refresh();
  }

  async download(
    manifest: LanguagePackDownloadManifest,
    transport: LanguagePackDownloadTransport,
    verifier: LanguagePackVerifier,
    onProgress?: (progress: LanguagePackDownloadProgress) => void,
  ): Promise<LanguageManagerState> {
    await this.runtime.downloadAndCacheLanguagePack(
      manifest,
      transport,
      verifier,
      onProgress,
    );
    return this.refresh();
  }
}
