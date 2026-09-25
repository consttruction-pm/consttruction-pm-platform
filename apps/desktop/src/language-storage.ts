import { mkdir, readFile, rename, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";

import type {
  CachedLanguagePack,
} from "../../client-sync/src/language-pack-store.js";
import type {
  PersistentLanguagePackBackend,
} from "../../client-sync/src/persistent-language-pack-store.js";
import type {
  LanguagePreferenceStore,
} from "../../client-sync/src/language-preference-store.js";
import type {
  CachedLanguagePackResources,
  LanguagePackResourceManifestStore,
} from "../../client-sync/src/language-pack-resource-manifest-store.js";

const PACKS_FILE = "language-packs.json";
const PREFERENCE_FILE = "language-preference.txt";
const RESOURCE_MANIFEST_FILE = "language-pack-resources.json";

type SerializedPack = {
  packageId: string;
  languageTag: string;
  version: string;
  verified: boolean;
  artifactBase64: string;
};

export class DesktopFileLanguagePackBackend
  implements PersistentLanguagePackBackend
{
  constructor(private readonly directory: string) {}

  async load(): Promise<readonly CachedLanguagePack[]> {
    const file = join(this.directory, PACKS_FILE);
    try {
      const raw = await readFile(file, "utf8");
      const value = JSON.parse(raw) as SerializedPack[];
      return value.map(fromSerialized);
    } catch (error) {
      if (isNotFound(error)) return [];
      throw error;
    }
  }

  async save(packs: readonly CachedLanguagePack[]): Promise<void> {
    await mkdir(this.directory, { recursive: true });
    const file = join(this.directory, PACKS_FILE);
    const temp = file + ".tmp";
    const payload = JSON.stringify(packs.map(toSerialized));
    await writeFile(temp, payload, "utf8");
    await rename(temp, file);
  }
}

export class DesktopFileLanguagePreferenceStore
  implements LanguagePreferenceStore
{
  constructor(private readonly directory: string) {}

  async load(): Promise<string | null> {
    try {
      return (await readFile(join(this.directory, PREFERENCE_FILE), "utf8")).trim() || null;
    } catch (error) {
      if (isNotFound(error)) return null;
      throw error;
    }
  }

  async save(languageTag: string): Promise<void> {
    const normalized = languageTag.trim();
    if (!normalized) throw new Error("INVALID_LANGUAGE_PREFERENCE");
    await mkdir(this.directory, { recursive: true });
    const file = join(this.directory, PREFERENCE_FILE);
    const temp = file + ".tmp";
    await writeFile(temp, normalized, "utf8");
    await rename(temp, file);
  }
}

function toSerialized(pack: CachedLanguagePack): SerializedPack {
  return {
    packageId: pack.packageId,
    languageTag: pack.languageTag,
    version: pack.version,
    verified: pack.verified,
    artifactBase64: Buffer.from(pack.artifact).toString("base64"),
  };
}

function fromSerialized(pack: SerializedPack): CachedLanguagePack {
  if (
    !pack ||
    typeof pack.packageId !== "string" ||
    typeof pack.languageTag !== "string" ||
    typeof pack.version !== "string" ||
    pack.verified !== true ||
    typeof pack.artifactBase64 !== "string"
  ) {
    throw new Error("INVALID_PERSISTED_LANGUAGE_PACK");
  }

  return {
    packageId: pack.packageId,
    languageTag: pack.languageTag,
    version: pack.version,
    verified: true,
    artifact: new Uint8Array(Buffer.from(pack.artifactBase64, "base64")),
  };
}

function isNotFound(error: unknown): boolean {
  return Boolean(
    error &&
      typeof error === "object" &&
      "code" in error &&
      error.code === "ENOENT",
  );
}


export class DesktopFileLanguagePackResourceManifestStore
  implements LanguagePackResourceManifestStore
{
  constructor(private readonly directory: string) {}

  async get(packageId: string, version: string): Promise<CachedLanguagePackResources | null> {
    const manifests = await this.loadAll();
    return manifests.find(
      (item) => item.packageId === packageId && item.version === version,
    ) ?? null;
  }

  async put(manifest: CachedLanguagePackResources): Promise<void> {
    if (!manifest.packageId || !manifest.languageTag || !manifest.version) {
      throw new Error("INVALID_LANGUAGE_PACK_RESOURCE_MANIFEST");
    }
    const manifests = (await this.loadAll()).filter(
      (item) => !(item.packageId === manifest.packageId && item.version === manifest.version),
    );
    manifests.push({ ...manifest, resources: { ...manifest.resources } });
    await this.saveAll(manifests);
  }

  async remove(packageId: string, version: string): Promise<void> {
    await this.saveAll(
      (await this.loadAll()).filter(
        (item) => !(item.packageId === packageId && item.version === version),
      ),
    );
  }

  private async loadAll(): Promise<readonly CachedLanguagePackResources[]> {
    try {
      const raw = await readFile(join(this.directory, RESOURCE_MANIFEST_FILE), "utf8");
      const value = JSON.parse(raw) as CachedLanguagePackResources[];
      return value.map((item) => ({
        ...item,
        resources: { ...item.resources },
      }));
    } catch (error) {
      if (isNotFound(error)) return [];
      throw error;
    }
  }

  private async saveAll(
    manifests: readonly CachedLanguagePackResources[],
  ): Promise<void> {
    await mkdir(this.directory, { recursive: true });
    const file = join(this.directory, RESOURCE_MANIFEST_FILE);
    const temp = file + ".tmp";
    await writeFile(
      temp,
      JSON.stringify(manifests),
      "utf8",
    );
    await rename(temp, file);
  }
}
