import { useState } from "react";
import { useAlerts } from "../../context/AlertsContext";
import type { SystemAlert } from "../../context/AlertsContext";
import { Search, ChevronRight, X } from "lucide-react";
import AlertDetailModal from "./AlertDetailModal";

export default function AlertList() {
  const { alerts } = useAlerts();
  const [search, setSearch] = useState("");
  const [filterPriority, setFilterPriority] = useState<string>("ALL");
  const [filterStatus, setFilterStatus] = useState<string>("ACTIVE");
  const [selectedAlert, setSelectedAlert] = useState<SystemAlert | null>(null);

  const filtered = alerts.filter(a => {
    // Search
    const matchesSearch = 
      a.id.toLowerCase().includes(search.toLowerCase()) || 
      a.disease.toLowerCase().includes(search.toLowerCase()) ||
      a.district.toLowerCase().includes(search.toLowerCase()) ||
      a.village.toLowerCase().includes(search.toLowerCase());
    
    if (!matchesSearch) return false;

    // Filters
    if (filterPriority !== "ALL" && a.priority !== filterPriority) return false;
    
    if (filterStatus === "UNREAD" && a.read) return false;
    if (filterStatus === "ACTIVE" && a.status === "RESOLVED") return false;
    if (filterStatus === "RESOLVED" && a.status !== "RESOLVED") return false;

    return true;
  });

  const clearFilters = () => {
    setSearch("");
    setFilterPriority("ALL");
    setFilterStatus("ALL");
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 flex flex-col flex-1 overflow-hidden">
      
      {/* Toolbar */}
      <div className="p-4 border-b border-gray-200 flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-gray-50">
        <div className="relative w-full md:w-96">
          <Search className="absolute left-3 top-2.5 text-gray-400" size={20} />
          <input 
            type="text" 
            placeholder="Search disease, location, ID..." 
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-brandBlue focus:border-brandBlue text-sm"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        
        <div className="flex flex-wrap gap-2">
          <select 
            value={filterPriority} 
            onChange={(e) => setFilterPriority(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white focus:ring-brandBlue"
          >
            <option value="ALL">All Priorities</option>
            <option value="CRITICAL">Critical</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
          </select>

          <select 
            value={filterStatus} 
            onChange={(e) => setFilterStatus(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white focus:ring-brandBlue"
          >
            <option value="ALL">All Statuses</option>
            <option value="ACTIVE">Active (Unresolved)</option>
            <option value="UNREAD">Unread</option>
            <option value="RESOLVED">Resolved</option>
          </select>

          {(search || filterPriority !== "ALL" || filterStatus !== "ACTIVE") && (
            <button onClick={clearFilters} className="px-3 py-2 text-red-600 hover:bg-red-50 rounded-lg text-sm font-medium flex items-center gap-1">
              <X size={16} /> Clear Filters
            </button>
          )}
        </div>
      </div>

      {/* Table for Desktop, Cards for Mobile handled via responsive table classes in a real app, 
          here using an overflow-x-auto table */}
      <div className="overflow-x-auto flex-1 custom-scrollbar">
        <table className="w-full text-left border-collapse min-w-[720px]">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200 text-xs font-medium text-gray-500 uppercase tracking-wider">
              <th className="px-4 py-3">Priority</th>
              <th className="px-4 py-3">Disease & Type</th>
              <th className="px-4 py-3">Location</th>
              <th className="px-4 py-3 text-right">Risk Score</th>
              <th className="px-4 py-3 text-right">Affected</th>
              <th className="px-4 py-3">Detection Time</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {filtered.map((a) => (
              <tr 
                key={a.id} 
                onClick={() => setSelectedAlert(a)}
                className={`hover:bg-gray-50 transition-colors cursor-pointer ${!a.read ? "bg-blue-50/30" : ""}`}
              >
                <td className="px-4 py-3 whitespace-nowrap">
                  <span className={`px-2 py-1 inline-flex text-xs leading-5 font-bold rounded-full 
                    ${a.priority === "CRITICAL" ? "bg-red-100 text-red-800 border border-red-200" : 
                      a.priority === "HIGH" ? "bg-orange-100 text-orange-800 border border-orange-200" : 
                      a.priority === "MEDIUM" ? "bg-yellow-100 text-yellow-800" : 
                      "bg-blue-100 text-blue-800"}`}>
                    {a.priority}
                  </span>
                  {!a.read && <span className="ml-2 w-2 h-2 bg-brandBlue rounded-full inline-block"></span>}
                </td>
                <td className="px-4 py-3">
                  <p className={`font-bold ${!a.read ? "text-gray-900" : "text-gray-700"}`}>{a.disease}</p>
                  <p className="text-xs text-gray-500">{a.type} • {a.id}</p>
                </td>
                <td className="px-4 py-3 whitespace-nowrap">
                  <p className="text-sm font-medium text-gray-800">{a.village}</p>
                  <p className="text-xs text-gray-500">{a.district}</p>
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-right">
                  <span className={`font-mono font-bold ${a.riskScore >= 80 ? "text-red-600" : a.riskScore >= 60 ? "text-orange-500" : "text-gray-900"}`}>
                    {a.riskScore}/100
                  </span>
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-right">
                  <p className="text-sm font-bold text-gray-900">{a.affectedAnimals}</p>
                  <p className="text-xs text-gray-500">{a.suspectedCases} Suspected</p>
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                  {new Date(a.detectedAt).toLocaleString()}
                </td>
                <td className="px-4 py-3 whitespace-nowrap">
                   <span className="text-xs font-bold text-gray-700">{a.status}</span>
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-right text-sm font-medium">
                  <button className="text-brandBlue hover:text-blue-900 flex items-center gap-1 justify-end w-full">
                    View <ChevronRight size={16} />
                  </button>
                </td>
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={8} className="px-6 py-12 text-center text-gray-500">
                  No alerts found matching the current filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {selectedAlert && (
        <AlertDetailModal 
          alert={selectedAlert} 
          onClose={() => setSelectedAlert(null)} 
        />
      )}
    </div>
  );
}

