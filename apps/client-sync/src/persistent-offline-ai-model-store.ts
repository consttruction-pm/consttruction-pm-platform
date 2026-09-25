import type { OfflineModelPack } from "./offline-ai-model-selector.ts";

export interface PersistentOfflineModelBackend {
  load(): Promise<readonly OfflineModelPack[]>;
  save(models: readonly OfflineModelPack[]): Promise<void>;
}

export class PersistentOfflineModelStore {
  constructor(private readonly backend: PersistentOfflineModelBackend) {}

  async list(): Promise<readonly OfflineModelPack[]> {
    return (await this.backend.load()).map((model) => ({ ...model }));
  }

  async put(model: OfflineModelPack): Promise<void> {
    if (!model.verified) throw new Error("UNVERIFIED_OFFLINE_MODEL");
    const current = await this.backend.load();
    const next = current.filter(
      (item) => item.packageId !== model.packageId || item.version !== model.version,
    );
    next.push({ ...model });
    await this.backend.save(next);
  }

  async remove(packageId: string, version: string): Promise<void> {
    const current = await this.backend.load();
    await this.backend.save(
      current.filter(
        (item) => item.packageId !== packageId || item.version !== version,
      ),
    );
  }
}
