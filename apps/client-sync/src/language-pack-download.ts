export type LanguagePackDownloadManifest = {
  packageId: string;
  languageTag: string;
  version: string;
  minAppVersion: string;
  maxAppVersion?: string | null;
  compressedSizeBytes: number;
  downloadUri: string;
  checksum: string;
  signature: string;
  resourcePaths?: {
    translation: string;
    glossary: string;
    help: string;
    reports: string;
  };
};

export type LanguagePackDownloadProgress = {
  packageId: string;
  languageTag: string;
  version: string;
  phase: "downloading" | "verifying" | "cached";
  bytesReceived: number;
  totalBytes: number;
};

export interface LanguagePackDownloadTransport {
  download(
    uri: string,
    onChunk?: (chunk: Uint8Array) => void,
  ): Promise<Uint8Array>;
}

export interface LanguagePackVerifier {
  verify(
    artifact: Uint8Array,
    manifest: LanguagePackDownloadManifest,
  ): Promise<boolean>;
}

export class LanguagePackDownloadService {
  constructor(
    private readonly transport: LanguagePackDownloadTransport,
    private readonly verifier: LanguagePackVerifier,
  ) {}

  async downloadVerified(
    manifest: LanguagePackDownloadManifest,
    onProgress?: (progress: LanguagePackDownloadProgress) => void,
  ): Promise<Uint8Array> {
    let received = 0;

    onProgress?.({
      packageId: manifest.packageId,
      languageTag: manifest.languageTag,
      version: manifest.version,
      phase: "downloading",
      bytesReceived: 0,
      totalBytes: manifest.compressedSizeBytes,
    });

    const artifact = await this.transport.download(manifest.downloadUri, (chunk) => {
      received += chunk.byteLength;
      onProgress?.({
        packageId: manifest.packageId,
        languageTag: manifest.languageTag,
        version: manifest.version,
        phase: "downloading",
        bytesReceived: received,
        totalBytes: manifest.compressedSizeBytes,
      });
    });

    onProgress?.({
      packageId: manifest.packageId,
      languageTag: manifest.languageTag,
      version: manifest.version,
      phase: "verifying",
      bytesReceived: artifact.byteLength,
      totalBytes: manifest.compressedSizeBytes,
    });

    const verified = await this.verifier.verify(artifact, manifest);
    if (!verified) {
      throw new Error("LANGUAGE_PACK_VERIFICATION_FAILED");
    }

    onProgress?.({
      packageId: manifest.packageId,
      languageTag: manifest.languageTag,
      version: manifest.version,
      phase: "cached",
      bytesReceived: artifact.byteLength,
      totalBytes: manifest.compressedSizeBytes,
    });

    return new Uint8Array(artifact);
  }
}
