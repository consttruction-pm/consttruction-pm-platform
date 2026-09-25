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
import { WebZipLanguagePackExtractor } from "./web-zip-language-pack-extractor.js";
import {
  FetchLanguagePackTransport,
  WebLanguagePackVerifier,
  type WebSignatureVerifier,
} from "./language-pack-download.js";
import {
  IndexedDbLanguagePackStore,
} from "./language-pack-store.js";
import {
  IndexedDbLanguagePackResourceManifestStore,
} from "./language-pack-resource-manifest-store.js";
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
  private readonly resourceManifests: IndexedDbLanguagePackResourceManifestStore;
  private activationService: LanguagePackActivationService | null = null;

  constructor(databaseName?: string) {
    this.packs = new IndexedDbLanguagePackStore(databaseName);
    this.resourceManifests = new IndexedDbLanguagePackResourceManifestStore();
    this.language = new ClientLanguageRuntime(
      this.packs,
      new WebLanguagePreferenceStore(),
      this.resourceManifests,
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

  configureZipResourceExtractor(): void {
    this.configureResourceExtractor(new WebZipLanguagePackExtractor());
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

  async activateCachedLanguagePack(
    packageId: string,
    version: string,
  ) {
    if (!this.activationService) {
      throw new Error("LANGUAGE_RESOURCE_EXTRACTOR_NOT_CONFIGURED");
    }
    const resources = await this.resourceManifests.get(packageId, version);
    if (!resources) {
      throw new Error("LANGUAGE_PACK_RESOURCE_MANIFEST_NOT_FOUND");
    }
    return this.activationService.activateFromStoredResources(
      packageId,
      version,
      resources.resources,
    );
  }
}
