import { 
  X, RefreshCw, CheckCircle2, AlertTriangle, 
  Clock, Database, ArrowRight, ShieldAlert, Wifi, WifiOff 
} from "lucide-react";
import { useSync } from "../services/SyncService";
import { useNavigate } from "react-router-dom";

export default function SyncModal() {
  const { 
    isSyncModalOpen, 
    closeSyncModal, 
    syncQueue, 
    pendingCount, 
    failedCount, 
    isSyncing, 
    syncNow, 
    retryFailedItem, 
    clearSyncedHistory,
    isOnline,
    serverReachable,
    lastSyncTime 
  } = useSync();

  const navigate = useNavigate();

  if (!isSyncModalOpen) return null;

  const syncedCount = syncQueue.filter(i => i.status === "Synced").length;

  return (
    <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
      <div 
        className="bg-white rounded-2xl shadow-2xl border border-gray-200 w-full max-w-lg overflow-hidden flex flex-col max-h-[85vh] animate-in fade-in zoom-in-95 duration-150"
        role="dialog"
        aria-modal="true"
        aria-labelledby="sync-modal-title"
      >
        {/* Header */}
        <div className="p-4 bg-gray-50 border-b border-gray-200 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-blue-100 text-blue-700">
              <Database size={18} />
            </div>
            <div>
              <h3 id="sync-modal-title" className="font-bold text-gray-900 text-sm">
                Synchronization Manager
              </h3>
              <p className="text-xs text-gray-500">
                IndexedDB Local Storage & Smart Sync
              </p>
            </div>
          </div>
          <button
            onClick={closeSyncModal}
            className="p-1.5 rounded-lg text-gray-400 hover:text-gray-700 hover:bg-gray-200 transition-colors"
            aria-label="Close"
          >
            <X size={18} />
          </button>
        </div>

        {/* Network & Connectivity Status Banner */}
        <div className="px-4 py-2.5 bg-gray-100 border-b border-gray-200 flex items-center justify-between text-xs">
          <div className="flex items-center gap-2">
            {!isOnline ? (
              <span className="flex items-center gap-1.5 text-red-700 font-bold">
                <WifiOff size={14} /> Offline Mode
              </span>
            ) : !serverReachable ? (
              <span className="flex items-center gap-1.5 text-amber-700 font-bold">
                <Wifi size={14} /> Device Online (Server Offline)
              </span>
            ) : (
              <span className="flex items-center gap-1.5 text-emerald-700 font-bold">
                <Wifi size={14} /> Connected to Central Server
              </span>
            )}
          </div>

          <div className="text-xs text-gray-500 font-mono">
            {lastSyncTime ? `Last: ${lastSyncTime.toLocaleTimeString()}` : "Not synced"}
          </div>
        </div>

        {/* Sync Summary Counters */}
        <div className="grid grid-cols-3 gap-2 p-3 bg-white border-b border-gray-100 text-center text-xs">
          <div className="p-2 bg-emerald-50 rounded-xl border border-emerald-100">
            <p className="text-emerald-700 font-bold text-base flex items-center justify-center gap-1">
              <CheckCircle2 size={16} /> {syncedCount}
            </p>
            <p className="text-emerald-700 text-xs font-medium mt-0.5">Records Synced</p>
          </div>

          <div className="p-2 bg-blue-50 rounded-xl border border-blue-100">
            <p className="text-blue-700 font-bold text-base flex items-center justify-center gap-1">
              <Clock size={16} /> {pendingCount}
            </p>
            <p className="text-blue-700 text-xs font-medium mt-0.5">Pending Sync</p>
          </div>

          <div className="p-2 bg-red-50 rounded-xl border border-red-100">
            <p className="text-red-700 font-bold text-base flex items-center justify-center gap-1">
              <AlertTriangle size={16} /> {failedCount}
            </p>
            <p className="text-red-700 text-xs font-medium mt-0.5">Needs Attention</p>
          </div>
        </div>

        {/* Queue Items List */}
        <div className="flex-1 overflow-y-auto p-3 space-y-2.5">
          {syncQueue.length === 0 ? (
            <div className="py-12 text-center text-gray-400">
              <CheckCircle2 size={36} className="mx-auto text-emerald-700 mb-2" />
              <p className="text-sm font-semibold text-gray-700">All local records are synchronized</p>
              <p className="text-xs text-gray-400 mt-0.5">No offline transactions queued in IndexedDB</p>
            </div>
          ) : (
            syncQueue.map((item) => (
              <div 
                key={item.localId}
                className="p-3 rounded-xl border border-gray-200 bg-white shadow-2xs hover:border-gray-300 transition-colors flex flex-col gap-1.5"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="text-xs font-bold text-gray-900 truncate">
                      {item.type}
                    </p>
                    <p className="text-xs text-gray-500 font-mono truncate">
                      ID: {item.id} • Store: {item.store}
                    </p>
                  </div>

                  <span
                    className={`shrink-0 px-2 py-0.5 rounded-full text-xs font-bold border flex items-center gap-1 ${
                      item.status === "Synced"
                        ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                        : item.status === "Syncing"
                        ? "bg-blue-50 text-blue-700 border-blue-200 animate-pulse"
                        : item.status === "Failed"
                        ? "bg-red-50 text-red-700 border-red-200"
                        : item.status === "Conflict"
                        ? "bg-amber-50 text-amber-700 border-amber-200"
                        : "bg-gray-100 text-gray-700 border-gray-200"
                    }`}
                  >
                    {item.status === "Syncing" && <RefreshCw size={10} className="animate-spin" />}
                    {item.status === "Synced" && <CheckCircle2 size={10} />}
                    {item.status === "Failed" && <AlertTriangle size={10} />}
                    {item.status === "Conflict" && <ShieldAlert size={10} />}
                    <span>{item.status}</span>
                  </span>
                </div>

                {item.lastError && (
                  <div className="text-xs text-red-700 bg-red-50 p-2 rounded-lg border border-red-100 flex items-center justify-between gap-2">
                    <span className="truncate">Reason: {item.lastError}</span>
                    <button
                      onClick={() => retryFailedItem(item.localId)}
                      className="px-2 py-0.5 bg-red-600 hover:bg-red-700 text-white rounded-lg font-bold text-xs shrink-0"
                    >
                      Retry
                    </button>
                  </div>
                )}
              </div>
            ))
          )}
        </div>

        {/* Footer Actions */}
        <div className="p-3 bg-gray-50 border-t border-gray-200 flex items-center justify-between gap-2">
          {syncedCount > 0 ? (
            <button
              onClick={clearSyncedHistory}
              className="text-xs text-gray-500 hover:text-gray-700 font-medium px-2 py-1"
            >
              Clear Synced
            </button>
          ) : (
            <button
              onClick={() => {
                closeSyncModal();
                navigate("/offline");
              }}
              className="link-action"
            >
              <span>Full Manager</span>
              <ArrowRight size={12} />
            </button>
          )}

          <div className="flex items-center gap-2">
            <button
              onClick={closeSyncModal}
              className="btn btn-ghost"
            >
              Close
            </button>
            <button
              onClick={syncNow}
              disabled={isSyncing || pendingCount === 0 || !isOnline}
              className="btn btn-primary shadow-2xs"
            >
              <RefreshCw size={13} className={isSyncing ? "animate-spin" : ""} />
              <span>{isSyncing ? "Syncing..." : `Sync (${pendingCount})`}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
