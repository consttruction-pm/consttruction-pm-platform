export interface CachedLanguagePack {
  packageId: string;
  languageTag: string;
  version: string;
  verified: boolean;
  artifact: Uint8Array;
}

export interface LanguagePackStore {
  list(): Promise<readonly CachedLanguagePack[]>;
  get(packageId: string, version: string): Promise<CachedLanguagePack | null>;
  put(pack: CachedLanguagePack): Promise<void>;
  remove(packageId: string, version: string): Promise<void>;
}

export class InMemoryLanguagePackStore implements LanguagePackStore {
  private readonly packs = new Map<string, CachedLanguagePack>();

  async list(): Promise<readonly CachedLanguagePack[]> {
    return [...this.packs.values()].map(clonePack);
  }

  async get(packageId: string, version: string): Promise<CachedLanguagePack | null> {
    const pack = this.packs.get(key(packageId, version));
    return pack ? clonePack(pack) : null;
  }

  async put(pack: CachedLanguagePack): Promise<void> {
    if (!pack.packageId || !pack.languageTag || !pack.version) {
      throw new Error("INVALID_LANGUAGE_PACK");
    }
    if (!pack.verified) {
      throw new Error("UNVERIFIED_LANGUAGE_PACK");
    }
    this.packs.set(key(pack.packageId, pack.version), clonePack(pack));
  }

  async remove(packageId: string, version: string): Promise<void> {
    this.packs.delete(key(packageId, version));
  }
}

function key(packageId: string, version: string): string {
  return packageId + "@" + version;
}

function clonePack(pack: CachedLanguagePack): CachedLanguagePack {
  return {
    ...pack,
    artifact: new Uint8Array(pack.artifact),
  };
}
