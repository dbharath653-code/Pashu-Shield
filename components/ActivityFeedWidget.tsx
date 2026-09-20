import { useState } from "react";
import { 
  BellRing, RefreshCw, AlertTriangle, 
  Activity, ArrowRight, Filter
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useSync, type ActivityEvent } from "../services/SyncService";

// Human-readable relative timestamp helper
export function formatRelativeTime(isoString: string): string {
  try {
    const date = new Date(isoString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    if (isNaN(diffMs)) return "Recent";

    const diffSec = Math.floor(diffMs / 1000);
    if (diffSec < 45) return "Just now";
    const diffMin = Math.floor(diffSec / 60);
    if (diffMin < 60) return `${diffMin} min ago`;
    const diffHours = Math.floor(diffMin / 60);
    if (diffHours < 24) return diffHours === 1 ? "1 hour ago" : `${diffHours} hours ago`;
    const diffDays = Math.floor(diffHours / 24);
    if (diffDays === 1) return "Yesterday";
    if (diffDays < 7) return `${diffDays} days ago`;
    return date.toLocaleDateString();
  } catch {
    return "Recent";
  }
}

export default function ActivityFeedWidget({ 
  maxItems = 8, 
  showHeader = true,
  className = "" 
}: { 
  maxItems?: number; 
  showHeader?: boolean;
  className?: string;
}) {
  const navigate = useNavigate();
  const { activityEvents, feedStatus, refreshActivityFeed } = useSync();
  const [filterType, setFilterType] = useState<string>("ALL");
  const [isRefreshing, setIsRefreshing] = useState(false);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    await refreshActivityFeed();
    setTimeout(() => setIsRefreshing(false), 500);
  };

  const filteredEvents = activityEvents.filter((ev) => {
    if (filterType === "ALL") return true;
    if (filterType === "REPORTS") return ev.type === "DISEASE_REPORT";
    if (filterType === "ALERTS") return ev.type === "AI_ALERT" || ev.type === "OUTBREAK";
    if (filterType === "CLINICAL") return ev.type === "VET_CASE" || ev.type === "LAB_RESULT";
    if (filterType === "VAX") return ev.type === "VACCINATION";
    return true;
  });

  const displayList = filteredEvents.slice(0, maxItems);

  const getSeverityBadge = (severity: ActivityEvent["severity"]) => {
    switch (severity) {
      case "critical":
        return {
          badgeClass: "bg-red-100 text-red-800 border-red-200",
          dotClass: "bg-red-500",
          label: "CRITICAL"
        };
      case "high":
        return {
          badgeClass: "bg-orange-100 text-orange-800 border-orange-200",
          dotClass: "bg-orange-500",
          label: "HIGH"
        };
      case "warning":
        return {
          badgeClass: "bg-amber-100 text-amber-800 border-amber-200",
          dotClass: "bg-amber-500",
          label: "WARNING"
        };
      case "success":
        return {
          badgeClass: "bg-emerald-100 text-emerald-800 border-emerald-200",
          dotClass: "bg-emerald-500",
          label: "SUCCESS"
        };
      case "info":
      default:
        return {
          badgeClass: "bg-blue-100 text-blue-800 border-blue-200",
          dotClass: "bg-blue-500",
          label: "INFO"
        };
    }
  };

  const handleItemClick = (event: ActivityEvent) => {
    if (event.targetRoute) {
      navigate(event.targetRoute);
    } else {
      switch (event.type) {
        case "DISEASE_REPORT":
          navigate("/reporting");
          break;
        case "VET_CASE":
          navigate("/vet-response");
          break;
        case "LAB_RESULT":
          navigate("/lab");
          break;
        case "VACCINATION":
          navigate("/vaccination");
          break;
        case "AI_ALERT":
        case "OUTBREAK":
          navigate("/alerts");
          break;
        default:
          navigate("/surveillance");
      }
    }
  };

  return (
    <div className={`bg-white rounded-2xl border border-gray-200 shadow-sm flex flex-col overflow-hidden ${className}`}>
      {/* Header */}
      {showHeader && (
        <div className="p-4 border-b border-gray-100 flex flex-wrap items-center justify-between gap-2 bg-gray-50/50">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-blue-100 text-brandBlue">
              <BellRing size={18} />
            </div>
            <div>
              <h3 className="font-bold text-gray-900 text-sm flex items-center gap-2">
                <span>Real-Time Activity & Alert Feed</span>
                {/* Live / Updating / Offline pill */}
                <span
                  className={`px-2 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider flex items-center gap-1 border ${
                    feedStatus === "LIVE"
                      ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                      : feedStatus === "UPDATING"
                      ? "bg-amber-50 text-amber-700 border-amber-200"
                      : "bg-gray-100 text-gray-600 border-gray-200"
                  }`}
                >
                  <span
                    className={`w-1.5 h-1.5 rounded-full ${
                      feedStatus === "LIVE"
                        ? "bg-emerald-500 animate-pulse"
                        : feedStatus === "UPDATING"
                        ? "bg-amber-500 animate-ping"
                        : "bg-gray-400"
                    }`}
                  />
                  <span>{feedStatus}</span>
                </span>
              </h3>
              <p className="text-[11px] text-gray-500">Live operational & early-warning updates</p>
            </div>
          </div>

          <div className="flex items-center gap-1.5">
            <button
              onClick={handleRefresh}
              className="p-1.5 text-gray-500 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors"
              title="Refresh Activity"
            >
              <RefreshCw size={14} className={isRefreshing ? "animate-spin" : ""} />
            </button>
            <button
              onClick={() => navigate("/alerts")}
              className="text-xs font-semibold text-brandBlue hover:underline flex items-center gap-1 px-1 py-1"
            >
              <span>All Alerts</span>
              <ArrowRight size={13} />
            </button>
          </div>
        </div>
      )}

      {/* Filter Tabs */}
      <div className="px-4 py-2 border-b border-gray-100 flex items-center gap-1.5 overflow-x-auto custom-scrollbar bg-white text-xs">
        <Filter size={12} className="text-gray-400 shrink-0" />
        {[
          { id: "ALL", label: "All Events" },
          { id: "REPORTS", label: "Disease Reports" },
          { id: "ALERTS", label: "Alerts & AI" },
          { id: "CLINICAL", label: "Vet & Lab" },
          { id: "VAX", label: "Vaccinations" }
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setFilterType(tab.id)}
            className={`px-2.5 py-1 rounded-lg font-medium whitespace-nowrap transition-colors text-xs ${
              filterType === tab.id
                ? "bg-blue-100 text-brandBlue font-bold"
                : "text-gray-600 hover:bg-gray-100"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Activity List */}
      <div className="flex-1 overflow-y-auto divide-y divide-gray-100">
        {displayList.length === 0 ? (
          <div className="p-8 text-center text-gray-400">
            <Activity size={32} className="mx-auto text-gray-300 mb-2" />
            <p className="text-xs font-medium text-gray-600">No recent activity events.</p>
            <p className="text-[11px] text-gray-400 mt-0.5">Events from reports, vet cases, and labs will stream here.</p>
          </div>
        ) : (
          displayList.map((event) => {
            const badge = getSeverityBadge(event.severity);
            return (
              <div
                key={event.id}
                onClick={() => handleItemClick(event)}
                className="p-3.5 hover:bg-blue-50/40 transition-colors cursor-pointer group flex items-start justify-between gap-3"
              >
                <div className="flex items-start gap-3 min-w-0 flex-1">
                  <span className={`w-2 h-2 rounded-full mt-1.5 shrink-0 ${badge.dotClass}`} />
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-1.5">
                      <p className="text-xs font-bold text-gray-900 group-hover:text-brandBlue transition-colors truncate">
                        {event.title}
                      </p>
                      <span className={`px-1.5 py-0.2 rounded text-[9px] font-bold border ${badge.badgeClass}`}>
                        {badge.label}
                      </span>
                    </div>

                    {event.description && (
                      <p className="text-[11px] text-gray-600 mt-0.5 line-clamp-2 leading-relaxed">
                        {event.description}
                      </p>
                    )}

                    <div className="flex items-center gap-2 mt-1.5 text-[10px] text-gray-400 font-medium">
                      {event.source && <span className="text-gray-500 font-semibold">{event.source}</span>}
                      {event.source && <span>•</span>}
                      {/* Responsive readable timestamp */}
                      <span title={event.timestamp}>
                        {formatRelativeTime(event.timestamp)}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="shrink-0 self-center opacity-0 group-hover:opacity-100 transition-opacity">
                  <ArrowRight size={14} className="text-brandBlue" />
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Footer info */}
      <div className="p-2.5 bg-gray-50 border-t border-gray-100 flex items-center justify-between text-[11px] text-gray-500 px-4">
        <span className="flex items-center gap-1">
          <AlertTriangle size={12} className="text-gray-400" />
          <span>Real data from Maharashtra surveillance stream</span>
        </span>
        <span className="font-mono text-[10px] text-gray-400">
          Showing {displayList.length} of {activityEvents.length}
        </span>
      </div>
    </div>
  );
}
