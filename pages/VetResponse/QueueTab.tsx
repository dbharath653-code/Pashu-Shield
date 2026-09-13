import { useState } from "react";
import { useVetResponse } from "../../context/VetResponseContext";
import type { VetCase } from "../../context/VetResponseContext";
import { Search, Filter, ChevronRight } from "lucide-react";

export default function QueueTab({ onViewCase }: { onViewCase: (c: VetCase) => void }) {
  const { cases } = useVetResponse();
  const [search, setSearch] = useState("");

  const filtered = cases.filter(c => 
    c.id.toLowerCase().includes(search.toLowerCase()) || 
    c.animalHerdId.toLowerCase().includes(search.toLowerCase()) ||
    c.location.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden flex flex-col">
      <div className="p-4 border-b border-gray-200 flex justify-between items-center bg-gray-50">
        <div className="relative w-96">
          <Search className="absolute left-3 top-2.5 text-gray-400" size={20} />
          <input 
            type="text" 
            placeholder="Search by Case ID, Animal/Herd, Location..." 
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-brandBlue focus:border-brandBlue"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className="flex gap-2">
          <button className="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 flex items-center gap-2">
            <Filter size={18} /> Filters
          </button>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200 text-xs font-medium text-gray-500 uppercase tracking-wider">
              <th className="px-6 py-4">Case ID</th>
              <th className="px-6 py-4">Priority</th>
              <th className="px-6 py-4">Animal/Herd</th>
              <th className="px-6 py-4">Location</th>
              <th className="px-6 py-4">Status</th>
              <th className="px-6 py-4">Assigned To</th>
              <th className="px-6 py-4">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {filtered.map((c) => (
              <tr key={c.id} className="hover:bg-gray-50 transition-colors cursor-pointer" onClick={() => onViewCase(c)}>
                <td className="px-6 py-4 whitespace-nowrap font-medium text-gray-900">{c.id}</td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`px-2 py-1 inline-flex text-xs leading-5 font-bold rounded-full 
                    ${c.priority === "CRITICAL" ? "bg-red-100 text-red-800" : 
                      c.priority === "HIGH" ? "bg-orange-100 text-orange-800" : 
                      c.priority === "MEDIUM" ? "bg-yellow-100 text-yellow-800" : "bg-green-100 text-green-800"}`}>
                    {c.priority}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{c.animalHerdId}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{c.location}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                  {c.status}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {c.assignedVet || <span className="text-gray-400 italic">Unassigned</span>}
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
                <td colSpan={7} className="px-6 py-8 text-center text-gray-500">No cases found.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

