import type { LocalAIProvider } from "./language-bound-ai-service.js";
import type { OfflineAIModelRuntime } from "./offline-ai-model-runtime.js";
import type {
  DeviceCapabilityProfile,
  PreferredLanguageModels,
} from "./offline-ai-model-selector.js";
import type { OfflineModelArtifactStore } from "./offline-ai-model-artifact-store.js";
import type { AILanguageContext } from "./ai-language-contract.js";
import type {
  LocalTextInferenceEngine,
  LocalVoiceEngine,
  LocalVoiceInputRequest,
  LocalVoiceOutputRequest,
} from "./local-inference-engine.js";

export class EngineBackedLocalAIProvider implements LocalAIProvider {
  constructor(private readonly engine: LocalTextInferenceEngine) {}

  async complete(
    request: AILanguageContext,
    modelPackageId: string,
    modelVersion: string,
  ): Promise<string> {
    if (!request.offline_ai_capable) {
      throw new Error("AI_OFFLINE_CAPABILITY_UNAVAILABLE");
    }
    if (!this.engine.isLoaded(modelPackageId, modelVersion)) {
      throw new Error("LOCAL_AI_MODEL_NOT_LOADED");
    }
    const result = await this.engine.complete({
      context: request,
      modelPackageId,
      modelVersion,
    });
    if (result.modelPackageId !== modelPackageId) {
      throw new Error("LOCAL_AI_MODEL_ID_MISMATCH");
    }
    return result.text;
  }
}

export class LocalAIEngineRuntime {
  constructor(
    private readonly modelRuntime: OfflineAIModelRuntime,
    private readonly artifactStore: OfflineModelArtifactStore,
    private readonly engine: LocalTextInferenceEngine,
  ) {}

  async prepare(
    appVersion: string,
    device: DeviceCapabilityProfile,
  ): Promise<PreferredLanguageModels> {
    const selected = await this.modelRuntime.select(appVersion, device);
    const model = selected.aiText;
    if (!model) return selected;

    const artifact = await this.artifactStore.get(
      model.packageId,
      model.version,
    );
    if (!artifact?.verified) return selected;

    await this.engine.load(model.packageId, model.version, artifact.artifact);
    return selected;
  }

  async unload(modelPackageId: string): Promise<void> {
    await this.engine.unload(modelPackageId);
  }
}

export class EngineBackedLocalVoiceRuntime {
  constructor(
    private readonly modelRuntime: OfflineAIModelRuntime,
    private readonly artifacts: OfflineModelArtifactStore,
    private readonly engine: LocalVoiceEngine,
  ) {}

  async prepare(
    appVersion: string,
    device: DeviceCapabilityProfile,
  ): Promise<PreferredLanguageModels> {
    const selected = await this.modelRuntime.select(appVersion, device);

    if (selected.voiceInput) {
      const artifact = await this.artifacts.get(
        selected.voiceInput.packageId,
        selected.voiceInput.version,
      );
      if (artifact?.verified) {
        await this.engine.loadInput(
          selected.voiceInput.packageId,
          selected.voiceInput.version,
          artifact.artifact,
        );
      }
    }

    if (selected.voiceOutput) {
      const artifact = await this.artifacts.get(
        selected.voiceOutput.packageId,
        selected.voiceOutput.version,
      );
      if (artifact?.verified) {
        await this.engine.loadOutput(
          selected.voiceOutput.packageId,
          selected.voiceOutput.version,
          artifact.artifact,
        );
      }
    }

    return selected;
  }

  async transcribe(
    request: Omit<LocalVoiceInputRequest, "modelPackageId">,
    selected: PreferredLanguageModels,
  ): Promise<LocalVoiceInputRequest["languageTag"] extends string ? string : never> {
    const model = selected.voiceInput;
    if (!model) throw new Error("LOCAL_VOICE_INPUT_MODEL_UNAVAILABLE");
    if (!this.engine.isInputLoaded(model.packageId, model.version)) {
      throw new Error("LOCAL_VOICE_INPUT_MODEL_NOT_LOADED");
    }
    const result = await this.engine.transcribe({
      ...request,
      modelPackageId: model.packageId,
    });
    if (result.modelPackageId !== model.packageId) {
      throw new Error("LOCAL_VOICE_INPUT_MODEL_ID_MISMATCH");
    }
    return result.text;
  }

  async synthesize(
    request: Omit<LocalVoiceOutputRequest, "modelPackageId">,
    selected: PreferredLanguageModels,
  ): Promise<Uint8Array> {
    const model = selected.voiceOutput;
    if (!model) throw new Error("LOCAL_VOICE_OUTPUT_MODEL_UNAVAILABLE");
    if (!this.engine.isOutputLoaded(model.packageId, model.version)) {
      throw new Error("LOCAL_VOICE_OUTPUT_MODEL_NOT_LOADED");
    }
    return this.engine.synthesize({
      ...request,
      modelPackageId: model.packageId,
    });
  }
}
