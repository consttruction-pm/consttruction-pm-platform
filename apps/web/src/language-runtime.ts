import {
  ClientLanguageRuntime,
} from "../../client-sync/src/language-runtime.js";
import { LanguagePackActivationService } from "../../client-sync/src/language-pack-activation.js";
import type { LanguagePackManifest } from "../../client-sync/src/language-pack-manifest.js";
import { LanguageResourceRuntime } from "../../client-sync/src/language-resource-runtime.js";
import {
  WebLanguageResourceReader,
  type WebLanguagePackExtractor,
} from "./language-resource-reader.js";
import {
  FetchLanguagePackTransport,
  WebLanguagePackVerifier,
  type WebSignatureVerifier,
} from "./language-pack-download.js";
import {
  IndexedDbLanguagePackStore,
} from "./language-pack-store.js";
import {
  WebLanguagePreferenceStore,
} from "./language-preference-store.js";
import type {
  LanguagePackDownloadManifest,
  LanguagePackDownloadProgress,
} from "../../client-sync/src/language-pack-download.js";

export class WebLanguageRuntime {
  readonly language: ClientLanguageRuntime;
  private readonly packs: IndexedDbLanguagePackStore;
  private activationService: LanguagePackActivationService | null = null;

  constructor(databaseName?: string) {
    this.packs = new IndexedDbLanguagePackStore(databaseName);
    this.language = new ClientLanguageRuntime(
      this.packs,
      new WebLanguagePreferenceStore(),
    );
  }

  configureResourceExtractor(extractor: WebLanguagePackExtractor): void {
    const resources = new LanguageResourceRuntime(
      new WebLanguageResourceReader(extractor),
    );
    this.activationService = new LanguagePackActivationService(
      this.packs,
      resources,
    );
  }

  async downloadLanguagePack(
    manifest: LanguagePackDownloadManifest,
    signatureVerifier: WebSignatureVerifier,
    onProgress?: (progress: LanguagePackDownloadProgress) => void,
  ): Promise<void> {
    const verifier = new WebLanguagePackVerifier(signatureVerifier);
    await this.language.downloadAndCacheLanguagePack(
      manifest,
      new FetchLanguagePackTransport(),
      verifier,
      onProgress,
    );
  }

  async activateLanguagePack(
    manifest: LanguagePackManifest,
  ) {
    if (!this.activationService) {
      throw new Error("LANGUAGE_RESOURCE_EXTRACTOR_NOT_CONFIGURED");
    }
    return this.activationService.activate(manifest);
  }
}
