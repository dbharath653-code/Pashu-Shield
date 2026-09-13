import React, { useState } from "react";
import { useVaccination } from "../../context/VaccinationContext";
import { Search, Filter, QrCode } from "lucide-react";

export default function VaccinationRegistry() {
  const { vaccinations } = useVaccination();
  const [search, setSearch] = useState("");

  const filtered = vaccinations.filter(v => 
    v.id.toLowerCase().includes(search.toLowerCase()) || 
    v.animalId.toLowerCase().includes(search.toLowerCase()) ||
    v.disease.toLowerCase().includes(search.toLowerCase()) ||
    v.vaccine.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden flex flex-col">
      <div className="p-4 border-b border-gray-200 flex justify-between items-center bg-gray-50">
        <div className="relative w-96">
          <Search className="absolute left-3 top-2.5 text-gray-400" size={20} />
          <input 
            type="text" 
            placeholder="Search by ID, Animal, Disease, Vaccine..." 
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-brandBlue focus:border-brandBlue"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className="flex gap-2">
          <button className="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 flex items-center gap-2 text-sm font-medium">
            <Filter size={18} /> Filters
          </button>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200 text-xs font-medium text-gray-500 uppercase tracking-wider">
              <th className="px-6 py-4">Vaccination ID</th>
              <th className="px-6 py-4">Animal ID</th>
              <th className="px-6 py-4">Disease / Vaccine</th>
              <th className="px-6 py-4">Date Administered</th>
              <th className="px-6 py-4">Next Booster Due</th>
              <th className="px-6 py-4">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {filtered.map((v) => (
              <tr key={v.id} className="hover:bg-gray-50 transition-colors">
                <td className="px-6 py-4 whitespace-nowrap font-medium text-gray-900">{v.id}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-bold text-gray-800">{v.animalId}</td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <p className="text-sm font-medium text-gray-800">{v.disease}</p>
                  <p className="text-xs text-gray-500">{v.vaccine} (Batch {v.batchNumber})</p>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">
                  {new Date(v.vaccinationDate).toLocaleDateString()}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`px-2 py-1 inline-flex text-xs leading-5 font-bold rounded-full 
                    ${new Date(v.nextDueDate) < new Date() ? "bg-red-100 text-red-800" : "bg-green-100 text-green-800"}`}>
                    {new Date(v.nextDueDate).toLocaleDateString()}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                  <button onClick={() => { alert(`Generating Certificate for ${v.id}...`); window.print(); }} className="text-brandBlue hover:text-blue-900 flex items-center gap-1">
                    <QrCode size={16} /> Certificate
                  </button>
                </td>
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={6} className="px-6 py-8 text-center text-gray-500">No vaccination records found.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

