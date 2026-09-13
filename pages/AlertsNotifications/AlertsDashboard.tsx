import { useAlerts } from "../../context/AlertsContext";
import { AlertTriangle, AlertCircle, ShieldAlert, Activity, Flame } from "lucide-react";

export default function AlertsDashboard() {
  const { alerts } = useAlerts();

  const criticalAlerts = alerts.filter(a => a.priority === "CRITICAL" && a.status !== "RESOLVED").length;
  const highRiskAlerts = alerts.filter(a => a.priority === "HIGH" && a.status !== "RESOLVED").length;
  const activeOutbreaks = alerts.filter(a => a.type === "OUTBREAK" && a.status !== "RESOLVED").length;
  const unresolvedCases = alerts.filter(a => a.status !== "RESOLVED").length;
  const animalsAtRisk = alerts
    .filter(a => a.status !== "RESOLVED")
    .reduce((acc, curr) => acc + (curr.affectedAnimals || 0), 0);

  return (
    <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-6">
      <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm flex flex-col justify-between hover:border-red-300 transition-colors cursor-pointer">
        <div className="flex justify-between items-start">
          <p className="text-sm font-medium text-gray-500">Critical Alerts</p>
          <div className="p-2 bg-red-50 text-red-600 rounded-lg"><Flame size={20} /></div>
        </div>
        <div className="mt-4">
          <p className="text-2xl font-bold text-gray-900">{criticalAlerts}</p>
          <p className="text-xs text-red-600 flex items-center mt-1">Requires immediate action</p>
        </div>
      </div>

      <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm flex flex-col justify-between hover:border-orange-300 transition-colors cursor-pointer">
        <div className="flex justify-between items-start">
          <p className="text-sm font-medium text-gray-500">High Risk</p>
          <div className="p-2 bg-orange-50 text-orange-600 rounded-lg"><AlertTriangle size={20} /></div>
        </div>
        <div className="mt-4">
          <p className="text-2xl font-bold text-gray-900">{highRiskAlerts}</p>
          <p className="text-xs text-orange-600 flex items-center mt-1">Escalated warnings</p>
        </div>
      </div>

      <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm flex flex-col justify-between cursor-pointer">
        <div className="flex justify-between items-start">
          <p className="text-sm font-medium text-gray-500">Active Outbreaks</p>
          <div className="p-2 bg-purple-50 text-purple-600 rounded-lg"><Activity size={20} /></div>
        </div>
        <div className="mt-4">
          <p className="text-2xl font-bold text-gray-900">{activeOutbreaks}</p>
          <p className="text-xs text-gray-500 flex items-center mt-1">Confirmed clusters</p>
        </div>
      </div>

      <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm flex flex-col justify-between cursor-pointer">
        <div className="flex justify-between items-start">
          <p className="text-sm font-medium text-gray-500">Unresolved Alerts</p>
          <div className="p-2 bg-blue-50 text-blue-600 rounded-lg"><ShieldAlert size={20} /></div>
        </div>
        <div className="mt-4">
          <p className="text-2xl font-bold text-gray-900">{unresolvedCases}</p>
          <p className="text-xs text-gray-500 flex items-center mt-1">Total pending attention</p>
        </div>
      </div>

      <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm flex flex-col justify-between cursor-pointer">
        <div className="flex justify-between items-start">
          <p className="text-sm font-medium text-gray-500">Animals at Risk</p>
          <div className="p-2 bg-gray-50 text-gray-600 rounded-lg"><AlertCircle size={20} /></div>
        </div>
        <div className="mt-4">
          <p className="text-2xl font-bold text-gray-900">{animalsAtRisk.toLocaleString()}</p>
          <p className="text-xs text-gray-500 flex items-center mt-1">In active alert zones</p>
        </div>
      </div>
    </div>
  );
}

