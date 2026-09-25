export type LanguageDirection = "ltr" | "rtl";

export interface LanguageCapabilitySet {
  ui: boolean;
  help: boolean;
  aiText: boolean;
  voiceInput: boolean;
  voiceOutput: boolean;
  offlineAi: boolean;
}

export interface InstalledLanguagePack {
  languageTag: string;
  version: string;
  active: boolean;
  verified: boolean;
  capabilities: LanguageCapabilitySet;
}

export interface LanguageRegistryEntry {
  languageTag: string;
  direction: LanguageDirection;
  locale: string;
  fallbackChain: string[];
  capabilities: LanguageCapabilitySet;
}

export interface LanguagePreference {
  preferredLanguage: string;
  fallbackChain: string[];
  installedPacks: InstalledLanguagePack[];
}

export interface ResolvedLanguage {
  languageTag: string;
  source: "preferred" | "fallback" | "default";
  direction: LanguageDirection;
  locale: string;
  packVersion: string | null;
  offline: boolean;
}

export class ClientLanguageManager {
  constructor(
    private readonly registry: readonly LanguageRegistryEntry[],
    private readonly defaultLanguage: string,
    private preference: LanguagePreference,
  ) {}

  getPreference(): LanguagePreference {
    return {
      preferredLanguage: this.preference.preferredLanguage,
      fallbackChain: [...this.preference.fallbackChain],
      installedPacks: this.preference.installedPacks.map((pack) => ({ ...pack })),
    };
  }

  setPreferredLanguage(languageTag: string): ResolvedLanguage {
    this.preference = {
      ...this.preference,
      preferredLanguage: languageTag,
    };
    return this.resolve();
  }

  setInstalledPacks(installedPacks: readonly InstalledLanguagePack[]): ResolvedLanguage {
    this.preference = {
      ...this.preference,
      installedPacks: installedPacks.map((pack) => ({ ...pack })),
    };
    return this.resolve();
  }

  resolve(): ResolvedLanguage {
    const candidates = [
      { tag: this.preference.preferredLanguage, source: "preferred" as const },
      ...this.preference.fallbackChain.map((tag) => ({ tag, source: "fallback" as const })),
      { tag: this.defaultLanguage, source: "default" as const },
    ];

    let firstRegistered: ResolvedLanguage | null = null;

    for (const candidate of candidates) {
      const entry = this.registry.find((item) => item.languageTag === candidate.tag);
      if (!entry) continue;

      const pack = this.preference.installedPacks.find(
        (item) => item.languageTag === candidate.tag && item.verified,
      );

      if (pack) {
        return {
          languageTag: entry.languageTag,
          source: candidate.source,
          direction: entry.direction,
          locale: entry.locale,
          packVersion: pack.version,
          offline: true,
        };
      }

      // Keep the first registered language as a non-offline fallback only
      // after every preferred/fallback candidate has been checked for a pack.
      if (!firstRegistered) {
        firstRegistered = {
          languageTag: entry.languageTag,
          source: candidate.source,
          direction: entry.direction,
          locale: entry.locale,
          packVersion: null,
          offline: false,
        };
      }
    }

    if (firstRegistered) {
      return firstRegistered;
    }

    throw new Error("no registered language is available");
  }

  canRunOffline(languageTag: string): boolean {
    const entry = this.registry.find((item) => item.languageTag === languageTag);
    const pack = this.preference.installedPacks.find(
      (item) => item.languageTag === languageTag && item.verified,
    );
    return Boolean(entry?.capabilities.ui && pack?.capabilities.ui);
  }
}
