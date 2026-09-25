import type { OfflineModelPack } from "./offline-ai-model-selector.ts";

export interface OfflineModelStore {
  list(): Promise<readonly OfflineModelPack[]>;
  put(model: OfflineModelPack): Promise<void>;
  remove(packageId: string, version: string): Promise<void>;
}

export class InMemoryOfflineModelStore implements OfflineModelStore {
  private readonly models = new Map<string, OfflineModelPack>();

  async list(): Promise<readonly OfflineModelPack[]> {
    return [...this.models.values()].map((model) => ({ ...model }));
  }

  async put(model: OfflineModelPack): Promise<void> {
    if (!model.verified) {
      throw new Error("UNVERIFIED_OFFLINE_MODEL");
    }
    this.models.set(model.packageId + "@" + model.version, { ...model });
  }

  async remove(packageId: string, version: string): Promise<void> {
    this.models.delete(packageId + "@" + version);
  }
}
