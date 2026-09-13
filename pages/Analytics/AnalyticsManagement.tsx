import { useState, useEffect } from "react";
import { AnalyticsService } from "../../services/AnalyticsService";
import type { AnalyticsData, FilterOptions } from "../../services/AnalyticsService";
import { BarChart3, Download, FileText } from "lucide-react";

import AnalyticsFilters from "./AnalyticsFilters";
import AnalyticsKPIs from "./AnalyticsKPIs";
import AnalyticsCharts from "./AnalyticsCharts";
import DistrictTable from "./DistrictTable";
import { GISSummaryCard, OutbreakCard, VaccinationLabCard, InsightsPanel } from "./AnalyticsSections";
import ReportGeneratorModal from "./ReportGeneratorModal";

export default function AnalyticsManagement() {
  const [filters, setFilters] = useState<FilterOptions>({
    dateRange: "Last 30 Days",
    district: "All",
    species: "All",
    disease: "All"
  });
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [showReportModal, setShowReportModal] = useState(false);

  const loadData = async () => {
    setLoading(true);
    try {
      const result = await AnalyticsService.getAnalytics(filters);
      setData(result);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleApply = () => {
    loadData();
  };

  const handleReset = () => {
    setFilters({
      dateRange: "Last 30 Days",
      district: "All",
      species: "All",
      disease: "All"
    });
    // Need to trigger load inside useEffect or setTimeout, 
    // but React state is async so just call loadData with default directly:
    setLoading(true);
    AnalyticsService.getAnalytics({
      dateRange: "Last 30 Days",
      district: "All",
      species: "All",
      disease: "All"
    }).then(res => { setData(res); setLoading(false); });
  };

  return (
    <div className="flex flex-col h-full bg-gray-50 p-2 md:p-4 overflow-y-auto">
      {/* Header */}
      <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200 mb-6 flex flex-col md:flex-row justify-between md:items-center gap-4">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-brandBlue/10 text-brandBlue rounded-xl">
            <BarChart3 size={28} />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900 tracking-tight">Analytics & Reports</h1>
            <p className="text-gray-500 text-sm mt-1">Livestock health intelligence, disease trends and surveillance reports</p>
          </div>
        </div>
        <button onClick={() => setShowReportModal(true)} className="px-5 py-2.5 bg-brandBlue text-white font-bold rounded-lg shadow-sm hover:bg-blue-700 transition-colors flex items-center gap-2 justify-center">
          <FileText size={20} /> Generate Report
        </button>
      </div>

      <AnalyticsFilters filters={filters} setFilters={setFilters} onApply={handleApply} onReset={handleReset} />

      {loading || !data ? (
        <div className="space-y-6 opacity-50 pointer-events-none">
           <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              {[1,2,3,4,5,6,7,8].map(i => <div key={i} className="bg-white h-[120px] rounded-xl border border-gray-200 animate-pulse"></div>)}
           </div>
           <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="bg-white h-[350px] rounded-xl border border-gray-200 animate-pulse"></div>
              <div className="bg-white h-[350px] rounded-xl border border-gray-200 animate-pulse"></div>
           </div>
        </div>
      ) : (
        <>
           <AnalyticsKPIs kpis={data.summary} />
           
           <InsightsPanel insights={data.insights} />

           <AnalyticsCharts trends={data.diseaseTrends} distribution={data.diseaseDistribution} labData={data.laboratoryAnalytics} />

           <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
              <div className="lg:col-span-2">
                 <DistrictTable data={data.districtAnalytics} />
              </div>
              <div className="lg:col-span-1 space-y-6">
                 <GISSummaryCard data={data} />
                 <OutbreakCard data={data} />
                 <VaccinationLabCard data={data} />
              </div>
           </div>
           
           {/* Quick Reports Section */}
           <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200 mb-6">
              <h3 className="text-lg font-bold text-gray-900 mb-4">Quick Reports</h3>
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
                 {["Daily Surveillance", "Weekly Disease", "Monthly Summary", "High-Risk Districts", "Vaccination Coverage", "Outbreak Status"].map(rep => (
                    <button key={rep} onClick={() => setShowReportModal(true)} className="p-4 bg-gray-50 border border-gray-200 rounded-lg text-sm font-medium text-gray-700 hover:bg-blue-50 hover:text-brandBlue hover:border-blue-200 transition-colors flex flex-col items-center text-center gap-2">
                       <Download size={20} className="text-gray-400" />
                       {rep}
                    </button>
                 ))}
              </div>
           </div>
        </>
      )}

      {showReportModal && <ReportGeneratorModal filters={filters} onClose={() => setShowReportModal(false)} />}
    </div>
  );
}

