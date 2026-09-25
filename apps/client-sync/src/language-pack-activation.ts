import type { LanguagePackManifest } from "./language-pack-manifest.ts";
import type { LanguagePackStore } from "./language-pack-store.ts";
import {
  LanguageResourceRuntime,
  type LanguageResourceBundle,
} from "./language-resource-runtime.ts";

export type ActiveLanguageBundle = {
  languageTag: string;
  version: string;
  bundle: LanguageResourceBundle;
};

export class LanguagePackActivationService {
  private active: ActiveLanguageBundle | null = null;

  constructor(
    private readonly store: LanguagePackStore,
    private readonly resources: LanguageResourceRuntime,
  ) {}

  async activate(manifest: LanguagePackManifest): Promise<ActiveLanguageBundle> {
    const cached = await this.store.get(
      manifest.package_id,
      manifest.version,
    );

    if (!cached || !cached.verified) {
      throw new Error("LANGUAGE_PACK_NOT_VERIFIED");
    }

    if (cached.languageTag !== manifest.language_tag) {
      throw new Error("LANGUAGE_PACK_LANGUAGE_MISMATCH");
    }

    const bundle = await this.resources.installBundle(
      manifest.language_tag,
      manifest.version,
      cached.artifact,
      {
        translation: manifest.resources.translation,
        glossary: manifest.resources.glossary,
        help: manifest.resources.help,
        reports: manifest.resources.reports,
      },
    );

    const next = {
      languageTag: manifest.language_tag,
      version: manifest.version,
      bundle,
    };
    this.active = next;
    return next;
  }

  current(): ActiveLanguageBundle | null {
    return this.active;
  }

  deactivate(): void {
    if (!this.active) return;
    this.resources.removeBundle(
      this.active.languageTag,
      this.active.version,
    );
    this.active = null;
  }
}
