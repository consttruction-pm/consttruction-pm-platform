import type { LanguageCatalogItem } from "./language-catalog.ts";
import {
  LanguagePackDownloadService,
  type LanguagePackDownloadManifest,
  type LanguagePackDownloadProgress,
  type LanguagePackDownloadTransport,
  type LanguagePackVerifier,
} from "./language-pack-download.ts";
import type { LanguagePackStore } from "./language-pack-store.ts";
import type { LanguageRegistryEntry } from "./language.ts";

export type LanguageManagerViewState = {
  selectedLanguage: string;
  items: readonly LanguageCatalogItem[];
  downloading: string | null;
  progress: LanguagePackDownloadProgress | null;
  error: string | null;
};

export class LanguageManagerViewModel {
  private state: LanguageManagerViewState;

  constructor(
    private readonly registry: readonly LanguageRegistryEntry[],
    private readonly store: LanguagePackStore,
    selectedLanguage: string,
  ) {
    this.state = {
      selectedLanguage,
      items: [],
      downloading: null,
      progress: null,
      error: null,
    };
  }

  snapshot(): LanguageManagerViewState {
    return {
      ...this.state,
      items: this.state.items.map((item) => ({
        ...item,
        capabilities: { ...item.capabilities },
      })),
    };
  }

  async refresh(): Promise<LanguageManagerViewState> {
    const installed = await this.store.list();
    this.state = {
      ...this.state,
      items: this.registry.map((entry) => {
        const verified = installed
          .filter((pack) => pack.languageTag === entry.languageTag && pack.verified)
          .sort((a, b) => a.version.localeCompare(b.version, undefined, { numeric: true }))
          .at(-1);

        return {
          languageTag: entry.languageTag,
          direction: entry.direction,
          locale: entry.locale,
          installedVersion: verified?.version ?? null,
          verified: Boolean(verified),
          offlineReady: Boolean(verified && entry.capabilities.ui),
          capabilities: entry.capabilities,
        };
      }),
      error: null,
    };
    return this.snapshot();
  }

  select(languageTag: string): LanguageManagerViewState {
    if (!this.registry.some((entry) => entry.languageTag === languageTag)) {
      throw new Error("UNSUPPORTED_LANGUAGE");
    }
    this.state = {
      ...this.state,
      selectedLanguage: languageTag,
      error: null,
    };
    return this.snapshot();
  }

  async download(
    manifest: LanguagePackDownloadManifest,
    transport: LanguagePackDownloadTransport,
    verifier: LanguagePackVerifier,
  ): Promise<LanguageManagerViewState> {
    this.state = {
      ...this.state,
      downloading: manifest.languageTag,
      progress: null,
      error: null,
    };

    try {
      const artifact = await new LanguagePackDownloadService(
        transport,
        verifier,
      ).downloadVerified(manifest, (progress) => {
        this.state = {
          ...this.state,
          progress,
        };
      });

      await this.store.put({
        packageId: manifest.packageId,
        languageTag: manifest.languageTag,
        version: manifest.version,
        verified: true,
        artifact,
      });

      this.state = {
        ...this.state,
        downloading: null,
        progress: null,
        error: null,
      };
      return this.refresh();
    } catch (error) {
      this.state = {
        ...this.state,
        downloading: null,
        progress: null,
        error: error instanceof Error ? error.message : "LANGUAGE_PACK_DOWNLOAD_FAILED",
      };
      throw error;
    }
  }
}
