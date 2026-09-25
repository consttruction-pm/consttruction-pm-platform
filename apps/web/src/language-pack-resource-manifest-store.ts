import type {
  CachedLanguagePackResources,
  LanguagePackResourceManifestStore,
} from "../../client-sync/src/language-pack-resource-manifest-store.js";

type StoredManifest = CachedLanguagePackResources & { key: string };

const DB_NAME = "construction-pm-language-pack-resource-manifests";
const DB_VERSION = 1;
const STORE_NAME = "manifests";

export class IndexedDbLanguagePackResourceManifestStore
  implements LanguagePackResourceManifestStore
{
  private readonly dbPromise: Promise<IDBDatabase>;

  constructor(databaseName = DB_NAME) {
    this.dbPromise = this.open(databaseName);
  }

  async get(packageId: string, version: string): Promise<CachedLanguagePackResources | null> {
    const db = await this.dbPromise;
    const record = await requestToPromise<StoredManifest | undefined>(() =>
      db.transaction(STORE_NAME, "readonly")
        .objectStore(STORE_NAME)
        .get(key(packageId, version)),
    );
    return record
      ? {
          packageId: record.packageId,
          languageTag: record.languageTag,
          version: record.version,
          resources: { ...record.resources },
        }
      : null;
  }

  async put(manifest: CachedLanguagePackResources): Promise<void> {
    const db = await this.dbPromise;
    const tx = db.transaction(STORE_NAME, "readwrite");
    tx.objectStore(STORE_NAME).put({
      ...manifest,
      resources: { ...manifest.resources },
      key: key(manifest.packageId, manifest.version),
    } satisfies StoredManifest);
    await transactionComplete(tx);
  }

  async remove(packageId: string, version: string): Promise<void> {
    const db = await this.dbPromise;
    const tx = db.transaction(STORE_NAME, "readwrite");
    tx.objectStore(STORE_NAME).delete(key(packageId, version));
    await transactionComplete(tx);
  }

  private open(databaseName: string): Promise<IDBDatabase> {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(databaseName, DB_VERSION);
      request.onupgradeneeded = () => {
        if (!request.result.objectStoreNames.contains(STORE_NAME)) {
          request.result.createObjectStore(STORE_NAME, { keyPath: "key" });
        }
      };
      request.onsuccess = () => resolve(request.result);
      request.onerror = () =>
        reject(request.error ?? new Error("LANGUAGE_RESOURCE_MANIFEST_DB_OPEN_FAILED"));
    });
  }
}

function key(packageId: string, version: string): string {
  return packageId + "@" + version;
}

function requestToPromise<T>(factory: () => IDBRequest<T>): Promise<T> {
  return new Promise((resolve, reject) => {
    const request = factory();
    request.onsuccess = () => resolve(request.result);
    request.onerror = () =>
      reject(request.error ?? new Error("LANGUAGE_RESOURCE_MANIFEST_DB_REQUEST_FAILED"));
  });
}

function transactionComplete(transaction: IDBTransaction): Promise<void> {
  return new Promise((resolve, reject) => {
    transaction.oncomplete = () => resolve();
    transaction.onerror = () =>
      reject(transaction.error ?? new Error("LANGUAGE_RESOURCE_MANIFEST_DB_TRANSACTION_FAILED"));
    transaction.onabort = () =>
      reject(transaction.error ?? new Error("LANGUAGE_RESOURCE_MANIFEST_DB_TRANSACTION_ABORTED"));
  });
}
