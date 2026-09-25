import type { DeviceCapabilityProfile, OfflineModelPack, PreferredLanguageModels } from "./offline-ai-model-selector.ts";
import { selectOfflineModels } from "./offline-ai-model-selector.ts";
import type { OfflineModelStore } from "./offline-ai-model-store.ts";

export class OfflineAIModelRuntime {
  constructor(
    private readonly store: OfflineModelStore,
    private preferredLanguage: string,
  ) {}

  setPreferredLanguage(languageTag: string): void {
    this.preferredLanguage = languageTag;
  }

  async select(
    appVersion: string,
    device: DeviceCapabilityProfile,
  ): Promise<PreferredLanguageModels> {
    return selectOfflineModels(
      this.preferredLanguage,
      appVersion,
      device,
      await this.store.list(),
    );
  }

  async installVerifiedModel(model: OfflineModelPack): Promise<void> {
    await this.store.put(model);
  }
}
