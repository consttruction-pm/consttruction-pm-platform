import {
  ClientLanguageRuntime,
  type LanguagePreference,
} from "./language-runtime.js";
import type { LanguageRegistryEntry, ResolvedLanguage } from "./language.js";

export type LanguageShellActivationState =
  | "activated"
  | "not-required"
  | "resource-manifest-missing";

export type LanguageShellBootstrapResult = {
  language: ResolvedLanguage;
  activation: LanguageShellActivationState;
};

export type LanguageShellActivation = (
  packageId: string,
  version: string,
) => Promise<unknown>;

export class ClientLanguageShellLifecycle {
  constructor(
    private readonly runtime: ClientLanguageRuntime,
    private readonly activateCached: LanguageShellActivation,
  ) {}

  configure(
    registry: readonly LanguageRegistryEntry[],
    defaultLanguage: string,
    preference: LanguagePreference,
  ): ResolvedLanguage {
    return this.runtime.configure(registry, defaultLanguage, preference);
  }

  async initialize(): Promise<LanguageShellBootstrapResult> {
    await this.runtime.refreshInstalledPackState();
    const language = await this.runtime.restorePreferredLanguage();
    return this.activateResolved(language);
  }

  async switchToInstalledLanguage(
    languageTag: string,
  ): Promise<LanguageShellBootstrapResult> {
    const installed = await this.runtime.installedPacks();
    const pack = installed
      .filter((item) => item.languageTag === languageTag && item.verified)
      .sort((left, right) => right.version.localeCompare(left.version))[0];

    if (!pack) {
      const current = this.runtime.current();
      return {
        language: current,
        activation: "resource-manifest-missing",
      };
    }

    await this.activateCached(pack.packageId, pack.version);
    const language = this.runtime.setPreferredLanguage(languageTag);
    return {
      language,
      activation: "activated",
    };
  }

  current(): ResolvedLanguage {
    return this.runtime.current();
  }

  private async activateResolved(
    language: ResolvedLanguage,
  ): Promise<LanguageShellBootstrapResult> {
    if (!language.packVersion || !language.offline) {
      return {
        language,
        activation: "not-required",
      };
    }

    const installed = await this.runtime.installedPacks();
    const pack = installed.find(
      (item) =>
        item.languageTag === language.languageTag &&
        item.version === language.packVersion &&
        item.verified,
    );

    if (!pack) {
      return {
        language,
        activation: "resource-manifest-missing",
      };
    }

    try {
      await this.activateCached(pack.packageId, pack.version);
      return {
        language,
        activation: "activated",
      };
    } catch (error) {
      if (error instanceof Error &&
          error.message === "LANGUAGE_PACK_RESOURCE_MANIFEST_NOT_FOUND") {
        return {
          language,
          activation: "resource-manifest-missing",
        };
      }
      throw error;
    }
  }
}
