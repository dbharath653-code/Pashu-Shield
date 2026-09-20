import { useState, useEffect } from "react";
import { useAppContext } from "../context/AppContext";
import { Activity, RefreshCw } from "lucide-react";
import { DISTRICT_NAMES } from "../services/ReferenceData";

const tabs = ["Reported Cases", "Suspected Outbreaks", "Confirmed Outbreaks", "Mortality Reports"];

export default function DiseaseSurveillance() {
  const { reports: localReports } = useAppContext();
  const [activeTab, setActiveTab] = useState(tabs[0]);
  const [reports, setReports] = useState<any[]>(localReports);
  const [selectedSpecies, setSelectedSpecies] = useState("All");
  const [selectedDistrict, setSelectedDistrict] = useState("All");
  const [selectedDisease, setSelectedDisease] = useState("All");
  const [loading, setLoading] = useState(false);

  const loadReports = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/v1/reports");
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data) && data.length > 0) {
          setReports(data);
          return;
        }
      }
    } catch {
      // Fallback
    } finally {
      setLoading(false);
    }
    setReports(localReports);
  };

  useEffect(() => {
    loadReports();

    const handleRealtime = (e: any) => {
      const ev = e.detail;
      if (ev?.type === "REPORT_CREATED") {
        loadReports();
      }
    };
    window.addEventListener("pashu_realtime_event", handleRealtime);
    return () => window.removeEventListener("pashu_realtime_event", handleRealtime);
  }, []);

  // Filter logic based on tabs and dropdowns
  const filteredReports = reports.filter((r) => {
    if (activeTab === "Suspected Outbreaks" && r.status !== "Suspected") return false;
    if (activeTab === "Confirmed Outbreaks" && r.status !== "Confirmed" && r.status !== "Under Review") return false;
    if (activeTab === "Mortality Reports" && Number(r.numberDead) <= 0) return false;

    if (selectedSpecies !== "All" && r.species !== selectedSpecies) return false;
    if (selectedDistrict !== "All" && r.district !== selectedDistrict) return false;
    if (selectedDisease !== "All" && r.disease !== selectedDisease) return false;

    return true;
  });

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 flex flex-col h-full overflow-hidden">
      {/* Top Banner with Provenance */}
      <div className="p-4 bg-gray-50 border-b border-gray-200 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2">
            <Activity className="text-brandBlue" size={20} />
            <span>Statewide Disease Surveillance Feed</span>
          </h2>
          <p className="text-xs text-gray-500 mt-0.5">
            Real-time syndromic event stream with automated clinical triage verification
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="px-2.5 py-1 bg-emerald-100 text-emerald-800 rounded-full text-xs font-bold flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            LIVE FEED
          </span>
          <button
            onClick={loadReports}
            className="p-1.5 hover:bg-gray-200 text-gray-600 rounded-lg transition-colors"
            title="Refresh Feed"
          >
            <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-200 overflow-x-auto bg-white">
        {tabs.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-6 py-3.5 text-sm font-semibold whitespace-nowrap border-b-2 transition-colors ${
              activeTab === tab
                ? "border-brandBlue text-brandBlue"
                : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Filters */}
      <div className="p-4 border-b border-gray-100 flex flex-wrap gap-4 items-end bg-gray-50/40">
        <div className="space-y-1">
          <label className="text-xs font-medium text-gray-600">Species</label>
          <select
            value={selectedSpecies}
            onChange={(e) => setSelectedSpecies(e.target.value)}
            className="block w-36 rounded-lg border-gray-300 shadow-xs text-xs p-2 border bg-white focus:ring-brandBlue focus:border-brandBlue"
          >
            <option value="All">All Species</option>
            <option value="Cattle">Cattle</option>
            <option value="Buffalo">Buffalo</option>
            <option value="Goat">Goat</option>
            <option value="Sheep">Sheep</option>
            <option value="Poultry">Poultry</option>
          </select>
        </div>

        <div className="space-y-1">
          <label className="text-xs font-medium text-gray-600">District</label>
          <select
            value={selectedDistrict}
            onChange={(e) => setSelectedDistrict(e.target.value)}
            className="block w-40 rounded-lg border-gray-300 shadow-xs text-xs p-2 border bg-white focus:ring-brandBlue focus:border-brandBlue"
          >
            <option value="All">All Districts</option>
            {DISTRICT_NAMES.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
        </div>

        <div className="space-y-1">
          <label className="text-xs font-medium text-gray-600">Suspected Disease</label>
          <select
            value={selectedDisease}
            onChange={(e) => setSelectedDisease(e.target.value)}
            className="block w-40 rounded-lg border-gray-300 shadow-xs text-xs p-2 border bg-white focus:ring-brandBlue focus:border-brandBlue"
          >
            <option value="All">All Diseases</option>
            <option value="Foot-and-Mouth Disease (FMD)">FMD</option>
            <option value="Lumpy Skin Disease (LSD)">LSD</option>
            <option value="Peste des Petits Ruminants (PPR)">PPR</option>
            <option value="Brucellosis">Brucellosis</option>
          </select>
        </div>

        {(selectedSpecies !== "All" || selectedDistrict !== "All" || selectedDisease !== "All") && (
          <button
            onClick={() => {
              setSelectedSpecies("All");
              setSelectedDistrict("All");
              setSelectedDisease("All");
            }}
            className="text-xs text-blue-600 hover:underline pb-2 font-medium"
          >
            Reset Filters
          </button>
        )}
      </div>

      {/* Table */}
      <div className="flex-1 overflow-x-auto overflow-y-auto custom-scrollbar">
        <table className="min-w-full divide-y divide-gray-200 min-w-[720px]">
          <thead className="bg-gray-100 text-gray-700 text-xs font-bold uppercase tracking-wider sticky top-0 shadow-xs">
            <tr>
              {["Date", "Report #", "Village", "District", "Species", "Disease", "Affected", "Deaths", "Triage Risk", "Status"].map(
                (col) => (
                  <th key={col} className="px-5 py-3 text-left">
                    {col}
                  </th>
                )
              )}
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-100 text-xs">
            {filteredReports.length === 0 ? (
              <tr>
                <td colSpan={10} className="px-6 py-12 text-center text-gray-400">
                  No records match the current filter criteria.
                </td>
              </tr>
            ) : (
              filteredReports.map((row) => (
                <tr key={row.id} className="hover:bg-blue-50/40 transition-colors">
                  <td className="px-5 py-3.5 whitespace-nowrap text-gray-500 font-mono">{row.date}</td>
                  <td className="px-5 py-3.5 whitespace-nowrap text-gray-700 font-mono">{row.reportNumber || row.id}</td>
                  <td className="px-5 py-3.5 whitespace-nowrap font-medium text-gray-900">{row.village}</td>
                  <td className="px-5 py-3.5 whitespace-nowrap text-gray-600">{row.district}</td>
                  <td className="px-5 py-3.5 whitespace-nowrap font-medium text-gray-800">{row.species}</td>
                  <td className="px-5 py-3.5 whitespace-nowrap text-gray-900 font-bold">{row.disease || "-"}</td>
                  <td className="px-5 py-3.5 whitespace-nowrap text-gray-700 font-bold">{row.numberAffected}</td>
                  <td className="px-5 py-3.5 whitespace-nowrap text-red-600 font-bold">{row.numberDead}</td>
                  <td className="px-5 py-3.5 whitespace-nowrap">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        row.triageRiskLevel === "CRITICAL"
                          ? "bg-red-100 text-red-800"
                          : row.triageRiskLevel === "HIGH"
                          ? "bg-orange-100 text-orange-800"
                          : "bg-blue-100 text-blue-800"
                      }`}
                    >
                      {row.triageRiskLevel || "MODERATE"}
                    </span>
                  </td>
                  <td className="px-5 py-3.5 whitespace-nowrap">
                    <span
                      className={`px-2.5 py-1 rounded-full text-[11px] font-bold ${
                        row.status === "Suspected"
                          ? "bg-amber-100 text-amber-800"
                          : row.status === "Confirmed"
                          ? "bg-red-100 text-red-800"
                          : "bg-emerald-100 text-emerald-800"
                      }`}
                    >
                      {row.status}
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
