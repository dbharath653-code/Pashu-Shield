/**
 * Small IndexedDB wrapper used as the app's offline datastore.
 *
 * IndexedDB can be unavailable (Safari private mode, disabled storage, quota
 * errors, blocked upgrades when another tab holds an old version). In those
 * cases we transparently degrade to an in-memory store so field workflows keep
 * working for the session instead of throwing on every read/write.
 */
export class IndexedDBService {
  private dbName = "livestock_health_db";
  private dbVersion = 6;
  private db: IDBDatabase | null = null;
  private memory = new Map<string, Map<string, any>>();
  private useMemoryFallback = false;

  private get supportsIndexedDB(): boolean {
    try {
      return typeof indexedDB !== "undefined" && indexedDB !== null;
    } catch {
      return false;
    }
  }

  private memoryStore(storeName: string): Map<string, any> {
    if (!this.memory.has(storeName)) this.memory.set(storeName, new Map());
    return this.memory.get(storeName)!;
  }

  /** Key used when writing into the in-memory fallback (mirrors the keyPath). */
  private keyFor(storeName: string, item: any): string {
    if (storeName === "sync_queue") return String(item?.localId ?? item?.id ?? crypto.randomUUID());
    return String(item?.id ?? crypto.randomUUID());
  }

  async init(): Promise<void> {
    if (this.db || this.useMemoryFallback || !this.supportsIndexedDB) {
      if (!this.supportsIndexedDB) this.useMemoryFallback = true;
      return;
    }

    return new Promise((resolve) => {
      let request: IDBOpenDBRequest;
      try {
        request = indexedDB.open(this.dbName, this.dbVersion);
      } catch (error) {
        console.warn("IndexedDB unavailable, using in-memory storage", error);
        this.useMemoryFallback = true;
        resolve();
        return;
      }

      request.onerror = () => {
        console.warn("IndexedDB could not be opened, using in-memory storage", request.error);
        this.useMemoryFallback = true;
        resolve();
      };

      request.onblocked = () => {
        console.warn("IndexedDB upgrade blocked by another tab, using in-memory storage");
        this.useMemoryFallback = true;
        resolve();
      };

      request.onsuccess = () => {
        this.db = request.result;
        // If another tab triggers a version upgrade we simply keep working with
        // the current handle until the page is reloaded.
        this.db.onversionchange = () => this.db?.close();
        resolve();
      };

      request.onupgradeneeded = (event: IDBVersionChangeEvent) => {
        const db = (event.target as IDBOpenDBRequest).result;

        if (!db.objectStoreNames.contains("animals")) {
          db.createObjectStore("animals", { keyPath: "id" });
        }
        if (!db.objectStoreNames.contains("herds")) {
          db.createObjectStore("herds", { keyPath: "id" });
        }
        if (!db.objectStoreNames.contains("health_records")) {
          db.createObjectStore("health_records", { keyPath: "id" });
        }
        if (!db.objectStoreNames.contains("vet_cases")) {
          db.createObjectStore("vet_cases", { keyPath: "id" });
        }
        if (!db.objectStoreNames.contains("lab_samples")) {
          db.createObjectStore("lab_samples", { keyPath: "id" });
        }
        if (!db.objectStoreNames.contains("vaccinations")) {
          db.createObjectStore("vaccinations", { keyPath: "id" });
        }
        if (!db.objectStoreNames.contains("vaccination_campaigns")) {
          db.createObjectStore("vaccination_campaigns", { keyPath: "id" });
        }
        if (!db.objectStoreNames.contains("alerts")) {
          db.createObjectStore("alerts", { keyPath: "id" });
        }
        if (!db.objectStoreNames.contains("voice_reports")) {
          db.createObjectStore("voice_reports", { keyPath: "id" });
        }
        if (!db.objectStoreNames.contains("sync_queue")) {
          db.createObjectStore("sync_queue", { keyPath: "localId" });
        }
      };
    });
  }

  private async getDB(): Promise<IDBDatabase | null> {
    if (!this.db && !this.useMemoryFallback) await this.init();
    return this.db;
  }

  async getAll<T = any>(storeName: string): Promise<T[]> {
    const db = await this.getDB();
    if (!db) return [...this.memoryStore(storeName).values()] as T[];

    try {
      return await new Promise<T[]>((resolve, reject) => {
        const transaction = db.transaction(storeName, "readonly");
        const store = transaction.objectStore(storeName);
        const request = store.getAll();
        request.onsuccess = () => resolve(request.result as T[]);
        request.onerror = () => reject(request.error);
      });
    } catch (error) {
      console.warn(`Read from "${storeName}" failed, using in-memory storage`, error);
      this.useMemoryFallback = true;
      return [...this.memoryStore(storeName).values()] as T[];
    }
  }

  async save(storeName: string, item: any): Promise<void> {
    const db = await this.getDB();
    if (!db) {
      this.memoryStore(storeName).set(this.keyFor(storeName, item), item);
      return;
    }

    try {
      await new Promise<void>((resolve, reject) => {
        const transaction = db.transaction(storeName, "readwrite");
        const store = transaction.objectStore(storeName);
        const request = store.put(item);
        request.onsuccess = () => resolve();
        request.onerror = () => reject(request.error);
      });
    } catch (error) {
      console.warn(`Write to "${storeName}" failed, using in-memory storage`, error);
      this.memoryStore(storeName).set(this.keyFor(storeName, item), item);
    }
  }

  async delete(storeName: string, id: string): Promise<void> {
    const db = await this.getDB();
    if (!db) {
      this.memoryStore(storeName).delete(id);
      return;
    }

    try {
      await new Promise<void>((resolve, reject) => {
        const transaction = db.transaction(storeName, "readwrite");
        const store = transaction.objectStore(storeName);
        const request = store.delete(id);
        request.onsuccess = () => resolve();
        request.onerror = () => reject(request.error);
      });
    } catch (error) {
      console.warn(`Delete from "${storeName}" failed, using in-memory storage`, error);
      this.memoryStore(storeName).delete(id);
    }
  }
}

export const dbService = new IndexedDBService();
