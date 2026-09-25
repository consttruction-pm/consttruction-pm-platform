import {
  mkdir,
  readFile,
  rename,
  rm,
  writeFile,
} from "node:fs/promises";
import { join } from "node:path";

import type {
  InstalledOfflineModelArtifact,
  OfflineModelArtifactStore,
} from "../../client-sync/src/offline-ai-model-artifact-store.js";

type Metadata = Omit<InstalledOfflineModelArtifact, "artifact"> & {
  artifactFile: string;
};

export class DesktopFileOfflineModelArtifactStore
  implements OfflineModelArtifactStore
{
  constructor(private readonly directory: string) {}

  async get(
    packageId: string,
    version: string,
  ): Promise<InstalledOfflineModelArtifact | null> {
    const base = baseName(packageId, version);
    try {
      const metadata = JSON.parse(
        await readFile(join(this.directory, base + ".json"), "utf8"),
      ) as Metadata;
      const artifact = new Uint8Array(
        await readFile(join(this.directory, metadata.artifactFile)),
      );
      return {
        packageId: metadata.packageId,
        languageTag: metadata.languageTag,
        modelType: metadata.modelType,
        version: metadata.version,
        verified: metadata.verified,
        artifact,
      };
    } catch (error) {
      if (isNotFound(error)) return null;
      throw error;
    }
  }

  async put(model: InstalledOfflineModelArtifact): Promise<void> {
    if (!model.verified) throw new Error("UNVERIFIED_OFFLINE_MODEL_ARTIFACT");
    if (!model.packageId || !model.version || model.artifact.byteLength === 0) {
      throw new Error("INVALID_OFFLINE_MODEL_ARTIFACT");
    }

    await mkdir(this.directory, { recursive: true });
    const base = baseName(model.packageId, model.version);
    const artifactFile = base + ".bin";
    const metadataFile = base + ".json";

    const artifactTemp = join(this.directory, artifactFile + ".tmp");
    const metadataTemp = join(this.directory, metadataFile + ".tmp");

    await writeFile(artifactTemp, Buffer.from(model.artifact));
    await rename(artifactTemp, join(this.directory, artifactFile));

    await writeFile(
      metadataTemp,
      JSON.stringify({
        packageId: model.packageId,
        languageTag: model.languageTag,
        modelType: model.modelType,
        version: model.version,
        verified: true,
        artifactFile,
      } satisfies Metadata),
      "utf8",
    );
    await rename(metadataTemp, join(this.directory, metadataFile));
  }

  async remove(packageId: string, version: string): Promise<void> {
    const base = baseName(packageId, version);
    await Promise.all([
      rm(join(this.directory, base + ".json"), { force: true }),
      rm(join(this.directory, base + ".bin"), { force: true }),
    ]);
  }
}

function baseName(packageId: string, version: string): string {
  return Buffer.from(packageId + "@" + version, "utf8").toString("base64url");
}

function isNotFound(error: unknown): boolean {
  return Boolean(
    error &&
      typeof error === "object" &&
      "code" in error &&
      error.code === "ENOENT",
  );
}
