import type {
  CachedLanguagePack,
  LanguagePackStore,
} from "../../client-sync/src/language-pack-store.js";
import type {
  LanguagePreferenceStore,
} from "../../client-sync/src/language-preference-store.js";
import type {
  CachedLanguagePackResources,
  LanguagePackResourceManifestStore,
} from "../../client-sync/src/language-pack-resource-manifest-store.js";

export interface MobileKeyValueStorage {
  get(key: string): Promise<string | null>;
  set(key: string, value: string): Promise<void>;
  remove(key: string): Promise<void>;
}

const PACKS_KEY = "construction-pm.language-packs";
const PREFERENCE_KEY = "construction-pm.preferred-language";
const RESOURCE_MANIFESTS_KEY = "construction-pm.language-pack-resource-manifests";

export class MobileKeyValueLanguagePackStore implements LanguagePackStore {
  constructor(private readonly storage: MobileKeyValueStorage) {}

  async list(): Promise<readonly CachedLanguagePack[]> {
    const raw = await this.storage.get(PACKS_KEY);
    if (!raw) return [];
    const value = JSON.parse(raw) as Array<Omit<CachedLanguagePack, "artifact"> & { artifactBase64: string }>;
    return value.map((item) => ({
      packageId: item.packageId,
      languageTag: item.languageTag,
      version: item.version,
      verified: item.verified,
      artifact: base64ToBytes(item.artifactBase64),
    }));
  }

  async get(packageId: string, version: string): Promise<CachedLanguagePack | null> {
    const packs = await this.list();
    return packs.find(
      (pack) => pack.packageId === packageId && pack.version === version,
    ) ?? null;
  }

  async put(pack: CachedLanguagePack): Promise<void> {
    if (!pack.packageId || !pack.languageTag || !pack.version) {
      throw new Error("INVALID_LANGUAGE_PACK");
    }
    if (!pack.verified) {
      throw new Error("UNVERIFIED_LANGUAGE_PACK");
    }

    const packs = (await this.list()).filter(
      (item) => !(item.packageId === pack.packageId && item.version === pack.version),
    );
    packs.push({ ...pack, artifact: new Uint8Array(pack.artifact) });
    await this.storage.set(
      PACKS_KEY,
      JSON.stringify(
        packs.map((item) => ({
          packageId: item.packageId,
          languageTag: item.languageTag,
          version: item.version,
          verified: item.verified,
          artifactBase64: bytesToBase64(item.artifact),
        })),
      ),
    );
  }

  async remove(packageId: string, version: string): Promise<void> {
    const packs = (await this.list()).filter(
      (item) => !(item.packageId === packageId && item.version === version),
    );
    await this.storage.set(
      PACKS_KEY,
      JSON.stringify(
        packs.map((item) => ({
          packageId: item.packageId,
          languageTag: item.languageTag,
          version: item.version,
          verified: item.verified,
          artifactBase64: bytesToBase64(item.artifact),
        })),
      ),
    );
  }
}

export class MobileKeyValueLanguagePreferenceStore
  implements LanguagePreferenceStore
{
  constructor(private readonly storage: MobileKeyValueStorage) {}

  async load(): Promise<string | null> {
    return this.storage.get(PREFERENCE_KEY);
  }

  async save(languageTag: string): Promise<void> {
    const normalized = languageTag.trim();
    if (!normalized) throw new Error("INVALID_LANGUAGE_PREFERENCE");
    await this.storage.set(PREFERENCE_KEY, normalized);
  }
}

function bytesToBase64(bytes: Uint8Array): string {
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary);
}

function base64ToBytes(value: string): Uint8Array {
  const binary = atob(value);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }
  return bytes;
}


export class MobileKeyValueLanguagePackResourceManifestStore
  implements LanguagePackResourceManifestStore
{
  constructor(private readonly storage: MobileKeyValueStorage) {}

  async get(packageId: string, version: string): Promise<CachedLanguagePackResources | null> {
    const manifests = await this.list();
    return manifests.find(
      (item) => item.packageId === packageId && item.version === version,
    ) ?? null;
  }

  async put(manifest: CachedLanguagePackResources): Promise<void> {
    if (!manifest.packageId || !manifest.languageTag || !manifest.version) {
      throw new Error("INVALID_LANGUAGE_PACK_RESOURCE_MANIFEST");
    }
    const manifests = (await this.list()).filter(
      (item) => !(item.packageId === manifest.packageId && item.version === manifest.version),
    );
    manifests.push({ ...manifest, resources: { ...manifest.resources } });
    await this.storage.set(RESOURCE_MANIFESTS_KEY, JSON.stringify(manifests));
  }

  async remove(packageId: string, version: string): Promise<void> {
    const manifests = (await this.list()).filter(
      (item) => !(item.packageId === packageId && item.version === version),
    );
    await this.storage.set(RESOURCE_MANIFESTS_KEY, JSON.stringify(manifests));
  }

  private async list(): Promise<readonly CachedLanguagePackResources[]> {
    const raw = await this.storage.get(RESOURCE_MANIFESTS_KEY);
    if (!raw) return [];
    const value = JSON.parse(raw) as CachedLanguagePackResources[];
    return value.map((item) => ({
      ...item,
      resources: { ...item.resources },
    }));
  }
}
