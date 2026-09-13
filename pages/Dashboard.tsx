import React, { useState } from "react";
import { 
  AlertTriangle, ShieldCheck, MapPin, 
  Activity, TestTube2, Stethoscope, ArrowRight, Plus, 
  HeartPulse, Syringe, BellRing, CheckCircle
} from "lucide-react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";
import { MapContainer, TileLayer, CircleMarker, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import { useNavigate } from "react-router-dom";
import { useAppContext } from "../context/AppContext";
import { useMultilingual } from "../context/MultilingualContext";
import { Phone } from "lucide-react";

export default function Dashboard() {
  const { t } = useMultilingual();
  const navigate = useNavigate();
  const { reports, alerts, totalPopulation, vaccinationCoverage } = useAppContext();
  const [trendFilter, setTrendFilter] = useState("30");

  const activeOutbreaks = reports.filter(r => r.status !== "Resolved").length;
  const highRiskDistricts = 12; // Mock value
  const pendingInvestigations = 8; // Mock value
  const pendingLabResults = 24; // Mock value

  const stats = [
    { label: "Active Cases", value: "3,214", icon: Activity, color: "bg-red-100 text-red-600", trend: "+12%" },
    { label: "Active Outbreaks", value: activeOutbreaks.toString(), icon: AlertTriangle, color: "bg-orange-100 text-orange-600", trend: "+2" },
    { label: "High-Risk Districts", value: highRiskDistricts.toString(), icon: MapPin, color: "bg-purple-100 text-purple-600", trend: "-1" },
    { label: "Pending Investigations", value: pendingInvestigations.toString(), icon: Stethoscope, color: "bg-blue-100 text-blue-600", trend: "-3" },
    { label: "Pending Lab Results", value: pendingLabResults.toString(), icon: TestTube2, color: "bg-indigo-100 text-indigo-600", trend: "+8" },
    { label: "Vaccination Coverage", value: `${vaccinationCoverage}%`, icon: ShieldCheck, color: "bg-green-100 text-green-600", trend: "+2.4%" },
  ];

  const trendData = [
    { date: "01 Sep", cases: 45, recovered: 30 },
    { date: "02 Sep", cases: 52, recovered: 38 },
    { date: "03 Sep", cases: 61, recovered: 42 },
    { date: "04 Sep", cases: 58, recovered: 50 },
    { date: "05 Sep", cases: 72, recovered: 55 },
    { date: "06 Sep", cases: 68, recovered: 60 },
    { date: "07 Sep", cases: 75, recovered: 65 },
  ];

  const quickActions = [
    { label: "Report Case", icon: Plus, path: "/reporting", color: "bg-red-50 text-red-700 border-red-200 hover:bg-red-100" },
    { label: "Register Animal/Herd", icon: HeartPulse, path: "/animal-health", color: "bg-blue-50 text-blue-700 border-blue-200 hover:bg-blue-100" },
    { label: "Collect Sample", icon: TestTube2, path: "/lab", color: "bg-indigo-50 text-indigo-700 border-indigo-200 hover:bg-indigo-100" },
    { label: "Record Vaccination", icon: Syringe, path: "/vaccination", color: "bg-green-50 text-green-700 border-green-200 hover:bg-green-100" },
    { label: "View High-Risk Areas", icon: MapPin, path: "/gis", color: "bg-purple-50 text-purple-700 border-purple-200 hover:bg-purple-100" },
  ];

  const pendingActions = [
    { id: 1, text: "Verify FMD outbreak in Pune", type: "Investigation", time: "2 hrs ago" },
    { id: 2, text: "Approve lab results for batch #402", type: "Lab", time: "4 hrs ago" },
    { id: 3, text: "Dispatch vaccination team to Nashik", type: "Vaccination", time: "5 hrs ago" },
  ];

  return (
    <div className="space-y-6 pb-8">
      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {stats.map((stat, i) => {
          const Icon = stat.icon;
          return (
            <div key={i} className="bg-white p-4 rounded-xl shadow-sm border border-gray-200 flex flex-col justify-between hover:shadow-md transition-shadow">
              <div className="flex justify-between items-start mb-2">
                <div className={`p-2 rounded-lg ${stat.color}`}><Icon size={20} /></div>
                <span className={`text-xs font-bold ${stat.trend.startsWith("+") ? "text-red-500" : "text-green-500"}`}>
                  {stat.trend}
                </span>
              </div>
              <div>
                <p className="text-xl font-bold text-gray-900">{stat.value}</p>
                <p className="text-xs font-medium text-gray-500 leading-tight mt-1">{stat.label}</p>
              </div>
            </div>
          );
        })}
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        {quickActions.map((action, i) => {
          const Icon = action.icon;
          return (
            <button key={i} onClick={() => navigate(action.path)} className={`flex items-center justify-center gap-2 p-3 rounded-xl border text-sm font-bold transition-colors ${action.color}`}>
              <Icon size={18} /> {action.label}
            </button>
          );
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Map */}
        <div className="bg-white p-5 rounded-xl shadow-sm border border-gray-200 lg:col-span-2 flex flex-col h-full min-h-[400px]">
          <div className="flex justify-between items-center mb-4">
            <h3 className="font-bold text-gray-900 flex items-center gap-2"><MapPin className="text-brandBlue"/> Maharashtra Disease Risk Map</h3>
            <div className="flex gap-3 text-xs font-medium">
               <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-500"></span> Outbreak</span>
               <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-orange-500"></span> High Risk</span>
               <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-yellow-400"></span> Watch</span>
            </div>
          </div>
          <div className="flex-1 bg-gray-50 rounded-lg overflow-hidden border border-gray-200 relative z-0">
             <MapContainer center={[19.7515, 75.7139]} zoom={6} style={{ height: "100%", width: "100%", zIndex: 1 }} zoomControl={false}>
                <TileLayer url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png" />
                <CircleMarker center={[18.5204, 73.8567]} radius={15} pathOptions={{ color: "red", fillColor: "red", fillOpacity: 0.4 }}><Popup>Pune: Active FMD Outbreak</Popup></CircleMarker>
                <CircleMarker center={[19.9975, 73.7898]} radius={10} pathOptions={{ color: "orange", fillColor: "orange", fillOpacity: 0.4 }}><Popup>Nashik: High Risk (LSD)</Popup></CircleMarker>
                <CircleMarker center={[21.1458, 79.0882]} radius={8} pathOptions={{ color: "#fbbf24", fillColor: "#fbbf24", fillOpacity: 0.4 }}><Popup>Nagpur: Watch Zone</Popup></CircleMarker>
             </MapContainer>
          </div>
        </div>

        {/* Pending Actions & Alerts */}
        <div className="space-y-6">
           <div className="bg-white rounded-xl shadow-sm border border-gray-200 flex flex-col h-[188px]">
              <div className="p-4 border-b border-gray-100 flex justify-between items-center">
                 <h3 className="font-bold text-gray-900 flex items-center gap-2"><CheckCircle className="text-brandBlue" size={18}/> Pending Actions</h3>
                 <span className="px-2 py-1 bg-red-100 text-red-700 text-xs font-bold rounded-full">{pendingActions.length}</span>
              </div>
              <div className="flex-1 overflow-y-auto p-2">
                 {pendingActions.map(act => (
                    <div key={act.id} className="p-3 hover:bg-gray-50 rounded-lg flex items-start gap-3 cursor-pointer group">
                       <div className="mt-0.5 w-2 h-2 rounded-full bg-red-500 shrink-0"></div>
                       <div>
                          <p className="text-sm font-medium text-gray-800 group-hover:text-brandBlue">{act.text}</p>
                          <p className="text-xs text-gray-500 mt-1">{act.type} • {act.time}</p>
                       </div>
                    </div>
                 ))}
              </div>
           </div>

           <div className="bg-white rounded-xl shadow-sm border border-gray-200 flex flex-col h-[188px]">
              <div className="p-4 border-b border-gray-100 flex justify-between items-center">
                 <h3 className="font-bold text-gray-900 flex items-center gap-2"><BellRing className="text-orange-500" size={18}/> Recent Alerts</h3>
                 <button onClick={() => navigate("/alerts")} className="text-xs text-brandBlue hover:underline font-medium">View All</button>
              </div>
              <div className="flex-1 overflow-y-auto p-2">
                 {alerts.slice(0,3).map(alert => (
                    <div key={alert.id} className="p-3 hover:bg-gray-50 rounded-lg flex flex-col gap-1 cursor-pointer">
                       <div className="flex justify-between items-start">
                          <p className="text-sm font-medium text-gray-800 truncate pr-2">{alert.title}</p>
                          <span className="text-[10px] font-bold text-gray-400 bg-gray-100 px-1.5 py-0.5 rounded whitespace-nowrap">{alert.type.toUpperCase()}</span>
                       </div>
                       <p className="text-xs text-gray-500">Alert - {alert.time}</p>
                    </div>
                 ))}
              </div>
           </div>

           <div className="bg-gray-50 rounded-xl shadow-sm border border-gray-200 flex flex-col p-5 text-center">
              <div className="flex justify-center items-center gap-2 mb-2">
                 <Phone className="text-gray-700 fill-gray-700" size={20} />
                 <h3 className="font-bold text-gray-900 text-lg">{t('helpline.title')}</h3>
              </div>
              <p className="font-bold text-gray-800 text-sm mb-1">{t('helpline.subtitle')}</p>
              <p className="text-gray-600 text-xs mb-4">{t('helpline.timing')}</p>
              <div className="text-4xl font-bold text-[#d32f2f] mb-5">{t('helpline.number')}</div>
              
              <div className="border-t border-gray-300 w-full mb-4"></div>
              
              <div className="flex justify-center items-center gap-2 mb-4">
                 <MapPin className="text-[#d32f2f] fill-[#d32f2f]" size={18} />
                 <h3 className="font-bold text-gray-900 text-sm">{t('helpline.mvuTitle')}</h3>
              </div>
              
              <button className="bg-[#1e8449] hover:bg-[#145a32] text-white font-bold py-2.5 px-4 rounded-lg transition-colors w-full">
                 {t('helpline.mvuButton')}
              </button>
           </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Disease Trends Chart */}
        <div className="bg-white p-5 rounded-xl shadow-sm border border-gray-200">
           <div className="flex justify-between items-center mb-6">
              <h3 className="font-bold text-gray-900 flex items-center gap-2"><Activity className="text-brandBlue"/> Disease Trends</h3>
              <select value={trendFilter} onChange={e => setTrendFilter(e.target.value)} className="border border-gray-300 rounded-lg text-sm px-3 py-1.5 focus:ring-brandBlue focus:border-brandBlue">
                 <option value="7">Last 7 Days</option>
                 <option value="30">Last 30 Days</option>
                 <option value="90">Last 90 Days</option>
              </select>
           </div>
           <div className="h-[250px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                 <LineChart data={trendData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e5e7eb" />
                    <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: "#6b7280" }} dy={10} />
                    <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: "#6b7280" }} />
                    <Tooltip contentStyle={{ borderRadius: "8px", border: "none", boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)" }} />
                    <Legend iconType="circle" wrapperStyle={{ fontSize: "12px", paddingTop: "10px" }} />
                    <Line type="monotone" name="New Cases" dataKey="cases" stroke="#ef4444" strokeWidth={3} dot={false} activeDot={{ r: 6 }} />
                    <Line type="monotone" name="Recovered" dataKey="recovered" stroke="#10b981" strokeWidth={3} dot={false} activeDot={{ r: 6 }} />
                 </LineChart>
              </ResponsiveContainer>
           </div>
        </div>

        {/* High Risk Districts Table */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 flex flex-col">
           <div className="p-5 border-b border-gray-100 flex justify-between items-center">
              <h3 className="font-bold text-gray-900 flex items-center gap-2"><AlertTriangle className="text-orange-500"/> High-Risk Districts</h3>
              <button onClick={() => navigate("/analytics")} className="text-sm text-brandBlue hover:underline font-medium flex items-center gap-1">Details <ArrowRight size={14}/></button>
           </div>
           <div className="flex-1 overflow-x-auto p-4">
              <table className="w-full text-left text-sm whitespace-nowrap">
                 <thead className="text-gray-500 font-medium border-b border-gray-200">
                    <tr>
                       <th className="pb-3 pr-4">District</th>
                       <th className="pb-3 px-4">Primary Risk</th>
                       <th className="pb-3 px-4">Active Cases</th>
                       <th className="pb-3 pl-4 text-right">Trend</th>
                    </tr>
                 </thead>
                 <tbody className="divide-y divide-gray-100">
                    <tr className="hover:bg-gray-50">
                       <td className="py-3 pr-4 font-bold text-gray-900">Pune</td>
                       <td className="py-3 px-4"><span className="px-2 py-1 bg-red-100 text-red-700 text-xs font-bold rounded-full">FMD</span></td>
                       <td className="py-3 px-4 text-gray-700">452</td>
                       <td className="py-3 pl-4 text-right text-red-500 font-bold">↑ 12%</td>
                    </tr>
                    <tr className="hover:bg-gray-50">
                       <td className="py-3 pr-4 font-bold text-gray-900">Nashik</td>
                       <td className="py-3 px-4"><span className="px-2 py-1 bg-orange-100 text-orange-700 text-xs font-bold rounded-full">LSD</span></td>
                       <td className="py-3 px-4 text-gray-700">318</td>
                       <td className="py-3 pl-4 text-right text-orange-500 font-bold">↑ 5%</td>
                    </tr>
                    <tr className="hover:bg-gray-50">
                       <td className="py-3 pr-4 font-bold text-gray-900">Ahmednagar</td>
                       <td className="py-3 px-4"><span className="px-2 py-1 bg-yellow-100 text-yellow-800 text-xs font-bold rounded-full">Brucellosis</span></td>
                       <td className="py-3 px-4 text-gray-700">189</td>
                       <td className="py-3 pl-4 text-right text-gray-400 font-bold">— 0%</td>
                    </tr>
                    <tr className="hover:bg-gray-50">
                       <td className="py-3 pr-4 font-bold text-gray-900">Satara</td>
                       <td className="py-3 px-4"><span className="px-2 py-1 bg-red-100 text-red-700 text-xs font-bold rounded-full">FMD</span></td>
                       <td className="py-3 px-4 text-gray-700">145</td>
                       <td className="py-3 pl-4 text-right text-green-500 font-bold">↓ 8%</td>
                    </tr>
                 </tbody>
              </table>
           </div>
        </div>
      </div>
    </div>
  );
}
