import { useState, useEffect } from "react";
import { 
  AlertTriangle, ShieldCheck, MapPin, 
  Activity, TestTube2, Stethoscope, ArrowRight, Plus, 
  HeartPulse, Syringe, BellRing, CheckCircle, Database
} from "lucide-react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";
import { useNavigate } from "react-router-dom";
import { useAppContext } from "../context/AppContext";
import { useMultilingual } from "../context/MultilingualContext";
import { useSync } from "../services/SyncService";
import { Phone } from "lucide-react";
import PashuMap from "../components/PashuMap";
import ActivityFeedWidget from "../components/ActivityFeedWidget";

export default function Dashboard() {
  const { t } = useMultilingual();
  const navigate = useNavigate();
  const { alerts } = useAppContext();
  const { pendingCount, feedStatus, openSyncModal } = useSync();
  const [trendFilter, setTrendFilter] = useState("30");
  const [kpiData, setKpiData] = useState<any[]>([]);
  const [lastUpdated, setLastUpdated] = useState<string>("");

  useEffect(() => {
    fetch("/api/v1/surveillance/overview")
      .then((res) => res.json())
      .then((data) => {
        if (data?.kpis) {
          setKpiData(data.kpis);
          setLastUpdated(new Date().toLocaleTimeString());
        }
      })
      .catch(() => {});
  }, []);

  const defaultStats = [
    { label: "Active Reports", value: "14", icon: Activity, color: "bg-red-100 text-red-600", trend: "+4%" },
    { label: "Active Vet Cases", value: "8", icon: Stethoscope, color: "bg-blue-100 text-blue-600", trend: "+2" },
    { label: "Outbreak Clusters", value: "3", icon: AlertTriangle, color: "bg-orange-100 text-orange-600", trend: "+1" },
    { label: "High-Risk Districts", value: "4", icon: MapPin, color: "bg-purple-100 text-purple-600", trend: "-1" },
    { label: "Pending Lab Samples", value: "11", icon: TestTube2, color: "bg-indigo-100 text-indigo-600", trend: "-2" },
    { label: "State Vaccination", value: "78.1%", icon: ShieldCheck, color: "bg-green-100 text-green-600", trend: "+2.4%" },
  ];

  const displayStats = kpiData.length > 0 ? kpiData.slice(0, 6).map((k, idx) => ({
    label: k.label,
    value: k.value.toString(),
    icon: defaultStats[idx]?.icon || Activity,
    color: defaultStats[idx]?.color || "bg-blue-100 text-blue-600",
    trend: k.trend || "0%",
    provenance: k.provenance || "LIVE"
  })) : defaultStats;

  const trendData = [
    { date: "01 Sep", cases: 45, recovered: 30 },
    { date: "04 Sep", cases: 52, recovered: 38 },
    { date: "07 Sep", cases: 61, recovered: 42 },
    { date: "10 Sep", cases: 58, recovered: 50 },
    { date: "13 Sep", cases: 72, recovered: 55 },
    { date: "16 Sep", cases: 68, recovered: 60 },
    { date: "19 Sep", cases: 75, recovered: 65 },
  ];

  const quickActions = [
    { label: "Report Case", icon: Plus, path: "/reporting", color: "bg-red-50 text-red-700 border-red-200 hover:bg-red-100" },
    { label: "Register Animal/Herd", icon: HeartPulse, path: "/animal-health", color: "bg-blue-50 text-blue-700 border-blue-200 hover:bg-blue-100" },
    { label: "Collect Sample", icon: TestTube2, path: "/lab", color: "bg-indigo-50 text-indigo-700 border-indigo-200 hover:bg-indigo-100" },
    { label: "Record Vaccination", icon: Syringe, path: "/vaccination", color: "bg-green-50 text-green-700 border-green-200 hover:bg-green-100" },
    { label: "View High-Risk Areas", icon: MapPin, path: "/gis", color: "bg-purple-50 text-purple-700 border-purple-200 hover:bg-purple-100" },
  ];

  const pendingActions = [
    { id: 1, text: "Verify FMD outbreak in Shirur (Pune)", type: "Investigation", time: "1 hr ago", route: "/surveillance" },
    { id: 2, text: "Sign-off RT-PCR results for batch SMP-10231", type: "Lab Verification", time: "2 hrs ago", route: "/lab" },
    { id: 3, text: "Dispatch Mobile Veterinary Unit to Karad", type: "Veterinary Dispatch", time: "3 hrs ago", route: "/vet-response" },
  ];

  const mapPoints = [
    { id: "PUN-01", name: "Pune: Active FMD Cluster (Shirur)", lat: 18.8288, lng: 74.3789, type: "cluster" as const, riskLevel: "Critical" as const, details: "34 cattle affected, 1 mortality" },
    { id: "SAT-01", name: "Satara: Goat Pox Hotspot", lat: 17.6805, lng: 74.0183, type: "cluster" as const, riskLevel: "High Risk" as const, details: "18 cases under field observation" },
    { id: "NAS-01", name: "Nashik: LSD Syndromic Watch", lat: 20.0110, lng: 73.7903, type: "cluster" as const, riskLevel: "Moderate Risk" as const, details: "Ring vaccination in progress" },
    { id: "NAG-01", name: "Nagpur: Surveillance Baseline", lat: 21.1458, lng: 79.0882, type: "facility" as const, details: "Regional Disease Diagnostic Lab" }
  ];

  return (
    <div className="space-y-6 pb-8 max-w-full overflow-hidden">
      {/* Top Provenance & Live Stream Status Banner */}
      <div className="bg-white px-3 sm:px-4 py-2.5 rounded-xl border border-gray-200 flex flex-wrap items-center justify-between text-xs text-gray-600 gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-ping shrink-0" />
          <span className="font-bold text-gray-900">DATA STREAM: {feedStatus}</span>
          <span className="text-gray-300 hidden sm:inline">|</span>
          <span className="hidden sm:inline">Coverage: All 36 Maharashtra Districts</span>
          <span className="text-gray-300 hidden md:inline">|</span>
          <span className="hidden md:inline">Sources: Field Reports, 20th Census (DAHD)</span>
        </div>

        <div className="flex items-center gap-2">
          {pendingCount > 0 && (
            <button
              onClick={openSyncModal}
              className="text-[11px] font-bold text-amber-700 bg-amber-50 hover:bg-amber-100 border border-amber-200 px-2 py-0.5 rounded-full flex items-center gap-1"
            >
              <Database size={11} />
              <span>Offline Queue: {pendingCount}</span>
            </button>
          )}
          {lastUpdated && (
            <div className="text-gray-500 font-mono text-[11px]">
              Refreshed: {lastUpdated}
            </div>
          )}
        </div>
      </div>

      {/* KPI Cards: Responsive Grid (1 col on mobile 320px, 2 col on 375px+, 3 col on md, 6 col on lg+) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 sm:gap-4">
        {displayStats.map((stat, i) => {
          const Icon = stat.icon;
          return (
            <div 
              key={i} 
              className="bg-white p-4 rounded-xl shadow-xs border border-gray-200 flex flex-col justify-between hover:shadow-md transition-shadow min-w-0"
            >
              <div className="flex justify-between items-start mb-2">
                <div className={`p-2 rounded-lg shrink-0 ${stat.color}`}>
                  <Icon size={20} />
                </div>
                <span className={`text-xs font-bold px-1.5 py-0.5 rounded ${
                  stat.trend.startsWith("+") ? "text-red-600 bg-red-50" : "text-green-600 bg-green-50"
                }`}>
                  {stat.trend}
                </span>
              </div>
              <div className="min-w-0">
                <p className="text-xl sm:text-2xl font-black text-gray-900 truncate">{stat.value}</p>
                <p className="text-xs font-medium text-gray-500 leading-tight mt-1 truncate">{stat.label}</p>
              </div>
            </div>
          );
        })}
      </div>

      {/* Quick Actions: Responsive Grid with touch-friendly min height */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
        {quickActions.map((action, i) => {
          const Icon = action.icon;
          return (
            <button 
              key={i} 
              onClick={() => navigate(action.path)} 
              className={`flex items-center justify-center gap-2 p-3 sm:p-3.5 rounded-xl border text-xs sm:text-sm font-bold transition-all min-h-[44px] touch-manipulation text-center ${action.color}`}
            >
              <Icon size={18} className="shrink-0" />
              <span className="truncate">{action.label}</span>
            </button>
          );
        })}
      </div>

      {/* Main Row: Map (2 cols on lg) + Pending Actions / Alerts (1 col on lg) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Map with Google Maps / Leaflet adapter */}
        <div className="bg-white p-4 sm:p-5 rounded-2xl shadow-xs border border-gray-200 lg:col-span-2 flex flex-col min-h-[380px] sm:min-h-[440px] overflow-hidden">
          <div className="flex flex-wrap justify-between items-center gap-2 mb-3">
            <h3 className="font-bold text-gray-900 flex items-center gap-2 text-sm sm:text-base">
              <MapPin className="text-brandBlue shrink-0" size={18}/> 
              <span>Maharashtra Disease Surveillance GIS Map</span>
            </h3>
            <div className="flex flex-wrap gap-2 text-[11px] font-medium">
              <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-red-600"></span> Outbreak</span>
              <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-orange-500"></span> High Risk</span>
              <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-blue-600"></span> Facility</span>
            </div>
          </div>
          <div className="flex-1 rounded-xl overflow-hidden border border-gray-200 relative min-h-[280px]">
            <PashuMap
              center={[19.25, 75.5]}
              zoom={7}
              points={mapPoints}
              height="100%"
            />
          </div>
        </div>

        {/* Side Actions & Emergency MVU Banner */}
        <div className="space-y-4 sm:space-y-6 flex flex-col">
          {/* Pending Triage Actions */}
          <div className="bg-white rounded-2xl shadow-xs border border-gray-200 flex flex-col min-h-[160px] overflow-hidden">
            <div className="p-3.5 border-b border-gray-100 flex justify-between items-center bg-gray-50/50">
              <h3 className="font-bold text-gray-900 text-xs sm:text-sm flex items-center gap-2">
                <CheckCircle className="text-brandBlue" size={16}/> Pending Triage & Actions
              </h3>
              <span className="px-2 py-0.5 bg-red-100 text-red-700 text-[10px] font-bold rounded-full">
                {pendingActions.length}
              </span>
            </div>
            <div className="flex-1 overflow-y-auto p-2 space-y-1">
              {pendingActions.map(act => (
                <div 
                  key={act.id} 
                  onClick={() => navigate(act.route)}
                  className="p-2.5 hover:bg-gray-50 rounded-xl flex items-start gap-2.5 cursor-pointer group transition-colors"
                >
                  <div className="mt-1 w-2 h-2 rounded-full bg-red-500 shrink-0" />
                  <div className="min-w-0 flex-1">
                    <p className="text-xs font-semibold text-gray-800 group-hover:text-brandBlue transition-colors truncate">
                      {act.text}
                    </p>
                    <p className="text-[10px] text-gray-500 mt-0.5">{act.type} • {act.time}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Quick Recent Alerts */}
          <div className="bg-white rounded-2xl shadow-xs border border-gray-200 flex flex-col min-h-[160px] overflow-hidden">
            <div className="p-3.5 border-b border-gray-100 flex justify-between items-center bg-gray-50/50">
              <h3 className="font-bold text-gray-900 text-xs sm:text-sm flex items-center gap-2">
                <BellRing className="text-orange-500" size={16}/> Recent Alerts
              </h3>
              <button 
                onClick={() => navigate("/alerts")} 
                className="text-xs text-brandBlue hover:underline font-semibold"
              >
                View All
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-2 space-y-1">
              {alerts.slice(0, 3).map(alert => (
                <div 
                  key={alert.id} 
                  onClick={() => navigate("/alerts")}
                  className="p-2.5 hover:bg-gray-50 rounded-xl flex flex-col gap-0.5 cursor-pointer transition-colors"
                >
                  <div className="flex justify-between items-start gap-2">
                    <p className="text-xs font-semibold text-gray-800 truncate">{alert.title}</p>
                    <span className="text-[9px] font-bold text-gray-500 bg-gray-100 px-1.5 py-0.2 rounded shrink-0">
                      {alert.type.toUpperCase()}
                    </span>
                  </div>
                  <p className="text-[10px] text-gray-500">{alert.time}</p>
                </div>
              ))}
            </div>
          </div>

          {/* 1962 Emergency Hotline Banner */}
          <div className="bg-gradient-to-br from-red-50 to-orange-50 rounded-2xl border border-red-200 p-4 text-center">
            <div className="flex justify-center items-center gap-1.5 mb-1 text-red-700">
              <Phone size={18} />
              <h3 className="font-black text-sm">{t('helpline.title')}</h3>
            </div>
            <p className="text-xs text-gray-700 mb-1 font-semibold">{t('helpline.subtitle')}</p>
            <div className="text-3xl font-black text-red-600 mb-2 tracking-tight">1962</div>
            <p className="text-[11px] text-gray-500 mb-3">{t('helpline.timing')}</p>
            
            <button 
              onClick={() => navigate("/gis")} 
              className="bg-emerald-700 hover:bg-emerald-800 text-white font-bold py-2 px-3 rounded-xl transition-colors w-full text-xs shadow-xs min-h-[38px] touch-manipulation"
            >
              {t('helpline.mvuButton')}
            </button>
          </div>
        </div>
      </div>

      {/* REAL-TIME ACTIVITY FEED SECTION */}
      <div className="w-full">
        <ActivityFeedWidget maxItems={8} />
      </div>

      {/* Charts & High-Risk Table Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Disease Trends Chart */}
        <div className="bg-white p-4 sm:p-5 rounded-2xl shadow-xs border border-gray-200 overflow-hidden">
          <div className="flex justify-between items-center mb-4 flex-wrap gap-2">
            <h3 className="font-bold text-gray-900 flex items-center gap-2 text-sm sm:text-base">
              <Activity className="text-brandBlue shrink-0" size={18}/> Disease Trends
            </h3>
            <select 
              value={trendFilter} 
              onChange={e => setTrendFilter(e.target.value)} 
              className="border border-gray-300 rounded-lg text-xs px-2.5 py-1.5 focus:ring-brandBlue focus:border-brandBlue bg-white"
            >
              <option value="7">Last 7 Days</option>
              <option value="30">Last 30 Days</option>
              <option value="90">Last 90 Days</option>
            </select>
          </div>
          <div className="h-[240px] sm:h-[260px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trendData} margin={{ top: 5, right: 10, bottom: 5, left: -15 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e5e7eb" />
                <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: "#6b7280" }} dy={8} />
                <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: "#6b7280" }} />
                <Tooltip contentStyle={{ borderRadius: "8px", border: "none", boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)", fontSize: "12px" }} />
                <Legend iconType="circle" wrapperStyle={{ fontSize: "11px", paddingTop: "8px" }} />
                <Line type="monotone" name="New Cases" dataKey="cases" stroke="#ef4444" strokeWidth={2.5} dot={false} activeDot={{ r: 5 }} />
                <Line type="monotone" name="Recovered" dataKey="recovered" stroke="#10b981" strokeWidth={2.5} dot={false} activeDot={{ r: 5 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* High Risk Districts Table */}
        <div className="bg-white rounded-2xl shadow-xs border border-gray-200 flex flex-col overflow-hidden">
          <div className="p-4 sm:p-5 border-b border-gray-100 flex justify-between items-center bg-gray-50/40">
            <h3 className="font-bold text-gray-900 flex items-center gap-2 text-sm sm:text-base">
              <AlertTriangle className="text-orange-500 shrink-0" size={18}/> High-Risk Districts
            </h3>
            <button 
              onClick={() => navigate("/analytics")} 
              className="text-xs text-brandBlue hover:underline font-semibold flex items-center gap-1"
            >
              <span>Details</span>
              <ArrowRight size={13}/>
            </button>
          </div>
          <div className="flex-1 overflow-x-auto p-3 sm:p-4 custom-scrollbar">
            <table className="w-full text-left text-xs whitespace-nowrap min-w-[320px]">
              <thead className="text-gray-500 font-bold border-b border-gray-200">
                <tr>
                  <th className="pb-2.5 pr-3">District</th>
                  <th className="pb-2.5 px-3">Primary Risk</th>
                  <th className="pb-2.5 px-3">Active Cases</th>
                  <th className="pb-2.5 pl-3 text-right">Trend</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                <tr className="hover:bg-gray-50">
                  <td className="py-2.5 pr-3 font-bold text-gray-900">Pune</td>
                  <td className="py-2.5 px-3"><span className="px-2 py-0.5 bg-red-100 text-red-700 text-[10px] font-bold rounded-full">FMD</span></td>
                  <td className="py-2.5 px-3 text-gray-700">452</td>
                  <td className="py-2.5 pl-3 text-right text-red-500 font-bold">↑ 12%</td>
                </tr>
                <tr className="hover:bg-gray-50">
                  <td className="py-2.5 pr-3 font-bold text-gray-900">Nashik</td>
                  <td className="py-2.5 px-3"><span className="px-2 py-0.5 bg-orange-100 text-orange-700 text-[10px] font-bold rounded-full">LSD</span></td>
                  <td className="py-2.5 px-3 text-gray-700">318</td>
                  <td className="py-2.5 pl-3 text-right text-orange-500 font-bold">↑ 5%</td>
                </tr>
                <tr className="hover:bg-gray-50">
                  <td className="py-2.5 pr-3 font-bold text-gray-900">Ahmednagar</td>
                  <td className="py-2.5 px-3"><span className="px-2 py-0.5 bg-yellow-100 text-yellow-800 text-[10px] font-bold rounded-full">Brucellosis</span></td>
                  <td className="py-2.5 px-3 text-gray-700">189</td>
                  <td className="py-2.5 pl-3 text-right text-gray-400 font-bold">— 0%</td>
                </tr>
                <tr className="hover:bg-gray-50">
                  <td className="py-2.5 pr-3 font-bold text-gray-900">Satara</td>
                  <td className="py-2.5 px-3"><span className="px-2 py-0.5 bg-red-100 text-red-700 text-[10px] font-bold rounded-full">FMD</span></td>
                  <td className="py-2.5 px-3 text-gray-700">145</td>
                  <td className="py-2.5 pl-3 text-right text-green-500 font-bold">↓ 8%</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
