import type { InstalledOfflineModelArtifact } from "./offline-ai-model-artifact-store.ts";

export interface PersistentOfflineModelArtifactBackend {
  get(packageId: string, version: string): Promise<InstalledOfflineModelArtifact | null>;
  put(model: InstalledOfflineModelArtifact): Promise<void>;
  remove(packageId: string, version: string): Promise<void>;
}

export class PersistentOfflineModelArtifactStore {
  constructor(private readonly backend: PersistentOfflineModelArtifactBackend) {}

  async get(packageId: string, version: string): Promise<InstalledOfflineModelArtifact | null> {
    const result = await this.backend.get(packageId, version);
    return result
      ? { ...result, artifact: new Uint8Array(result.artifact) }
      : null;
  }

  async put(model: InstalledOfflineModelArtifact): Promise<void> {
    if (!model.verified) {
      throw new Error("UNVERIFIED_OFFLINE_MODEL_ARTIFACT");
    }
    if (model.artifact.byteLength === 0) {
      throw new Error("EMPTY_OFFLINE_MODEL_ARTIFACT");
    }
    await this.backend.put({
      ...model,
      artifact: new Uint8Array(model.artifact),
    });
  }

  async remove(packageId: string, version: string): Promise<void> {
    await this.backend.remove(packageId, version);
  }
}
