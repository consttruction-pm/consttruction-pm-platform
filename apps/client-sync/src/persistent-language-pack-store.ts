import type {
  CachedLanguagePack,
  LanguagePackStore,
} from "./language-pack-store.ts";

export interface PersistentLanguagePackBackend {
  load(): Promise<readonly CachedLanguagePack[]>;
  save(packs: readonly CachedLanguagePack[]): Promise<void>;
}

export class PersistentLanguagePackStore implements LanguagePackStore {
  private statePromise: Promise<Map<string, CachedLanguagePack>> | null = null;

  constructor(private readonly backend: PersistentLanguagePackBackend) {}

  async list(): Promise<readonly CachedLanguagePack[]> {
    const state = await this.state();
    return [...state.values()].map(clonePack);
  }

  async get(packageId: string, version: string): Promise<CachedLanguagePack | null> {
    const state = await this.state();
    const pack = state.get(key(packageId, version));
    return pack ? clonePack(pack) : null;
  }

  async put(pack: CachedLanguagePack): Promise<void> {
    validatePack(pack);
    const state = await this.state();
    state.set(key(pack.packageId, pack.version), clonePack(pack));
    await this.backend.save([...state.values()].map(clonePack));
  }

  async remove(packageId: string, version: string): Promise<void> {
    const state = await this.state();
    state.delete(key(packageId, version));
    await this.backend.save([...state.values()].map(clonePack));
  }

  private async state(): Promise<Map<string, CachedLanguagePack>> {
    if (!this.statePromise) {
      this.statePromise = this.backend.load().then((packs) => {
        const state = new Map<string, CachedLanguagePack>();
        for (const pack of packs) {
          validatePack(pack);
          state.set(key(pack.packageId, pack.version), clonePack(pack));
        }
        return state;
      });
    }
    return this.statePromise;
  }
}

function validatePack(pack: CachedLanguagePack): void {
  if (!pack.packageId || !pack.languageTag || !pack.version) {
    throw new Error("INVALID_LANGUAGE_PACK");
  }
  if (!pack.verified) {
    throw new Error("UNVERIFIED_LANGUAGE_PACK");
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
