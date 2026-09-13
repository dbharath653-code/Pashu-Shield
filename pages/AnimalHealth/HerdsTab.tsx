import React, { useState } from "react";
import { useAnimalHealth } from "../../context/AnimalHealthContext";
import { Search, Filter, Plus, ChevronRight } from "lucide-react";

export default function HerdsTab({ onRegister }: { onRegister: () => void }) {
  const { herds } = useAnimalHealth();
  const [search, setSearch] = useState("");

  const filteredHerds = herds.filter(h => 
    h.id.toLowerCase().includes(search.toLowerCase()) || 
    h.ownerName.toLowerCase().includes(search.toLowerCase()) ||
    h.village.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden flex flex-col">
      <div className="p-4 border-b border-gray-200 flex justify-between items-center bg-gray-50">
        <div className="relative w-96">
          <Search className="absolute left-3 top-2.5 text-gray-400" size={20} />
          <input 
            type="text" 
            placeholder="Search by Herd ID, Owner, Village..." 
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-brandBlue focus:border-brandBlue"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className="flex gap-2">
          <button className="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 flex items-center gap-2">
            <Filter size={18} /> Filters
          </button>
          <button onClick={onRegister} className="px-4 py-2 bg-brandBlue text-white rounded-lg hover:bg-brandBlue/90 flex items-center gap-2">
            <Plus size={18} /> Register Herd
          </button>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200 text-xs font-medium text-gray-500 uppercase tracking-wider">
              <th className="px-6 py-4">Herd ID</th>
              <th className="px-6 py-4">Owner</th>
              <th className="px-6 py-4">Location</th>
              <th className="px-6 py-4">Species</th>
              <th className="px-6 py-4">Total Animals</th>
              <th className="px-6 py-4">Health Status</th>
              <th className="px-6 py-4">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {filteredHerds.map((herd) => (
              <tr key={herd.id} className="hover:bg-gray-50 transition-colors cursor-pointer">
                <td className="px-6 py-4 whitespace-nowrap font-medium text-gray-900">{herd.id}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{herd.ownerName}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{herd.village}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{herd.species}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{herd.totalAnimals}</td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full 
                    ${herd.healthStatus === "Low Risk" ? "bg-green-100 text-green-800" : 
                      herd.healthStatus === "High Risk" ? "bg-red-100 text-red-800" : 
                      "bg-yellow-100 text-yellow-800"}`}>
                    {herd.healthStatus}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                  <button onClick={(e) => { e.stopPropagation(); alert(`Viewing Herd Profile for ${herd.id}\nSpecies: ${herd.species}\nAnimals: ${herd.totalAnimals}\nStatus: ${herd.healthStatus}`); }} className="text-brandBlue hover:text-blue-900 flex items-center gap-1">
                    View <ChevronRight size={16} />
                  </button>
                </td>
              </tr>
            ))}
            {filteredHerds.length === 0 && (
              <tr>
                <td colSpan={7} className="px-6 py-8 text-center text-gray-500">No herds found in local database.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

