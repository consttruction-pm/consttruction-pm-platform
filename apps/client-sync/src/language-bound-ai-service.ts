import type { AILanguageContext } from "./ai-language-contract.ts";
import type {
  DeviceCapabilityProfile,
  PreferredLanguageModels,
} from "./offline-ai-model-selector.ts";
import { selectOfflineModels } from "./offline-ai-model-selector.ts";
import type { OfflineModelStore } from "./offline-ai-model-store.ts";

export type AIExecutionMode = "offline" | "online";

export type AIExecutionDecision = {
  mode: AIExecutionMode;
  language: string;
  modelPackageId: string | null;
  reason: "offline_model_available" | "offline_model_unavailable" | "offline_policy_disabled";
};

export interface LocalAIProvider {
  complete(
    request: AILanguageContext,
    modelPackageId: string,
  ): Promise<string>;
}

export interface OnlineAIProvider {
  complete(request: AILanguageContext): Promise<string>;
}

export class LanguageBoundAIService {
  constructor(
    private readonly modelStore: OfflineModelStore,
    private readonly localProvider: LocalAIProvider,
    private readonly onlineProvider: OnlineAIProvider,
    private preferredLanguage: string,
  ) {}

  setPreferredLanguage(languageTag: string): void {
    this.preferredLanguage = languageTag;
  }

  async decide(
    appVersion: string,
    device: DeviceCapabilityProfile,
  ): Promise<AIExecutionDecision> {
    const selected = selectOfflineModels(
      this.preferredLanguage,
      appVersion,
      device,
      await this.modelStore.list(),
    );

    if (device.offlineAiAllowed && selected.aiText) {
      return {
        mode: "offline",
        language: this.preferredLanguage,
        modelPackageId: selected.aiText.packageId,
        reason: "offline_model_available",
      };
    }

    return {
      mode: "online",
      language: this.preferredLanguage,
      modelPackageId: null,
      reason: device.offlineAiAllowed
        ? "offline_model_unavailable"
        : "offline_policy_disabled",
    };
  }

  async complete(
    request: AILanguageContext,
    appVersion: string,
    device: DeviceCapabilityProfile,
  ): Promise<{ mode: AIExecutionMode; text: string }> {
    if (!request.text_capable) {
      throw new Error("AI_TEXT_OUTPUT_UNAVAILABLE");
    }
    const decision = await this.decide(appVersion, device);

    if (decision.mode === "offline" && decision.modelPackageId) {
      return {
        mode: "offline",
        text: await this.localProvider.complete(
          request,
          decision.modelPackageId,
        ),
      };
    }

    return {
      mode: "online",
      text: await this.onlineProvider.complete(request),
    };
  }
}
