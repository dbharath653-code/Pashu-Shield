import { 
  Wifi, WifiOff, RefreshCw, CheckCircle, Database, AlertCircle, Clock, Trash2 
} from "lucide-react";
import { useSync } from "../../services/SyncService";

export default function OfflineSync() {
  const { 
    isOnline, 
    serverReachable, 
    syncQueue, 
    pendingCount, 
    isSyncing, 
    lastSyncTime, 
    syncNow, 
    retryFailedItem, 
    clearSyncedHistory 
  } = useSync();

  const handleSync = async () => {
    if (!isOnline) {
      alert("Cannot sync while offline. Please connect to the internet first.");
      return;
    }
    await syncNow();
  };

  const syncedCount = syncQueue.filter(item => item.status === "Synced").length;

  return (
    <div className="flex flex-col h-full bg-gray-50 p-2 sm:p-4 space-y-4 max-w-full overflow-hidden">
      {/* Top Banner Card */}
      <div className="bg-white p-4 sm:p-6 rounded-2xl shadow-xs border border-gray-200">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-xl sm:text-2xl font-black text-gray-900 tracking-tight">OFFLINE SYNC MANAGER</h1>
            <p className="text-gray-500 text-xs sm:text-sm mt-1">
              Monitor local IndexedDB storage, inspect queued offline transactions, and synchronize data with the central Maharashtra server.
            </p>
          </div>
          
          <div className="flex flex-wrap items-center gap-2 sm:gap-3">
             <div className={`flex items-center gap-2 px-3 sm:px-4 py-2 rounded-xl font-bold text-xs sm:text-sm border ${
               !isOnline 
                 ? "bg-red-50 text-red-700 border-red-200" 
                 : !serverReachable 
                 ? "bg-amber-50 text-amber-700 border-amber-200"
                 : "bg-green-50 text-green-700 border-green-200"
             }`}>
               {!isOnline ? <WifiOff size={16} /> : <Wifi size={16} />}
               <span>{!isOnline ? "Device Offline" : !serverReachable ? "Server Reachable: No" : "System Online"}</span>
             </div>
             
             <button 
               onClick={handleSync}
               disabled={isSyncing || pendingCount === 0 || !isOnline}
               className={`px-4 sm:px-5 py-2 rounded-xl font-bold text-xs sm:text-sm flex items-center gap-2 transition-colors touch-manipulation min-h-[40px] shadow-xs ${
                 isSyncing ? "bg-blue-100 text-blue-700 cursor-wait" : 
                 pendingCount === 0 ? "bg-gray-100 text-gray-400 cursor-not-allowed" : 
                 !isOnline ? "bg-gray-100 text-gray-400 cursor-not-allowed" :
                 "bg-brandBlue text-white hover:bg-blue-700"
               }`}
             >
               <RefreshCw size={16} className={isSyncing ? "animate-spin" : ""} />
               <span>{isSyncing ? "Synchronizing..." : `Sync Now (${pendingCount})`}</span>
             </button>
          </div>
        </div>
      </div>

      {/* KPI Cards: Responsive (1 col on mobile, 3 col on md+) */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 sm:gap-4">
        <div className="bg-white p-4 sm:p-5 rounded-2xl border border-gray-200 shadow-xs flex items-center justify-between">
          <div>
            <p className="text-xs sm:text-sm font-medium text-gray-500">Pending Uploads</p>
            <p className="text-2xl sm:text-3xl font-black text-orange-600 mt-0.5">{pendingCount}</p>
          </div>
          <div className="p-3 bg-orange-50 text-orange-600 rounded-2xl"><Database size={24} /></div>
        </div>
        
        <div className="bg-white p-4 sm:p-5 rounded-2xl border border-gray-200 shadow-xs flex items-center justify-between">
          <div>
            <p className="text-xs sm:text-sm font-medium text-gray-500">Last Successful Sync</p>
            <p className="text-lg sm:text-xl font-black text-gray-900 mt-0.5">
              {lastSyncTime ? lastSyncTime.toLocaleTimeString() : "Never"}
            </p>
          </div>
          <div className="p-3 bg-blue-50 text-brandBlue rounded-2xl"><Clock size={24} /></div>
        </div>
        
        <div className="bg-white p-4 sm:p-5 rounded-2xl border border-gray-200 shadow-xs flex items-center justify-between">
          <div>
            <p className="text-xs sm:text-sm font-medium text-gray-500">Local Database State</p>
            <p className="text-lg sm:text-xl font-black text-emerald-600 mt-0.5">IndexedDB Connected</p>
            <p className="text-[10px] text-gray-400">livestock_health_db (v6)</p>
          </div>
          <div className="p-3 bg-emerald-50 text-emerald-600 rounded-2xl"><CheckCircle size={24} /></div>
        </div>
      </div>

      {/* Queue Card */}
      <div className="flex-1 bg-white rounded-2xl shadow-xs border border-gray-200 overflow-hidden flex flex-col min-h-[350px]">
        <div className="p-4 border-b border-gray-200 bg-gray-50/50 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h2 className="font-bold text-gray-800 text-sm sm:text-base">Synchronization Queue</h2>
            <span className="text-xs text-gray-500 font-mono">({syncQueue.length} records)</span>
          </div>

          {syncedCount > 0 && (
            <button
              onClick={clearSyncedHistory}
              className="text-xs text-gray-500 hover:text-gray-800 flex items-center gap-1 font-semibold"
            >
              <Trash2 size={13} />
              <span>Clear Synced</span>
            </button>
          )}
        </div>
        
        <div className="overflow-y-auto flex-1 p-3 sm:p-4 custom-scrollbar">
          {syncQueue.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-gray-400 py-16 space-y-3">
              <CheckCircle size={44} className="text-emerald-400" />
              <p className="text-base font-bold text-gray-700">All data is synchronized!</p>
              <p className="text-xs text-gray-400">There are no pending offline records in the local IndexedDB queue.</p>
            </div>
          ) : (
            <div className="space-y-2.5">
              {syncQueue.map((item) => (
                <div 
                  key={item.localId} 
                  className="flex flex-col sm:flex-row sm:items-center justify-between p-3.5 border border-gray-200 rounded-xl bg-white shadow-2xs hover:shadow-xs transition-shadow gap-3"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div className={`p-2.5 rounded-xl shrink-0 ${
                      item.store === "animals" ? "bg-purple-100 text-purple-700" :
                      item.store === "herds" ? "bg-indigo-100 text-indigo-700" :
                      item.store === "reports" ? "bg-rose-100 text-rose-700" :
                      item.store === "vaccinations" ? "bg-emerald-100 text-emerald-700" :
                      "bg-blue-100 text-blue-700"
                    }`}>
                      <Database size={18} />
                    </div>
                    <div className="min-w-0">
                      <p className="font-bold text-gray-900 text-xs sm:text-sm truncate">{item.id}</p>
                      <p className="text-xs text-gray-500 truncate">{item.type} • Store: {item.store}</p>
                      {item.lastError && (
                        <p className="text-[11px] text-red-600 mt-0.5">Error: {item.lastError}</p>
                      )}
                    </div>
                  </div>
                  
                  <div className="flex items-center justify-between sm:justify-end gap-3 shrink-0">
                     <div className="text-[10px] text-gray-400 font-mono hidden md:block max-w-[200px] truncate">
                        Key: {item.idempotencyKey.substring(0, 22)}...
                     </div>

                     {item.status === "Failed" && (
                       <button
                         onClick={() => retryFailedItem(item.localId)}
                         className="px-2.5 py-1 text-xs font-bold text-white bg-red-600 hover:bg-red-700 rounded-lg shadow-2xs"
                       >
                         Retry
                       </button>
                     )}

                     <div className={`flex items-center gap-1 px-3 py-1 rounded-full text-xs font-bold border ${
                        item.status === "Pending" ? "bg-gray-100 text-gray-700 border-gray-200" :
                        item.status === "Syncing" ? "bg-blue-100 text-blue-700 border-blue-200 animate-pulse" :
                        item.status === "Synced" ? "bg-emerald-100 text-emerald-800 border-emerald-200" :
                        "bg-red-100 text-red-700 border-red-200"
                     }`}>
                        {item.status === "Pending" && <Clock size={12} />}
                        {item.status === "Syncing" && <RefreshCw size={12} className="animate-spin" />}
                        {item.status === "Synced" && <CheckCircle size={12} />}
                        {item.status === "Failed" && <AlertCircle size={12} />}
                        <span>{item.status}</span>
                     </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
