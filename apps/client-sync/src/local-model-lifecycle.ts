import type { DeviceCapabilityProfile, OfflineModelPack } from "./offline-ai-model-selector.js";
import type { OfflineAIModelRuntime } from "./offline-ai-model-runtime.js";
import type { OfflineModelArtifactStore } from "./offline-ai-model-artifact-store.js";
import type { LocalTextInferenceEngine } from "./local-inference-engine.js";

export type LocalModelLifecyclePolicy = {
  maxLoadedModelBytes: number;
  maxConcurrentModels: number;
};

type LoadedModel = {
  model: OfflineModelPack;
  loadedAt: number;
  lastUsedAt: number;
};

export type LocalModelLifecycleState = {
  activePackageId: string | null;
  activeVersion: string | null;
  loaded: readonly {
    packageId: string;
    version: string;
    sizeBytes: number;
  }[];
};

export class LocalTextModelLifecycleManager {
  private readonly loaded = new Map<string, LoadedModel>();
  private activePackageId: string | null = null;

  constructor(
    private readonly modelRuntime: OfflineAIModelRuntime,
    private readonly artifactStore: OfflineModelArtifactStore,
    private readonly engine: LocalTextInferenceEngine,
    private readonly policy: LocalModelLifecyclePolicy,
    private readonly clock: () => number = () => Date.now(),
  ) {
    if (policy.maxLoadedModelBytes <= 0 || policy.maxConcurrentModels <= 0) {
      throw new Error("INVALID_LOCAL_MODEL_LIFECYCLE_POLICY");
    }
  }

  async prepare(
    appVersion: string,
    device: DeviceCapabilityProfile,
  ): Promise<LocalModelLifecycleState> {
    const selected = await this.modelRuntime.select(appVersion, device);
    const model = selected.aiText;
    if (!model) {
      return this.snapshot();
    }

    const key = modelKey(model.packageId, model.version);
    if (this.loaded.has(key)) {
      this.markUsed(key);
      this.activePackageId = model.packageId;
      return this.snapshot();
    }

    if (model.sizeBytes > this.policy.maxLoadedModelBytes) {
      throw new Error("LOCAL_AI_MODEL_EXCEEDS_MEMORY_BUDGET");
    }

    await this.ensureCapacity(model.sizeBytes, key);

    const artifact = await this.artifactStore.get(
      model.packageId,
      model.version,
    );
    if (!artifact?.verified) {
      throw new Error("LOCAL_AI_MODEL_ARTIFACT_UNAVAILABLE");
    }

    // Load the replacement first. The previous active model remains tracked
    // until the new model has loaded successfully.
    await this.engine.load(
      model.packageId,
      model.version,
      artifact.artifact,
    );

    const now = this.clock();
    this.loaded.set(key, {
      model,
      loadedAt: now,
      lastUsedAt: now,
    });
    this.activePackageId = model.packageId;

    await this.unloadOtherVersionsOfPackage(model.packageId, model.version);
    return this.snapshot();
  }

  async unload(packageId: string, version?: string): Promise<void> {
    const entries = [...this.loaded.values()].filter(
      (entry) =>
        entry.model.packageId === packageId &&
        (version === undefined || entry.model.version === version),
    );
    for (const entry of entries) {
      const key = modelKey(entry.model.packageId, entry.model.version);
      await this.engine.unload(
        entry.model.packageId,
        entry.model.version,
      );
      this.loaded.delete(key);
    }

    if (
      this.activePackageId === packageId &&
      ![...this.loaded.values()].some(
        (entry) => entry.model.packageId === packageId,
      )
    ) {
      this.activePackageId = null;
    }
  }

  markUsed(packageId: string, version: string): void {
    const key = modelKey(packageId, version);
    const entry = this.loaded.get(key);
    if (!entry) return;
    this.loaded.set(key, {
      ...entry,
      lastUsedAt: this.clock(),
    });
    this.activePackageId = packageId;
  }

  snapshot(): LocalModelLifecycleState {
    const loaded = [...this.loaded.values()]
      .sort((left, right) => left.lastUsedAt - right.lastUsedAt)
      .map((entry) => ({
        packageId: entry.model.packageId,
        version: entry.model.version,
        sizeBytes: entry.model.sizeBytes,
      }));

    const active = this.activePackageId
      ? [...this.loaded.values()].find(
          (entry) => entry.model.packageId === this.activePackageId,
        )
      : undefined;

    return {
      activePackageId: this.activePackageId,
      activeVersion: active?.model.version ?? null,
      loaded,
    };
  }

  private async ensureCapacity(
    incomingBytes: number,
    incomingKey: string,
  ): Promise<void> {
    while (
      this.loaded.size >= this.policy.maxConcurrentModels ||
      totalLoadedBytes(this.loaded) + incomingBytes >
        this.policy.maxLoadedModelBytes
    ) {
      const activeEntry = this.activePackageId
        ? [...this.loaded.values()].find(
            (entry) => entry.model.packageId === this.activePackageId,
          )
        : undefined;
      const activeKey = activeEntry
        ? modelKey(activeEntry.model.packageId, activeEntry.model.version)
        : null;

      const evictable = [...this.loaded.entries()]
        .filter(([key]) => key !== incomingKey && key !== activeKey)
        .sort((left, right) => left[1].lastUsedAt - right[1].lastUsedAt)[0];

      if (!evictable) {
        throw new Error("LOCAL_AI_MODEL_MEMORY_BUDGET_UNAVAILABLE");
      }

      const [key, entry] = evictable;
      await this.engine.unload(entry.model.packageId);
      this.loaded.delete(key);
      if (this.activePackageId === entry.model.packageId) {
        this.activePackageId = null;
      }
    }
  }

  private async unloadOtherVersionsOfPackage(
    packageId: string,
    retainedVersion: string,
  ): Promise<void> {
    const older = [...this.loaded.values()].filter(
      (entry) =>
        entry.model.packageId === packageId &&
        entry.model.version !== retainedVersion,
    );
    for (const entry of older) {
      await this.engine.unload(entry.model.packageId);
      this.loaded.delete(modelKey(entry.model.packageId, entry.model.version));
    }
  }

}

function totalLoadedBytes(
  loaded: ReadonlyMap<string, LoadedModel>,
): number {
  return [...loaded.values()].reduce(
    (total, entry) => total + entry.model.sizeBytes,
    0,
  );
}

function modelKey(packageId: string, version: string): string {
  return packageId + "@" + version;
}
