import type {
  InstalledOfflineModelArtifact,
  OfflineModelArtifactStore,
} from "../../client-sync/src/offline-ai-model-artifact-store.js";

type RecordValue = Omit<InstalledOfflineModelArtifact, "artifact"> & {
  artifact: ArrayBuffer;
};

export class IndexedDbOfflineModelArtifactStore
  implements OfflineModelArtifactStore
{
  private readonly dbPromise: Promise<IDBDatabase>;

  constructor(
    private readonly databaseName = "construction-pm-ai-models",
    private readonly storeName = "artifacts",
  ) {
    this.dbPromise = openDatabase(databaseName, storeName);
  }

  async get(
    packageId: string,
    version: string,
  ): Promise<InstalledOfflineModelArtifact | null> {
    const db = await this.dbPromise;
    const key = packageId + "@" + version;
    const value = await request<RecordValue | undefined>(
      db,
      this.storeName,
      "readonly",
      (store) => store.get(key),
    );
    if (!value) return null;
    return {
      ...value,
      artifact: new Uint8Array(value.artifact.slice(0)),
    };
  }

  async put(model: InstalledOfflineModelArtifact): Promise<void> {
    if (!model.verified) throw new Error("UNVERIFIED_OFFLINE_MODEL_ARTIFACT");
    if (!model.packageId || !model.version || model.artifact.byteLength === 0) {
      throw new Error("INVALID_OFFLINE_MODEL_ARTIFACT");
    }

    const db = await this.dbPromise;
    const key = model.packageId + "@" + model.version;
    const buffer = model.artifact.slice().buffer;
    await request(
      db,
      this.storeName,
      "readwrite",
      (store) =>
        store.put({
          ...model,
          artifact: buffer,
        } satisfies RecordValue, key),
    );
  }

  async remove(packageId: string, version: string): Promise<void> {
    const db = await this.dbPromise;
    await request(
      db,
      this.storeName,
      "readwrite",
      (store) => store.delete(packageId + "@" + version),
    );
  }
}

function openDatabase(
  databaseName: string,
  storeName: string,
): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(databaseName, 1);
    request.onerror = () => reject(request.error ?? new Error("INDEXED_DB_OPEN_FAILED"));
    request.onupgradeneeded = () => {
      if (!request.result.objectStoreNames.contains(storeName)) {
        request.result.createObjectStore(storeName);
      }
    };
    request.onsuccess = () => resolve(request.result);
  });
}

function request<T>(
  db: IDBDatabase,
  storeName: string,
  mode: IDBTransactionMode,
  operation: (store: IDBObjectStore) => IDBRequest<T>,
): Promise<T> {
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(storeName, mode);
    const store = transaction.objectStore(storeName);
    const request = operation(store);
    request.onerror = () => reject(
      request.error ?? new Error("INDEXED_DB_REQUEST_FAILED"),
    );
    request.onsuccess = () => resolve(request.result);
  });
}
