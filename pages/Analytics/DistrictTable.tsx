import { useState } from "react";
import type { DistrictStat } from "../../services/AnalyticsService";
import { Search, Download, ArrowUpDown, ChevronLeft, ChevronRight } from "lucide-react";

interface Props {
  data: DistrictStat[];
}

export default function DistrictTable({ data }: Props) {
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const rowsPerPage = 5;

  const filtered = data.filter(d => d.district.toLowerCase().includes(search.toLowerCase()));
  const paginated = filtered.slice((page - 1) * rowsPerPage, page * rowsPerPage);
  const totalPages = Math.ceil(filtered.length / rowsPerPage);

  const getRiskBadge = (level: string) => {
    switch (level) {
      case "CRITICAL": return "bg-red-100 text-red-800 border-red-200";
      case "HIGH": return "bg-orange-100 text-orange-800 border-orange-200";
      case "MEDIUM": return "bg-yellow-100 text-yellow-800 border-yellow-200";
      case "LOW": return "bg-green-100 text-green-800 border-green-200";
      default: return "bg-gray-100 text-gray-800";
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden mb-6">
       <div className="p-5 border-b border-gray-200 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <h3 className="text-lg font-bold text-gray-900">District-Wise Analytics</h3>
          
          <div className="flex items-center gap-3 w-full sm:w-auto">
             <div className="relative flex-1 sm:w-64">
                <Search className="absolute left-3 top-2.5 text-gray-400" size={18} />
                <input 
                  type="text" 
                  placeholder="Search districts..." 
                  value={search}
                  onChange={e => { setSearch(e.target.value); setPage(1); }}
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:ring-brandBlue focus:border-brandBlue"
                />
             </div>
             <button className="p-2 border border-gray-300 rounded-lg text-gray-600 hover:bg-gray-50 flex items-center gap-2" title="Export CSV">
                <Download size={18} />
             </button>
          </div>
       </div>
       
       <div className="overflow-x-auto">
          <table className="w-full text-left text-sm whitespace-nowrap">
             <thead className="bg-gray-50 text-gray-600 font-medium border-b border-gray-200">
                <tr>
                   <th className="px-6 py-4 cursor-pointer hover:bg-gray-100"><div className="flex items-center gap-1">District <ArrowUpDown size={14}/></div></th>
                   <th className="px-6 py-4 cursor-pointer hover:bg-gray-100"><div className="flex items-center gap-1">Total Cases <ArrowUpDown size={14}/></div></th>
                   <th className="px-6 py-4 cursor-pointer hover:bg-gray-100"><div className="flex items-center gap-1">Active <ArrowUpDown size={14}/></div></th>
                   <th className="px-6 py-4 cursor-pointer hover:bg-gray-100"><div className="flex items-center gap-1">Recovered <ArrowUpDown size={14}/></div></th>
                   <th className="px-6 py-4 cursor-pointer hover:bg-gray-100"><div className="flex items-center gap-1">Mortality <ArrowUpDown size={14}/></div></th>
                   <th className="px-6 py-4 cursor-pointer hover:bg-gray-100"><div className="flex items-center gap-1">Vax Cov. <ArrowUpDown size={14}/></div></th>
                   <th className="px-6 py-4">Risk Level</th>
                </tr>
             </thead>
             <tbody className="divide-y divide-gray-100">
                {paginated.length > 0 ? paginated.map(row => (
                   <tr key={row.district} className="hover:bg-gray-50 transition-colors">
                      <td className="px-6 py-4 font-bold text-gray-900">{row.district}</td>
                      <td className="px-6 py-4 text-gray-600">{row.totalCases.toLocaleString()}</td>
                      <td className="px-6 py-4 text-gray-600">{row.activeCases.toLocaleString()}</td>
                      <td className="px-6 py-4 text-gray-600">{row.recovered.toLocaleString()}</td>
                      <td className="px-6 py-4 text-gray-600 font-medium">{row.mortality.toLocaleString()}</td>
                      <td className="px-6 py-4">
                         <div className="flex items-center gap-2">
                            <div className="w-16 h-2 bg-gray-200 rounded-full overflow-hidden">
                               <div className="h-full bg-brandBlue" style={{ width: `${row.vaccinationCoverage}%` }}></div>
                            </div>
                            <span className="text-xs text-gray-500">{row.vaccinationCoverage}%</span>
                         </div>
                      </td>
                      <td className="px-6 py-4">
                         <span className={`px-2 py-1 text-xs font-bold rounded-full border ${getRiskBadge(row.riskLevel)}`}>
                            {row.riskLevel}
                         </span>
                      </td>
                   </tr>
                )) : (
                   <tr>
                      <td colSpan={7} className="px-6 py-8 text-center text-gray-500">No districts match your search.</td>
                   </tr>
                )}
             </tbody>
          </table>
       </div>
       
       <div className="px-6 py-4 border-t border-gray-200 flex justify-between items-center bg-gray-50">
          <div className="text-sm text-gray-500">
             Showing {Math.min(filtered.length, (page - 1) * rowsPerPage + 1)} to {Math.min(filtered.length, page * rowsPerPage)} of {filtered.length} entries
          </div>
          <div className="flex gap-1">
             <button disabled={page === 1} onClick={() => setPage(p => p - 1)} className="p-1 border border-gray-300 rounded bg-white text-gray-600 hover:bg-gray-50 disabled:opacity-50">
                <ChevronLeft size={18} />
             </button>
             <button disabled={page >= totalPages} onClick={() => setPage(p => p + 1)} className="p-1 border border-gray-300 rounded bg-white text-gray-600 hover:bg-gray-50 disabled:opacity-50">
                <ChevronRight size={18} />
             </button>
          </div>
       </div>
    </div>
  );
}
