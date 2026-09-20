import { useState } from "react";
import { useLab } from "../../context/LabContext";
import type { LabSample } from "../../context/LabContext";
import { Search, Filter, ChevronRight } from "lucide-react";

export default function SampleRegistry({ onViewSample }: { onViewSample: (s: LabSample) => void }) {
  const { samples } = useLab();
  const [search, setSearch] = useState("");

  const filtered = samples.filter(s => 
    s.id.toLowerCase().includes(search.toLowerCase()) || 
    (s.caseId && s.caseId.toLowerCase().includes(search.toLowerCase())) ||
    (s.animalId && s.animalId.toLowerCase().includes(search.toLowerCase())) ||
    s.diseaseSuspected.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden flex flex-col">
      <div className="p-4 border-b border-gray-200 flex flex-col sm:flex-row justify-between items-stretch sm:items-center gap-3 bg-gray-50">
        <div className="relative flex-1 sm:w-96">
          <Search className="absolute left-3 top-2.5 text-gray-400" size={18} />
          <input 
            type="text" 
            placeholder="Search Sample ID, Case ID, Disease..." 
            className="w-full pl-9 pr-4 py-2 border border-gray-300 rounded-lg text-xs sm:text-sm focus:ring-brandBlue focus:border-brandBlue"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className="flex gap-2">
          <button className="px-3.5 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 flex items-center justify-center gap-1.5 text-xs sm:text-sm font-medium touch-manipulation min-h-[38px]">
            <Filter size={16} /> Filters
          </button>
        </div>
      </div>

      <div className="overflow-x-auto custom-scrollbar">
        <table className="w-full text-left border-collapse min-w-[640px]">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200 text-xs font-medium text-gray-500 uppercase tracking-wider">
              <th className="px-6 py-4">Sample ID</th>
              <th className="px-6 py-4">Priority</th>
              <th className="px-6 py-4">Type</th>
              <th className="px-6 py-4">Suspected Disease</th>
              <th className="px-6 py-4">Location</th>
              <th className="px-6 py-4">Status</th>
              <th className="px-6 py-4">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {filtered.map((s) => (
              <tr key={s.id} className="hover:bg-gray-50 transition-colors cursor-pointer" onClick={() => onViewSample(s)}>
                <td className="px-6 py-4 whitespace-nowrap font-medium text-gray-900">{s.id}</td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`px-2 py-1 inline-flex text-xs leading-5 font-bold rounded-full 
                    ${s.priority === "Critical" ? "bg-red-100 text-red-800" : 
                      s.priority === "Urgent" ? "bg-orange-100 text-orange-800" : 
                      "bg-gray-100 text-gray-800"}`}>
                    {s.priority}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{s.species} {s.sampleType}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{s.diseaseSuspected}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{s.district}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                  {s.status}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                  <button className="text-brandBlue hover:text-blue-900 flex items-center gap-1">
                    View <ChevronRight size={16} />
                  </button>
                </td>
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={7} className="px-6 py-8 text-center text-gray-500">No samples found.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

