import type {
  CachedLanguagePack,
  LanguagePackStore,
} from "../../client-sync/src/language-pack-store.js";

type StoredPack = {
  key: string;
  packageId: string;
  languageTag: string;
  version: string;
  verified: boolean;
  artifact: ArrayBuffer;
};

const DB_NAME = "construction-pm-language-packs";
const DB_VERSION = 1;
const STORE_NAME = "packs";

export class IndexedDbLanguagePackStore implements LanguagePackStore {
  private readonly dbPromise: Promise<IDBDatabase>;

  constructor(private readonly databaseName = DB_NAME) {
    this.dbPromise = this.open();
  }

  async list(): Promise<readonly CachedLanguagePack[]> {
    const db = await this.dbPromise;
    const records = await requestToPromise<StoredPack[]>(() => {
      const request = db.transaction(STORE_NAME, "readonly")
        .objectStore(STORE_NAME)
        .getAll();
      return request;
    });
    return records.map(fromStored);
  }

  async get(packageId: string, version: string): Promise<CachedLanguagePack | null> {
    const db = await this.dbPromise;
    const record = await requestToPromise<StoredPack | undefined>(() =>
      db.transaction(STORE_NAME, "readonly")
        .objectStore(STORE_NAME)
        .get(key(packageId, version)),
    );
    return record ? fromStored(record) : null;
  }

  async put(pack: CachedLanguagePack): Promise<void> {
    if (!pack.packageId || !pack.languageTag || !pack.version) {
      throw new Error("INVALID_LANGUAGE_PACK");
    }
    if (!pack.verified) {
      throw new Error("UNVERIFIED_LANGUAGE_PACK");
    }

    const db = await this.dbPromise;
    const tx = db.transaction(STORE_NAME, "readwrite");
    tx.objectStore(STORE_NAME).put({
      key: key(pack.packageId, pack.version),
      packageId: pack.packageId,
      languageTag: pack.languageTag,
      version: pack.version,
      verified: true,
      artifact: pack.artifact.slice().buffer,
    } satisfies StoredPack);
    await transactionComplete(tx);
  }

  async remove(packageId: string, version: string): Promise<void> {
    const db = await this.dbPromise;
    const tx = db.transaction(STORE_NAME, "readwrite");
    tx.objectStore(STORE_NAME).delete(key(packageId, version));
    await transactionComplete(tx);
  }

  private open(): Promise<IDBDatabase> {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(this.databaseName, DB_VERSION);

      request.onupgradeneeded = () => {
        const db = request.result;
        if (!db.objectStoreNames.contains(STORE_NAME)) {
          db.createObjectStore(STORE_NAME, { keyPath: "key" });
        }
      };

      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error ?? new Error("INDEXED_DB_OPEN_FAILED"));
    });
  }
}

function key(packageId: string, version: string): string {
  return packageId + "@" + version;
}

function fromStored(record: StoredPack): CachedLanguagePack {
  return {
    packageId: record.packageId,
    languageTag: record.languageTag,
    version: record.version,
    verified: record.verified,
    artifact: new Uint8Array(record.artifact.slice(0)),
  };
}

function requestToPromise<T>(factory: () => IDBRequest<T>): Promise<T> {
  return new Promise((resolve, reject) => {
    const request = factory();
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error ?? new Error("INDEXED_DB_REQUEST_FAILED"));
  });
}

function transactionComplete(transaction: IDBTransaction): Promise<void> {
  return new Promise((resolve, reject) => {
    transaction.oncomplete = () => resolve();
    transaction.onerror = () =>
      reject(transaction.error ?? new Error("INDEXED_DB_TRANSACTION_FAILED"));
    transaction.onabort = () =>
      reject(transaction.error ?? new Error("INDEXED_DB_TRANSACTION_ABORTED"));
  });
}
