import type { AnalyticsData } from "../../services/AnalyticsService";
import { useNavigate } from "react-router-dom";
import { Map as MapIcon, ShieldAlert, Activity, CheckCircle, Syringe, TestTube, AlertTriangle } from "lucide-react";

interface Props {
  data: AnalyticsData;
}

export function GISSummaryCard({ data }: Props) {
  const navigate = useNavigate();
  return (
    <div className="bg-brandBlue text-white p-6 rounded-xl shadow-sm border border-blue-800 relative overflow-hidden flex flex-col justify-between">
       <div className="absolute top-0 right-0 p-4 opacity-10">
          <MapIcon size={120} />
       </div>
       <div className="relative z-10 mb-6">
          <h3 className="text-xl font-bold mb-2 flex items-center gap-2">
             <MapIcon /> Geographical Summary
          </h3>
          <p className="text-blue-100 text-sm">Overview of risk zones and outbreak hotspots across Maharashtra.</p>
       </div>
       <div className="relative z-10 grid grid-cols-2 gap-4 mb-6">
          <div className="bg-white/10 p-3 rounded-lg border border-white/20">
             <div className="text-blue-200 text-xs font-medium mb-1">High-Risk Districts</div>
             <div className="text-2xl font-bold">{data.districtAnalytics.filter(d => d.riskLevel === "CRITICAL" || d.riskLevel === "HIGH").length}</div>
          </div>
          <div className="bg-white/10 p-3 rounded-lg border border-white/20">
             <div className="text-blue-200 text-xs font-medium mb-1">Active Outbreaks</div>
             <div className="text-2xl font-bold">{data.outbreakAnalytics.active}</div>
          </div>
       </div>
       <button onClick={() => navigate("/gis")} className="relative z-10 w-full py-3 bg-white text-brandBlue font-bold rounded-lg shadow-sm hover:bg-gray-50 transition-colors">
          View Full GIS Risk Map
       </button>
    </div>
  );
}

export function OutbreakCard({ data }: Props) {
  return (
    <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200 flex flex-col h-full">
       <h3 className="text-lg font-bold text-gray-900 mb-6 flex items-center gap-2">
          <ShieldAlert className="text-orange-500" /> Outbreak Intelligence
       </h3>
       <div className="space-y-4 flex-1">
          <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
             <span className="text-sm font-medium text-gray-600">Active Outbreaks</span>
             <span className="text-lg font-bold text-gray-900">{data.outbreakAnalytics.active}</span>
          </div>
          <div className="flex justify-between items-center p-3 bg-red-50 text-red-800 rounded-lg border border-red-100">
             <span className="text-sm font-medium">Newly Detected</span>
             <span className="text-lg font-bold">+{data.outbreakAnalytics.newDetected}</span>
          </div>
          <div className="flex justify-between items-center p-3 bg-green-50 text-green-800 rounded-lg border border-green-100">
             <span className="text-sm font-medium">Resolved</span>
             <span className="text-lg font-bold">{data.outbreakAnalytics.resolved}</span>
          </div>
          <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg border border-gray-200">
             <span className="text-sm font-medium text-gray-600">Highest Activity</span>
             <span className="text-sm font-bold text-orange-600">{data.outbreakAnalytics.highestDistrict}</span>
          </div>
       </div>
    </div>
  );
}

export function VaccinationLabCard({ data }: Props) {
  return (
    <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200 flex flex-col h-full">
       <h3 className="text-lg font-bold text-gray-900 mb-6 flex items-center gap-2">
          <Syringe className="text-green-600" /> Vaccination & Laboratory
       </h3>
       
       <div className="mb-6">
          <div className="flex justify-between text-sm mb-1">
             <span className="font-medium text-gray-700">Vaccination Coverage</span>
             <span className="font-bold text-brandBlue">{data.vaccinationAnalytics.coveragePercent}%</span>
          </div>
          <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden mb-2">
             <div className="h-full bg-brandBlue" style={{ width: `${data.vaccinationAnalytics.coveragePercent}%` }}></div>
          </div>
          <div className="flex justify-between text-xs text-gray-500">
             <span>{data.vaccinationAnalytics.vaccinated.toLocaleString()} vaccinated</span>
             <span>{data.vaccinationAnalytics.target.toLocaleString()} target</span>
          </div>
       </div>

       <hr className="border-gray-100 mb-6" />

       <div className="grid grid-cols-2 gap-4">
          <div>
             <div className="text-xs text-gray-500 mb-1 flex items-center gap-1"><TestTube size={12}/> Samples Tested</div>
             <div className="text-xl font-bold text-gray-900">{data.laboratoryAnalytics.tested.toLocaleString()}</div>
          </div>
          <div>
             <div className="text-xs text-gray-500 mb-1 flex items-center gap-1"><AlertTriangle size={12}/> Positivity Rate</div>
             <div className="text-xl font-bold text-red-600">
                {((data.laboratoryAnalytics.positive / data.laboratoryAnalytics.tested) * 100 || 0).toFixed(1)}%
             </div>
          </div>
          <div>
             <div className="text-xs text-gray-500 mb-1">Avg Turnaround</div>
             <div className="text-xl font-bold text-gray-900">{data.laboratoryAnalytics.avgTurnaroundHours}h</div>
          </div>
          <div>
             <div className="text-xs text-gray-500 mb-1">Pending</div>
             <div className="text-xl font-bold text-orange-500">{data.laboratoryAnalytics.pending}</div>
          </div>
       </div>
    </div>
  );
}

export function InsightsPanel({ insights }: { insights: string[] }) {
  return (
    <div className="bg-yellow-50 p-5 rounded-xl border border-yellow-200 shadow-sm mb-6">
       <h3 className="text-lg font-bold text-yellow-800 mb-4 flex items-center gap-2">
          <Activity size={20} /> AI / Surveillance Insights
       </h3>
       <ul className="space-y-3">
          {insights.map((insight, idx) => (
             <li key={idx} className="flex items-start gap-2">
                <CheckCircle className="text-yellow-600 shrink-0 mt-0.5" size={16} />
                <span className="text-sm font-medium text-yellow-900">{insight}</span>
             </li>
          ))}
       </ul>
    </div>
  );
}
