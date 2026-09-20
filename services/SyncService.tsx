import React, { createContext, useContext, useState, useEffect, useCallback, useMemo } from "react";
import { dbService } from "./db/IndexedDBService";
import { ReportingService } from "./ReportingService";
import { useAuth } from "../context/AuthContext";

export interface SyncQueueItem {
  localId: string;
  idempotencyKey: string;
  store: string;
  id: string;
  type: string;
  operation: "CREATE" | "UPDATE" | "DELETE";
  data: any;
  status: "Pending" | "Syncing" | "Synced" | "Failed" | "Conflict";
  attempts: number;
  lastAttemptAt?: string;
  lastError?: string;
  queuedAt: string;
}

export interface ActivityEvent {
  id: string;
  type:
    | "DISEASE_REPORT"
    | "VACCINATION"
    | "AI_ALERT"
    | "VET_CASE"
    | "LAB_RESULT"
    | "SYSTEM_SYNC"
    | "OUTBREAK";
  title: string;
  description?: string;
  timestamp: string; // ISO string preserved internally
  severity: "info" | "success" | "warning" | "high" | "critical";
  source?: string;
  entityId?: string;
  entityType?: string;
  targetRoute?: string;
  metadata?: Record<string, unknown>;
}

interface SyncContextType {
  // Network detection: distinguishes device vs backend
  isOnline: boolean;
  serverReachable: boolean;
  networkStatus: "ONLINE" | "OFFLINE" | "SERVER_UNAVAILABLE";

  // Sync state
  syncQueue: SyncQueueItem[];
  pendingCount: number;
  failedCount: number;
  isSyncing: boolean;
  lastSyncTime: Date | null;
  syncNow: () => Promise<void>;
  enqueueOfflineItem: (
    store: string,
    id: string,
    type: string,
    data: any,
    operation?: "CREATE" | "UPDATE" | "DELETE"
  ) => Promise<void>;
  retryFailedItem: (localId: string) => Promise<void>;
  clearSyncedHistory: () => Promise<void>;

  // Activity feed & Live Event Stream
  activityEvents: ActivityEvent[];
  feedStatus: "LIVE" | "UPDATING" | "OFFLINE";
  addActivityEvent: (event: Omit<ActivityEvent, "id">) => void;
  refreshActivityFeed: () => Promise<void>;

  // UI Modal control
  isSyncModalOpen: boolean;
  openSyncModal: () => void;
  closeSyncModal: () => void;
}

const SyncContext = createContext<SyncContextType | undefined>(undefined);

export function SyncProvider({ children }: { children: React.ReactNode }) {
  const { wsStatus, token } = useAuth();

  const [isOnline, setIsOnline] = useState<boolean>(
    typeof navigator !== "undefined" ? navigator.onLine : true
  );
  const [serverReachable, setServerReachable] = useState<boolean>(true);
  const [syncQueue, setSyncQueue] = useState<SyncQueueItem[]>([]);
  const [isSyncing, setIsSyncing] = useState<boolean>(false);
  const [lastSyncTime, setLastSyncTime] = useState<Date | null>(() => {
    const saved = localStorage.getItem("pashu_last_sync_time");
    return saved ? new Date(saved) : new Date();
  });
  const [isSyncModalOpen, setIsSyncModalOpen] = useState(false);

  const [activityEvents, setActivityEvents] = useState<ActivityEvent[]>([]);
  const [feedStatus, setFeedStatus] = useState<"LIVE" | "UPDATING" | "OFFLINE">("LIVE");

  // Determine aggregate network status
  const networkStatus: "ONLINE" | "OFFLINE" | "SERVER_UNAVAILABLE" = !isOnline
    ? "OFFLINE"
    : !serverReachable
    ? "SERVER_UNAVAILABLE"
    : "ONLINE";

  // Feed status updates based on WS + Network
  useEffect(() => {
    if (!isOnline) {
      setFeedStatus("OFFLINE");
    } else if (wsStatus === "CONNECTED") {
      setFeedStatus("LIVE");
    } else if (wsStatus === "RECONNECTING" || wsStatus === "SYNCING") {
      setFeedStatus("UPDATING");
    } else {
      setFeedStatus(serverReachable ? "LIVE" : "OFFLINE");
    }
  }, [isOnline, wsStatus, serverReachable]);

  // Lightweight backend connectivity check
  const checkServerReachability = useCallback(async (): Promise<boolean> => {
    if (!navigator.onLine) {
      setServerReachable(false);
      return false;
    }
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 4000);
      const res = await fetch("/api/v1/sync/pull", {
        method: "HEAD",
        signal: controller.signal
      }).catch(() => null);
      clearTimeout(timeoutId);

      // If backend responded with any HTTP status (even 404/405/200), server is reachable.
      // If network failed completely or timed out, res is null.
      if (res !== null) {
        setServerReachable(true);
        return true;
      }
      setServerReachable(false);
      return false;
    } catch {
      setServerReachable(false);
      return false;
    }
  }, []);

  // Load sync queue from IndexedDB and sync legacy localStorage reporting queue
  const loadSyncQueue = useCallback(async () => {
    await dbService.init();

    // 1. Read existing sync_queue in IndexedDB
    let dbQueue: SyncQueueItem[] = await dbService.getAll<SyncQueueItem>("sync_queue");

    // 2. Check for legacy items in ReportingService localStorage queue and migrate them
    try {
      const legacyReports = ReportingService.getSyncQueue();
      if (legacyReports && legacyReports.length > 0) {
        for (const r of legacyReports) {
          const reportLocalId = `REP-${r.id || Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
          const exists = dbQueue.some((q) => q.data?.id === r.id || q.localId === reportLocalId);
          if (!exists) {
            const newItem: SyncQueueItem = {
              localId: reportLocalId,
              idempotencyKey: `idemp-report-${r.id || Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
              store: "reports",
              id: r.id || reportLocalId,
              type: `Disease Report (${r.disease || r.species || "Unknown"})`,
              operation: "CREATE",
              data: r,
              status: "Pending",
              attempts: 0,
              queuedAt: r.queuedAt || new Date().toISOString()
            };
            await dbService.save("sync_queue", newItem);
            dbQueue.push(newItem);
          }
        }
        ReportingService.clearSyncQueue();
      }
    } catch (e) {
      console.warn("Could not check legacy reporting sync queue:", e);
    }

    // 3. Scan domain stores for pending sync items
    try {
      const [animals, herds, vetCases, labSamples, vaccinations, voiceReports] = await Promise.all([
        dbService.getAll("animals"),
        dbService.getAll("herds"),
        dbService.getAll("vet_cases"),
        dbService.getAll("lab_samples"),
        dbService.getAll("vaccinations"),
        dbService.getAll("voice_reports")
      ]);

      const mapToQueue = async (items: any[], store: string, typeLabel: string) => {
        for (const item of items) {
          if (item.syncStatus === "Pending") {
            const existing = dbQueue.find((q) => q.store === store && q.id === item.id);
            if (!existing) {
              const queueItem: SyncQueueItem = {
                localId: `SQ-${store}-${item.id}`,
                idempotencyKey: `idemp-${store}-${item.id}`,
                store,
                id: item.id,
                type: typeLabel,
                operation: "CREATE",
                data: item,
                status: "Pending",
                attempts: 0,
                queuedAt: new Date().toISOString()
              };
              await dbService.save("sync_queue", queueItem);
              dbQueue.push(queueItem);
            }
          }
        }
      };

      await mapToQueue(animals, "animals", "Animal Registration");
      await mapToQueue(herds, "herds", "Herd Registration");
      await mapToQueue(vetCases, "vet_cases", "Veterinary Case");
      await mapToQueue(labSamples, "lab_samples", "Lab Diagnostic Sample");
      await mapToQueue(vaccinations, "vaccinations", "Vaccination Record");
      await mapToQueue(voiceReports, "voice_reports", "Voice Field Report");
    } catch (e) {
      console.warn("Error scanning domain stores for sync items:", e);
    }

    setSyncQueue([...dbQueue]);
  }, []);

  // Enqueue a new offline item safely
  const enqueueOfflineItem = useCallback(
    async (
      store: string,
      id: string,
      type: string,
      data: any,
      operation: "CREATE" | "UPDATE" | "DELETE" = "CREATE"
    ) => {
      await dbService.init();
      const localId = `SQ-${store}-${id}-${Date.now()}`;
      const idempotencyKey = `idemp-${store}-${id}-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;

      const queueItem: SyncQueueItem = {
        localId,
        idempotencyKey,
        store,
        id,
        type,
        operation,
        data: { ...data, syncStatus: "Pending", clientRecordId: localId },
        status: "Pending",
        attempts: 0,
        queuedAt: new Date().toISOString()
      };

      await dbService.save("sync_queue", queueItem);
      // Also update the store item itself if applicable
      if (store !== "reports") {
        await dbService.save(store, queueItem.data);
      }

      setSyncQueue((prev) => [queueItem, ...prev]);

      // Emit an internal activity event for offline queueing
      addActivityEvent({
        type: store === "reports" ? "DISEASE_REPORT" : store === "vaccinations" ? "VACCINATION" : "SYSTEM_SYNC",
        title: `Queued Offline: ${type}`,
        description: `Saved locally. Will sync automatically when connection is restored.`,
        timestamp: new Date().toISOString(),
        severity: "info",
        source: "Offline Sync Queue",
        entityId: id,
        entityType: store,
        targetRoute: store === "reports" ? "/reporting" : store === "vaccinations" ? "/vaccination" : "/offline"
      });
    },
    []
  );

  // Load and compile real Activity Events from actual data sources
  const loadActivityEvents = useCallback(async () => {
    await dbService.init();

    const compiled: ActivityEvent[] = [];

    // 1. Fetch real alerts from IndexedDB
    try {
      const alerts = await dbService.getAll("alerts");
      alerts.forEach((a) => {
        compiled.push({
          id: `act-alert-${a.id}`,
          type: a.type === "OUTBREAK" ? "OUTBREAK" : "AI_ALERT",
          title: `${a.type === "OUTBREAK" ? "🚨 Outbreak Alert" : "🤖 AI Risk Alert"}: ${a.disease}`,
          description: `${a.priority} priority alert in ${a.village ? `${a.village}, ` : ""}${a.district} district (${a.affectedAnimals || 0} affected).`,
          timestamp: a.detectedAt || new Date().toISOString(),
          severity:
            a.priority === "CRITICAL"
              ? "critical"
              : a.priority === "HIGH"
              ? "high"
              : a.priority === "MEDIUM"
              ? "warning"
              : "info",
          source: a.source || "Surveillance Engine",
          entityId: a.id,
          entityType: "alert",
          targetRoute: "/alerts"
        });
      });
    } catch (e) {
      console.warn("Could not load alerts for feed:", e);
    }

    // 2. Fetch real veterinary cases from IndexedDB
    try {
      const vetCases = await dbService.getAll("vet_cases");
      vetCases.forEach((c) => {
        compiled.push({
          id: `act-case-${c.id}`,
          type: "VET_CASE",
          title: `👨‍⚕️ Veterinary Case: #${c.caseNumber || c.id}`,
          description: `Case for ${c.species} in ${c.location} status is '${c.status}'. ${c.assignedVet ? `Assigned to ${c.assignedVet}.` : "Pending assignment."}`,
          timestamp: c.reportedAt || new Date().toISOString(),
          severity: c.priority === "CRITICAL" ? "critical" : c.priority === "HIGH" ? "high" : "info",
          source: "Veterinary Network",
          entityId: c.id,
          entityType: "vet_case",
          targetRoute: "/vet-response"
        });
      });
    } catch (e) {
      console.warn("Could not load vet cases for feed:", e);
    }

    // 3. Fetch real lab samples from IndexedDB
    try {
      const labSamples = await dbService.getAll("lab_samples");
      labSamples.forEach((s) => {
        compiled.push({
          id: `act-lab-${s.id}`,
          type: "LAB_RESULT",
          title: `🧪 Lab Sample: ${s.id}`,
          description: `${s.sampleType} for ${s.species} (${s.diseaseSuspected}) is currently '${s.status}'.`,
          timestamp: s.collectionDate || new Date().toISOString(),
          severity: s.priority === "Critical" ? "critical" : s.priority === "Urgent" ? "warning" : "info",
          source: "Disease Diagnostic Lab",
          entityId: s.id,
          entityType: "lab_sample",
          targetRoute: "/lab"
        });
      });
    } catch (e) {
      console.warn("Could not load lab samples for feed:", e);
    }

    // 4. Fetch real vaccinations from IndexedDB
    try {
      const vaccinations = await dbService.getAll("vaccinations");
      vaccinations.forEach((v) => {
        compiled.push({
          id: `act-vax-${v.id}`,
          type: "VACCINATION",
          title: `💉 Vaccination: ${v.vaccine || v.disease}`,
          description: `Vaccination record for ${v.species} in ${v.location || v.district} (Batch #${v.batchNumber}).`,
          timestamp: v.vaccinationDate || new Date().toISOString(),
          severity: "success",
          source: "NADCP Registry",
          entityId: v.id,
          entityType: "vaccination",
          targetRoute: "/vaccination"
        });
      });
    } catch (e) {
      console.warn("Could not load vaccinations for feed:", e);
    }

    // 5. If backend is reachable, fetch latest server disease reports
    try {
      const res = await fetch("/api/v1/reports");
      if (res.ok) {
        const reports = await res.json();
        if (Array.isArray(reports)) {
          reports.slice(0, 15).forEach((r: any) => {
            compiled.push({
              id: `act-rep-${r.id}`,
              type: "DISEASE_REPORT",
              title: `🚨 Disease Report: ${r.disease || r.suspected_disease || "Suspected Signs"}`,
              description: `Report #${r.reportNumber || r.id} submitted from ${r.village}, ${r.district} (${r.numberAffected || 1} ${r.species} affected).`,
              timestamp: r.date ? new Date(r.date).toISOString() : new Date().toISOString(),
              severity: Number(r.numberDead) > 0 ? "critical" : "warning",
              source: "Field Surveillance",
              entityId: r.id,
              entityType: "disease_report",
              targetRoute: "/surveillance"
            });
          });
        }
      }
    } catch {
      // offline fallback
    }

    // Sort by timestamp descending (newest first)
    compiled.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());

    // Deduplicate by ID
    const uniqueMap = new Map<string, ActivityEvent>();
    compiled.forEach((c) => {
      if (!uniqueMap.has(c.id)) {
        uniqueMap.set(c.id, c);
      }
    });

    setActivityEvents(Array.from(uniqueMap.values()).slice(0, 50));
  }, []);

  const addActivityEvent = useCallback((event: Omit<ActivityEvent, "id">) => {
    const newEvent: ActivityEvent = {
      ...event,
      id: `act-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`
    };
    setActivityEvents((prev) => [newEvent, ...prev]);
  }, []);

  // SMART SYNCHRONIZATION: Local Queue -> Check Network -> Authenticate -> Push -> Mark Synced / Retry Backoff / Conflict
  const syncNow = useCallback(async () => {
    if (!navigator.onLine) {
      setIsOnline(false);
      return;
    }

    const reachable = await checkServerReachability();
    if (!reachable) {
      return;
    }

    await dbService.init();
    const currentQueue: SyncQueueItem[] = await dbService.getAll<SyncQueueItem>("sync_queue");
    const pendingItems = currentQueue.filter(
      (item) => item.status === "Pending" || item.status === "Failed"
    );

    if (pendingItems.length === 0) {
      return;
    }

    setIsSyncing(true);

    // Build payload for backend sync endpoint
    const pushItems = pendingItems.map((item) => ({
      idempotency_key: item.idempotencyKey,
      store: item.store,
      id: item.id,
      operation: item.operation || "CREATE",
      data: item.data
    }));

    try {
      const authToken = token || localStorage.getItem("auth_token");
      const headers: Record<string, string> = {
        "Content-Type": "application/json"
      };
      if (authToken) headers["Authorization"] = `Bearer ${authToken}`;

      const res = await fetch("/api/v1/sync/push", {
        method: "POST",
        headers,
        body: JSON.stringify({ items: pushItems })
      });

      if (res.ok) {
        const responseData = await res.json();
        const processedList: any[] = responseData.processed || [];

        for (const item of pendingItems) {
          const processed = processedList.find((p) => p.localId === item.id || p.idempotencyKey === item.idempotencyKey);
          
          if (processed?.status === "SYNCED" || processed?.status === "ALREADY_SYNCED") {
            item.status = "Synced";
            item.lastAttemptAt = new Date().toISOString();
            await dbService.save("sync_queue", item);

            // Also mark corresponding store item as Synced
            if (item.store && item.data) {
              const updatedRecord = { ...item.data, syncStatus: "Synced" };
              await dbService.save(item.store, updatedRecord).catch(() => {});
            }
          } else if (processed?.status === "CONFLICT") {
            item.status = "Conflict";
            item.lastError = processed.message || "Server detected data conflict.";
            item.lastAttemptAt = new Date().toISOString();
            await dbService.save("sync_queue", item);
          } else if (processed?.status === "ERROR") {
            item.attempts += 1;
            item.status = "Failed";
            item.lastError = processed.error || "Server error";
            item.lastAttemptAt = new Date().toISOString();
            await dbService.save("sync_queue", item);
          } else {
            // General success fallback if processed item list was not detailed
            item.status = "Synced";
            item.lastAttemptAt = new Date().toISOString();
            await dbService.save("sync_queue", item);
            if (item.store && item.data) {
              const updatedRecord = { ...item.data, syncStatus: "Synced" };
              await dbService.save(item.store, updatedRecord).catch(() => {});
            }
          }
        }

        // Add synchronization completed event to activity feed
        addActivityEvent({
          type: "SYSTEM_SYNC",
          title: "⚙️ Data Synchronization Completed",
          description: `Successfully synchronized ${pendingItems.length} record(s) to central surveillance server.`,
          timestamp: new Date().toISOString(),
          severity: "success",
          source: "Offline Sync Manager",
          targetRoute: "/offline"
        });
      } else {
        // HTTP Error from server (e.g. 500 or 401)
        for (const item of pendingItems) {
          item.attempts += 1;
          item.status = "Failed";
          item.lastError = `Server responded with ${res.status}`;
          item.lastAttemptAt = new Date().toISOString();
          await dbService.save("sync_queue", item);
        }
      }
    } catch (err: any) {
      // Network/Fetch failed
      for (const item of pendingItems) {
        item.attempts += 1;
        item.status = "Failed";
        item.lastError = err?.message || "Network request failed";
        item.lastAttemptAt = new Date().toISOString();
        await dbService.save("sync_queue", item);
      }
    } finally {
      setIsSyncing(false);
      const now = new Date();
      setLastSyncTime(now);
      localStorage.setItem("pashu_last_sync_time", now.toISOString());
      await loadSyncQueue();
      await loadActivityEvents();
    }
  }, [token, checkServerReachability, addActivityEvent, loadSyncQueue, loadActivityEvents]);

  // Retry a single failed item
  const retryFailedItem = useCallback(
    async (localId: string) => {
      await dbService.init();
      const item = syncQueue.find((q) => q.localId === localId);
      if (item) {
        item.status = "Pending";
        await dbService.save("sync_queue", item);
        setSyncQueue((prev) => prev.map((q) => (q.localId === localId ? { ...q, status: "Pending" } : q)));
        await syncNow();
      }
    },
    [syncQueue, syncNow]
  );

  // Clear synced history from queue
  const clearSyncedHistory = useCallback(async () => {
    await dbService.init();
    const syncedItems = syncQueue.filter((q) => q.status === "Synced");
    for (const item of syncedItems) {
      await dbService.delete("sync_queue", item.localId);
    }
    setSyncQueue((prev) => prev.filter((q) => q.status !== "Synced"));
  }, [syncQueue]);

  // Network and real-time listeners setup
  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true);
      checkServerReachability().then((reachable) => {
        if (reachable) {
          syncNow();
        }
      });
    };

    const handleOffline = () => {
      setIsOnline(false);
      setServerReachable(false);
    };

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    // Initial load
    checkServerReachability();
    loadSyncQueue();
    loadActivityEvents();

    // Listen to real-time events from WebSocket
    const handleRealtime = (e: any) => {
      const ev = e.detail;
      if (!ev) return;

      if (ev.type === "SYNC_COMPLETED") {
        loadSyncQueue();
        loadActivityEvents();
      } else if (ev.type === "REPORT_CREATED") {
        addActivityEvent({
          type: "DISEASE_REPORT",
          title: `🚨 New Disease Report: ${ev.data?.disease || "Livestock Case"}`,
          description: `Submitted for ${ev.data?.village || "field"}, ${ev.data?.district || "Maharashtra"}.`,
          timestamp: new Date().toISOString(),
          severity: "warning",
          source: "Field Surveillance",
          targetRoute: "/surveillance"
        });
      } else if (ev.type === "CASE_CREATED" || ev.type === "CASE_STATUS_CHANGED") {
        addActivityEvent({
          type: "VET_CASE",
          title: `👨‍⚕️ Veterinary Case Updated`,
          description: `Veterinary assignment updated for case #${ev.data?.caseNumber || "Case"}.`,
          timestamp: new Date().toISOString(),
          severity: "info",
          source: "Veterinary Dispatch",
          targetRoute: "/vet-response"
        });
      } else if (ev.type === "LAB_RESULT_VERIFIED" || ev.type === "LAB_SAMPLE_COLLECTED") {
        addActivityEvent({
          type: "LAB_RESULT",
          title: `🧪 Lab Result Available`,
          description: `Sample ${ev.data?.id || ""} diagnostic tests updated.`,
          timestamp: new Date().toISOString(),
          severity: "success",
          source: "Diagnostic Lab",
          targetRoute: "/lab"
        });
      }
    };

    window.addEventListener("pashu_realtime_event", handleRealtime);

    // Periodic background sync & refresh interval (fallback when WS is not connected)
    const interval = setInterval(() => {
      if (document.visibilityState === "visible") {
        if (navigator.onLine) {
          checkServerReachability().then((reachable) => {
            if (reachable) {
              loadSyncQueue();
            }
          });
        }
      }
    }, 15000);

    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
      window.removeEventListener("pashu_realtime_event", handleRealtime);
      clearInterval(interval);
    };
  }, [checkServerReachability, loadSyncQueue, loadActivityEvents, syncNow, addActivityEvent]);

  const pendingCount = useMemo(
    () => syncQueue.filter((item) => item.status === "Pending" || item.status === "Syncing").length,
    [syncQueue]
  );

  const failedCount = useMemo(
    () => syncQueue.filter((item) => item.status === "Failed" || item.status === "Conflict").length,
    [syncQueue]
  );

  return (
    <SyncContext.Provider
      value={{
        isOnline,
        serverReachable,
        networkStatus,
        syncQueue,
        pendingCount,
        failedCount,
        isSyncing,
        lastSyncTime,
        syncNow,
        enqueueOfflineItem,
        retryFailedItem,
        clearSyncedHistory,
        activityEvents,
        feedStatus,
        addActivityEvent,
        refreshActivityFeed: loadActivityEvents,
        isSyncModalOpen,
        openSyncModal: () => setIsSyncModalOpen(true),
        closeSyncModal: () => setIsSyncModalOpen(false)
      }}
    >
      {children}
    </SyncContext.Provider>
  );
}

export function useSync() {
  const context = useContext(SyncContext);
  if (context === undefined) {
    throw new Error("useSync must be used within a SyncProvider");
  }
  return context;
}
