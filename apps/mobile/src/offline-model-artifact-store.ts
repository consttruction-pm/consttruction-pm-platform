import type {
  InstalledOfflineModelArtifact,
  OfflineModelArtifactStore,
} from "../../client-sync/src/offline-ai-model-artifact-store.js";

export interface MobileBinaryArtifactStorage {
  get(key: string): Promise<Uint8Array | null>;
  set(key: string, artifact: Uint8Array): Promise<void>;
  remove(key: string): Promise<void>;
}

export interface MobileArtifactMetadataStorage {
  get(key: string): Promise<string | null>;
  set(key: string, value: string): Promise<void>;
  remove(key: string): Promise<void>;
}

export class MobileBinaryOfflineModelArtifactStore
  implements OfflineModelArtifactStore
{
  constructor(
    private readonly binaries: MobileBinaryArtifactStorage,
    private readonly metadata: MobileArtifactMetadataStorage,
  ) {}

  async get(
    packageId: string,
    version: string,
  ): Promise<InstalledOfflineModelArtifact | null> {
    const key = artifactKey(packageId, version);
    const raw = await this.metadata.get(key);
    if (!raw) return null;

    const value = JSON.parse(raw) as Omit<InstalledOfflineModelArtifact, "artifact">;
    const artifact = await this.binaries.get(key);
    if (!artifact) return null;

    return {
      ...value,
      artifact: new Uint8Array(artifact),
    };
  }

  async put(model: InstalledOfflineModelArtifact): Promise<void> {
    if (!model.verified) throw new Error("UNVERIFIED_OFFLINE_MODEL_ARTIFACT");
    if (!model.packageId || !model.version || model.artifact.byteLength === 0) {
      throw new Error("INVALID_OFFLINE_MODEL_ARTIFACT");
    }

    const key = artifactKey(model.packageId, model.version);
    await this.binaries.set(key, model.artifact);
    await this.metadata.set(
      key,
      JSON.stringify({
        packageId: model.packageId,
        languageTag: model.languageTag,
        modelType: model.modelType,
        version: model.version,
        verified: true,
      }),
    );
  }

  async remove(packageId: string, version: string): Promise<void> {
    const key = artifactKey(packageId, version);
    await Promise.all([
      this.binaries.remove(key),
      this.metadata.remove(key),
    ]);
  }
}

function artifactKey(packageId: string, version: string): string {
  return "construction-pm.offline-model." + packageId + "@" + version;
}
