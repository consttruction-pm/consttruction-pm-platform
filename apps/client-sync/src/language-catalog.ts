import type { LanguageRegistryEntry } from "./language.ts";
import type { LanguagePackStore } from "./language-pack-store.ts";

export type LanguageCatalogItem = {
  languageTag: string;
  direction: "ltr" | "rtl";
  locale: string;
  installedPackageId: string | null;
  installedVersion: string | null;
  verified: boolean;
  offlineReady: boolean;
  capabilities: LanguageRegistryEntry["capabilities"];
};

export class LanguageCatalogService {
  constructor(
    private readonly registry: readonly LanguageRegistryEntry[],
    private readonly store: LanguagePackStore,
  ) {}

  async list(): Promise<readonly LanguageCatalogItem[]> {
    const installed = await this.store.list();
    return this.registry.map((entry) => {
      const packs = installed.filter(
        (pack) => pack.languageTag === entry.languageTag,
      );
      const verified = packs.find((pack) => pack.verified) ?? null;
      return {
        languageTag: entry.languageTag,
        direction: entry.direction,
        locale: entry.locale,
        installedPackageId: verified?.packageId ?? null,
        installedVersion: verified?.version ?? null,
        verified: Boolean(verified),
        offlineReady: Boolean(verified && entry.capabilities.ui),
        capabilities: entry.capabilities,
      };
    });
  }
}
