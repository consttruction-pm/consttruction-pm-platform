import type { ClientLanguageRuntime } from "./language-runtime.ts";
import type {
  DeviceCapabilityProfile,
  PreferredLanguageModels,
} from "./offline-ai-model-selector.ts";
import type { OfflineAIModelRuntime } from "./offline-ai-model-runtime.ts";
import type { LanguageBoundAIService } from "./language-bound-ai-service.ts";

export type MultilingualCapabilityState = {
  language: string;
  offlineModels: PreferredLanguageModels;
};

export class MultilingualCapabilityCoordinator {
  constructor(
    private readonly languageRuntime: ClientLanguageRuntime,
    private readonly offlineAiRuntime: OfflineAIModelRuntime,
    private readonly aiService: LanguageBoundAIService,
  ) {}

  async setLanguage(
    languageTag: string,
    appVersion: string,
    device: DeviceCapabilityProfile,
  ): Promise<MultilingualCapabilityState> {
    this.languageRuntime.setPreferredLanguage(languageTag);
    this.offlineAiRuntime.setPreferredLanguage(languageTag);
    this.aiService.setPreferredLanguage(languageTag);

    return {
      language: languageTag,
      offlineModels: await this.offlineAiRuntime.select(appVersion, device),
    };
  }

  async currentCapabilities(
    appVersion: string,
    device: DeviceCapabilityProfile,
  ): Promise<MultilingualCapabilityState> {
    const current = this.languageRuntime.current();
    this.offlineAiRuntime.setPreferredLanguage(current.languageTag);
    this.aiService.setPreferredLanguage(current.languageTag);

    return {
      language: current.languageTag,
      offlineModels: await this.offlineAiRuntime.select(appVersion, device),
    };
  }
}
