import type {
  LanguagePackDownloadTransport,
  LanguagePackVerifier,
} from "./language-pack-download.ts";
import type { OfflineModelPack } from "./offline-ai-model-selector.ts";
import type { OfflineModelArtifactStore } from "./offline-ai-model-artifact-store.ts";
import type { OfflineModelStore } from "./offline-ai-model-store.ts";

export type OfflineModelDownloadManifest = {
  model: OfflineModelPack;
  downloadUri: string;
};

export class OfflineModelDownloadService {
  constructor(
    private readonly transport: LanguagePackDownloadTransport,
    private readonly verifier: LanguagePackVerifier,
    private readonly store: OfflineModelStore,
    private readonly artifactStore: OfflineModelArtifactStore,
  ) {}

  async downloadAndInstall(
    manifest: OfflineModelDownloadManifest,
    onProgress?: (progress: {
      packageId: string;
      languageTag: string;
      version: string;
      phase: "downloading" | "verifying" | "installed";
      bytesReceived: number;
      totalBytes: number;
    }) => void,
  ): Promise<void> {
    const totalBytes = manifest.model.sizeBytes;
    let received = 0;

    onProgress?.({
      packageId: manifest.model.packageId,
      languageTag: manifest.model.languageTag,
      version: manifest.model.version,
      phase: "downloading",
      bytesReceived: 0,
      totalBytes,
    });

    const artifact = await this.transport.download(
      manifest.downloadUri,
      (chunk) => {
        received += chunk.byteLength;
        onProgress?.({
          packageId: manifest.model.packageId,
          languageTag: manifest.model.languageTag,
          version: manifest.model.version,
          phase: "downloading",
          bytesReceived: received,
          totalBytes,
        });
      },
    );

    onProgress?.({
      packageId: manifest.model.packageId,
      languageTag: manifest.model.languageTag,
      version: manifest.model.version,
      phase: "verifying",
      bytesReceived: artifact.byteLength,
      totalBytes,
    });

    const verified = await this.verifier.verify(artifact, {
      packageId: manifest.model.packageId,
      languageTag: manifest.model.languageTag,
      version: manifest.model.version,
      minAppVersion: manifest.model.minAppVersion,
      maxAppVersion: manifest.model.maxAppVersion,
      compressedSizeBytes: artifact.byteLength,
      downloadUri: manifest.downloadUri,
      checksum: manifest.model.checksum,
      signature: manifest.model.signature,
    });
    if (!verified) {
      throw new Error("OFFLINE_MODEL_VERIFICATION_FAILED");
    }

    await this.store.put({
      ...manifest.model,
      verified: true,
    });
    await this.artifactStore.put({
      packageId: manifest.model.packageId,
      languageTag: manifest.model.languageTag,
      modelType: manifest.model.modelType,
      version: manifest.model.version,
      artifact: new Uint8Array(artifact),
      verified: true,
    });

    onProgress?.({
      packageId: manifest.model.packageId,
      languageTag: manifest.model.languageTag,
      version: manifest.model.version,
      phase: "installed",
      bytesReceived: artifact.byteLength,
      totalBytes,
    });
  }
}
