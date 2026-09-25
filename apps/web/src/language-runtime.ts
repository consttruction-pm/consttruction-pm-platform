import {
  ClientLanguageRuntime,
} from "../../client-sync/src/language-runtime.js";
import {
  FetchLanguagePackTransport,
  WebLanguagePackVerifier,
  type WebSignatureVerifier,
} from "./language-pack-download.js";
import {
  IndexedDbLanguagePackStore,
} from "./language-pack-store.js";
import type {
  LanguagePackDownloadManifest,
  LanguagePackDownloadProgress,
} from "../../client-sync/src/language-pack-download.js";

export class WebLanguageRuntime {
  readonly language: ClientLanguageRuntime;

  constructor(databaseName?: string) {
    this.language = new ClientLanguageRuntime(
      new IndexedDbLanguagePackStore(databaseName),
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
}
