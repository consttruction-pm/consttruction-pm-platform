export type CachedLanguagePackResources = {
  packageId: string;
  languageTag: string;
  version: string;
  resources: {
    translation: string;
    glossary: string;
    help: string;
    reports: string;
  };
};

export interface LanguagePackResourceManifestStore {
  get(packageId: string, version: string): Promise<CachedLanguagePackResources | null>;
  put(manifest: CachedLanguagePackResources): Promise<void>;
  remove(packageId: string, version: string): Promise<void>;
}

export class InMemoryLanguagePackResourceManifestStore
  implements LanguagePackResourceManifestStore
{
  private readonly manifests = new Map<string, CachedLanguagePackResources>();

  async get(packageId: string, version: string): Promise<CachedLanguagePackResources | null> {
    const value = this.manifests.get(packageId + "@" + version);
    return value ? clone(value) : null;
  }

  async put(manifest: CachedLanguagePackResources): Promise<void> {
    if (!manifest.packageId || !manifest.languageTag || !manifest.version) {
      throw new Error("INVALID_LANGUAGE_PACK_RESOURCE_MANIFEST");
    }
    this.manifests.set(manifest.packageId + "@" + manifest.version, clone(manifest));
  }

  async remove(packageId: string, version: string): Promise<void> {
    this.manifests.delete(packageId + "@" + version);
  }
}

function clone(value: CachedLanguagePackResources): CachedLanguagePackResources {
  return {
    ...value,
    resources: { ...value.resources },
  };
}
