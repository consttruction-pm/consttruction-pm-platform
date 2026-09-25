export type InstalledOfflineModelArtifact = {
  packageId: string;
  languageTag: string;
  modelType: "ai_text" | "voice_input" | "voice_output";
  version: string;
  artifact: Uint8Array;
  verified: boolean;
};

export interface OfflineModelArtifactStore {
  get(packageId: string, version: string): Promise<InstalledOfflineModelArtifact | null>;
  put(model: InstalledOfflineModelArtifact): Promise<void>;
  remove(packageId: string, version: string): Promise<void>;
}

export class InMemoryOfflineModelArtifactStore implements OfflineModelArtifactStore {
  private readonly artifacts = new Map<string, InstalledOfflineModelArtifact>();

  async get(packageId: string, version: string): Promise<InstalledOfflineModelArtifact | null> {
    const value = this.artifacts.get(packageId + "@" + version);
    return value ? { ...value, artifact: new Uint8Array(value.artifact) } : null;
  }

  async put(model: InstalledOfflineModelArtifact): Promise<void> {
    if (!model.verified) throw new Error("UNVERIFIED_OFFLINE_MODEL_ARTIFACT");
    if (!model.packageId || !model.languageTag || !model.version || model.artifact.byteLength === 0) {
      throw new Error("INVALID_OFFLINE_MODEL_ARTIFACT");
    }
    this.artifacts.set(model.packageId + "@" + model.version, {
      ...model,
      artifact: new Uint8Array(model.artifact),
    });
  }

  async remove(packageId: string, version: string): Promise<void> {
    this.artifacts.delete(packageId + "@" + version);
  }
}
