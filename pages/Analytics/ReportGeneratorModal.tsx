import React, { useState } from "react";
import { AnalyticsService } from "../../services/AnalyticsService";
import type { FilterOptions } from "../../services/AnalyticsService";
import { X, FileText, Download, Loader2 } from "lucide-react";

interface Props {
  filters: FilterOptions;
  onClose: () => void;
}

export default function ReportGeneratorModal({ filters, onClose }: Props) {
  const [reportType, setReportType] = useState("Monthly Summary");
  const [format, setFormat] = useState("PDF");
  const [isGenerating, setIsGenerating] = useState(false);

  const handleGenerate = async () => {
    setIsGenerating(true);
    try {
      const filename = await AnalyticsService.generateReport(filters, reportType, format);
      // Mock download
      const element = document.createElement("a");
      const file = new Blob(["Mock report content for " + filename], { type: "text/plain" });
      element.href = URL.createObjectURL(file);
      element.download = filename;
      document.body.appendChild(element);
      element.click();
      document.body.removeChild(element);
      onClose();
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex justify-center items-center p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg overflow-hidden">
         <div className="bg-brandBlue text-white p-5 flex justify-between items-center">
            <h3 className="text-xl font-bold flex items-center gap-2"><FileText /> Generate Report</h3>
            <button onClick={onClose} className="text-white/70 hover:text-white transition-colors">
               <X size={24} />
            </button>
         </div>

         <div className="p-6 space-y-5">
            <div>
               <label className="block text-sm font-medium text-gray-700 mb-2">Report Type</label>
               <select value={reportType} onChange={e => setReportType(e.target.value)} className="w-full border border-gray-300 rounded-lg p-3 focus:ring-brandBlue focus:border-brandBlue">
                  <option>Disease Surveillance Report</option>
                  <option>District Health Report</option>
                  <option>Outbreak Report</option>
                  <option>Vaccination Report</option>
                  <option>Laboratory Report</option>
                  <option>Monthly Summary</option>
                  <option>Custom Report</option>
               </select>
            </div>

            <div>
               <label className="block text-sm font-medium text-gray-700 mb-2">Format</label>
               <div className="flex gap-4">
                  {["PDF", "Excel", "CSV"].map(fmt => (
                     <label key={fmt} className="flex items-center gap-2 cursor-pointer">
                        <input type="radio" name="format" value={fmt} checked={format === fmt} onChange={e => setFormat(e.target.value)} className="text-brandBlue focus:ring-brandBlue" />
                        <span className="text-sm font-medium text-gray-700">{fmt}</span>
                     </label>
                  ))}
               </div>
            </div>

            <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
               <h4 className="text-xs font-bold text-gray-500 uppercase mb-2">Applied Filters</h4>
               <ul className="text-sm text-gray-700 space-y-1">
                  <li><strong>Date Range:</strong> {filters.dateRange}</li>
                  <li><strong>District:</strong> {filters.district}</li>
                  <li><strong>Species:</strong> {filters.species}</li>
                  <li><strong>Disease:</strong> {filters.disease}</li>
               </ul>
            </div>
         </div>

         <div className="p-5 border-t border-gray-200 flex justify-end gap-3 bg-gray-50">
            <button onClick={onClose} className="px-5 py-2.5 text-gray-600 font-medium hover:bg-gray-200 rounded-lg transition-colors">
               Cancel
            </button>
            <button onClick={handleGenerate} disabled={isGenerating} className="px-5 py-2.5 bg-brandBlue text-white font-bold rounded-lg hover:bg-blue-700 transition-colors flex items-center gap-2 shadow-sm disabled:opacity-70">
               {isGenerating ? <Loader2 size={20} className="animate-spin" /> : <Download size={20} />}
               {isGenerating ? "Generating..." : "Generate Report"}
            </button>
         </div>
      </div>
    </div>
  );
}

