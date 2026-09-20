import { useState } from "react";
import { useAnimalHealth } from "../../context/AnimalHealthContext";
import { Search, Filter, Plus, ChevronRight } from "lucide-react";

export default function AnimalsTab({ onRegister }: { onRegister: () => void }) {
  const { animals } = useAnimalHealth();
  const [search, setSearch] = useState("");

  const filteredAnimals = animals.filter(a => 
    a.id.toLowerCase().includes(search.toLowerCase()) || 
    a.ownerName.toLowerCase().includes(search.toLowerCase()) ||
    a.village.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden flex flex-col">
      <div className="p-4 border-b border-gray-200 flex flex-col sm:flex-row justify-between items-stretch sm:items-center gap-3 bg-gray-50">
        <div className="relative flex-1 sm:w-96">
          <Search className="absolute left-3 top-2.5 text-gray-400" size={18} />
          <input 
            type="text" 
            placeholder="Search by Animal ID, Owner, Village..." 
            className="w-full pl-9 pr-4 py-2 border border-gray-300 rounded-lg text-xs sm:text-sm focus:ring-brandBlue focus:border-brandBlue"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className="flex gap-2">
          <button className="px-3 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 flex items-center justify-center gap-1.5 text-xs sm:text-sm font-medium touch-manipulation min-h-[38px]">
            <Filter size={16} /> Filters
          </button>
          <button onClick={onRegister} className="px-3.5 py-2 bg-brandBlue text-white rounded-lg hover:bg-brandBlue/90 flex items-center justify-center gap-1.5 text-xs sm:text-sm font-bold touch-manipulation min-h-[38px] shadow-xs">
            <Plus size={16} /> Register Animal
          </button>
        </div>
      </div>

      <div className="overflow-x-auto custom-scrollbar">
        <table className="w-full text-left border-collapse min-w-[640px]">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200 text-xs font-medium text-gray-500 uppercase tracking-wider">
              <th className="px-6 py-4">Animal ID</th>
              <th className="px-6 py-4">Species/Breed</th>
              <th className="px-6 py-4">Owner</th>
              <th className="px-6 py-4">Location</th>
              <th className="px-6 py-4">Health Status</th>
              <th className="px-6 py-4">Risk</th>
              <th className="px-6 py-4">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {filteredAnimals.map((animal) => (
              <tr key={animal.id} className="hover:bg-gray-50 transition-colors cursor-pointer">
                <td className="px-6 py-4 whitespace-nowrap font-medium text-gray-900">{animal.id}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{animal.species} • {animal.breed}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{animal.ownerName}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{animal.village}, {animal.district}</td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full 
                    ${animal.healthStatus === "Healthy" ? "bg-green-100 text-green-800" : 
                      animal.healthStatus === "Diseased" ? "bg-red-100 text-red-800" : 
                      "bg-yellow-100 text-yellow-800"}`}>
                    {animal.healthStatus}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                  <span className={animal.riskScore > 50 ? "text-red-600" : "text-green-600"}>{animal.riskScore}</span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                  <button onClick={(e) => { e.stopPropagation(); alert(`Viewing Animal Profile for ${animal.id}\nSpecies: ${animal.species}\nStatus: ${animal.healthStatus}\nRisk: ${animal.riskScore}`); }} className="text-brandBlue hover:text-blue-900 flex items-center gap-1">
                    View <ChevronRight size={16} />
                  </button>
                </td>
              </tr>
            ))}
            {filteredAnimals.length === 0 && (
              <tr>
                <td colSpan={7} className="px-6 py-8 text-center text-gray-500">No animals found in local database.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

