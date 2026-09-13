export class IndexedDBService {
  private dbName = "livestock_health_db";
  private dbVersion = 6;
  private db: IDBDatabase | null = null;

  async init(): Promise<void> {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(this.dbName, this.dbVersion);

      request.onerror = () => reject(request.error);

      request.onsuccess = () => {
        this.db = request.result;
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

  private async getDB(): Promise<IDBDatabase> {
    if (!this.db) await this.init();
    return this.db!;
  }

  async getAll(storeName: string): Promise<any[]> {
    const db = await this.getDB();
    return new Promise((resolve, reject) => {
      const transaction = db.transaction(storeName, "readonly");
      const store = transaction.objectStore(storeName);
      const request = store.getAll();
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  async save(storeName: string, item: any): Promise<void> {
    const db = await this.getDB();
    return new Promise((resolve, reject) => {
      const transaction = db.transaction(storeName, "readwrite");
      const store = transaction.objectStore(storeName);
      const request = store.put(item);
      request.onsuccess = () => resolve();
      request.onerror = () => reject(request.error);
    });
  }

  async delete(storeName: string, id: string): Promise<void> {
    const db = await this.getDB();
    return new Promise((resolve, reject) => {
      const transaction = db.transaction(storeName, "readwrite");
      const store = transaction.objectStore(storeName);
      const request = store.delete(id);
      request.onsuccess = () => resolve();
      request.onerror = () => reject(request.error);
    });
  }
}

export const dbService = new IndexedDBService();

