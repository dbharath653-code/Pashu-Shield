import React from "react";
import type { KPIData } from "../../services/AnalyticsService";
import { TrendingUp, TrendingDown, Minus, Activity, ShieldAlert, HeartPulse, ShieldX, TestTube, Syringe } from "lucide-react";

interface Props {
  kpis: KPIData[];
}

export default function AnalyticsKPIs({ kpis }: Props) {
  const getIcon = (label: string) => {
    if (label.includes("Total")) return <Activity size={24} className="text-blue-500" />;
    if (label.includes("Active")) return <ShieldAlert size={24} className="text-orange-500" />;
    if (label.includes("Recovered")) return <HeartPulse size={24} className="text-green-500" />;
    if (label.includes("Mortality")) return <ShieldX size={24} className="text-red-500" />;
    if (label.includes("Tested")) return <TestTube size={24} className="text-purple-500" />;
    if (label.includes("Vaccinated")) return <Syringe size={24} className="text-teal-500" />;
    return <Activity size={24} className="text-gray-500" />;
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "success": return "text-green-600 bg-green-50";
      case "danger": return "text-red-600 bg-red-50";
      case "warning": return "text-orange-600 bg-orange-50";
      default: return "text-gray-600 bg-gray-50";
    }
  };

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      {kpis.map((kpi, idx) => (
        <div key={idx} className="bg-white p-5 rounded-xl shadow-sm border border-gray-200 flex flex-col hover:shadow-md transition-shadow">
           <div className="flex justify-between items-start mb-2">
              <span className="text-sm font-medium text-gray-500">{kpi.label}</span>
              <div className="p-2 bg-gray-50 rounded-lg">
                 {getIcon(kpi.label)}
              </div>
           </div>
           
           <div className="text-3xl font-bold text-gray-900 mb-2">
              {kpi.value.toLocaleString()}
           </div>
           
           <div className={`flex items-center gap-1 text-xs font-medium px-2 py-1 rounded-md w-fit ${getStatusColor(kpi.status)}`}>
              {kpi.trend === "up" ? <TrendingUp size={14} /> : kpi.trend === "down" ? <TrendingDown size={14} /> : <Minus size={14} />}
              <span>{Math.abs(kpi.changePercent)}% vs prev period</span>
           </div>
        </div>
      ))}
    </div>
  );
}
