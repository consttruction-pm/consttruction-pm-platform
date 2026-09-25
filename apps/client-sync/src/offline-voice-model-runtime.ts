import type {
  DeviceCapabilityProfile,
  PreferredLanguageModels,
} from "./offline-ai-model-selector.ts";
import { OfflineAIModelRuntime } from "./offline-ai-model-runtime.ts";
import type { OfflineModelArtifactStore } from "./offline-ai-model-artifact-store.ts";

export interface LocalVoiceModelLoader {
  loadInput(packageId: string, artifact: Uint8Array): Promise<void>;
  loadOutput(packageId: string, artifact: Uint8Array): Promise<void>;
}

export type PreparedVoiceModels = {
  inputModelPackageId: string | null;
  outputModelPackageId: string | null;
};

export class OfflineVoiceModelRuntime {
  constructor(
    private readonly modelRuntime: OfflineAIModelRuntime,
    private readonly artifacts: OfflineModelArtifactStore,
    private readonly loader: LocalVoiceModelLoader,
  ) {}

  async prepare(
    appVersion: string,
    device: DeviceCapabilityProfile,
  ): Promise<PreparedVoiceModels> {
    const selected: PreferredLanguageModels =
      await this.modelRuntime.select(appVersion, device);

    let inputModelPackageId: string | null = null;
    let outputModelPackageId: string | null = null;

    if (selected.voiceInput) {
      const artifact = await this.artifacts.get(
        selected.voiceInput.packageId,
        selected.voiceInput.version,
      );
      if (artifact?.verified) {
        await this.loader.loadInput(
          selected.voiceInput.packageId,
          artifact.artifact,
        );
        inputModelPackageId = selected.voiceInput.packageId;
      }
    }

    if (selected.voiceOutput) {
      const artifact = await this.artifacts.get(
        selected.voiceOutput.packageId,
        selected.voiceOutput.version,
      );
      if (artifact?.verified) {
        await this.loader.loadOutput(
          selected.voiceOutput.packageId,
          artifact.artifact,
        );
        outputModelPackageId = selected.voiceOutput.packageId;
      }
    }

    return {
      inputModelPackageId,
      outputModelPackageId,
    };
  }
}
