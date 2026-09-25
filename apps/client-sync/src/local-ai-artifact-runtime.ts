import type { DeviceCapabilityProfile } from "./offline-ai-model-selector.ts";
import type { OfflineAIModelRuntime } from "./offline-ai-model-runtime.ts";
import type { OfflineModelArtifactStore } from "./offline-ai-model-artifact-store.ts";

export interface LocalTextModelLoader {
  load(packageId: string, artifact: Uint8Array): Promise<void>;
}

export class LocalAIArtifactRuntime {
  constructor(
    private readonly artifactStore: OfflineModelArtifactStore,
    private readonly modelRuntime: OfflineAIModelRuntime,
    private readonly localLoader: LocalTextModelLoader,
  ) {}

  async prepareTextModel(
    appVersion: string,
    device: DeviceCapabilityProfile,
  ): Promise<string | null> {
    const selected = await this.modelRuntime.select(appVersion, device);
    const model = selected.aiText;
    if (!model) return null;

    const artifact = await this.artifactStore.get(
      model.packageId,
      model.version,
    );
    if (!artifact || !artifact.verified) return null;

    await this.localLoader.load(model.packageId, artifact.artifact);
    return model.packageId;
  }
}
