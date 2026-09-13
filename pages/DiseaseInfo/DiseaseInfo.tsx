import React, { useState, useEffect } from "react";
import { useMultilingual } from "../../context/MultilingualContext";
import { DiseaseService } from "../../services/DiseaseService";
import type { Disease } from "../../services/DiseaseService";
import { Info, Search, ShieldAlert, Activity, Filter, Syringe, Virus, MapPin, X } from "lucide-react";
import DiseaseDetailModal from "./DiseaseDetailModal";
import DiseaseCard from "./DiseaseCard";

export default function DiseaseInfo() {
  const { t, language } = useMultilingual();
  const [diseases, setDiseases] = useState<Disease[]>([]);
  const [loading, setLoading] = useState(true);
  
  // Filters
  const [search, setSearch] = useState("");
  const [species, setSpecies] = useState("All");
  const [category, setCategory] = useState("All");
  const [riskLevel, setRiskLevel] = useState("All");
  
  const [selectedDisease, setSelectedDisease] = useState<Disease | null>(null);

  useEffect(() => {
    loadDiseases();
  }, [search, species, category, riskLevel]);

  const loadDiseases = async () => {
    setLoading(true);
    try {
      const data = await DiseaseService.searchDiseases(search, category, riskLevel, species);
      setDiseases(data);
    } finally {
      setLoading(false);
    }
  };

  const clearFilters = () => {
    setSearch("");
    setSpecies("All");
    setCategory("All");
    setRiskLevel("All");
  };

  // Stats for the summary cards
  const total = diseases.length;
  const highRisk = diseases.filter(d => d.riskLevel === "High" || d.riskLevel === "Critical").length;
  const zoonotic = diseases.filter(d => d.zoonotic).length;
  const vaccinePreventable = diseases.filter(d => d.vaccinePreventable).length;

  return (
    <div className="flex flex-col h-full bg-gray-50 p-2 md:p-4 overflow-y-auto">
      {/* Header */}
      <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200 mb-6 flex flex-col md:flex-row justify-between md:items-center gap-4">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-brandBlue/10 text-brandBlue rounded-xl">
            <Info size={28} />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900 tracking-tight">
               {t("di.title")}
            </h1>
            <p className="text-gray-500 text-sm mt-1">{t("di.subtitle")}</p>
          </div>
        </div>
      </div>

      {/* Summary Dashboard */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white p-4 rounded-xl shadow-sm border border-gray-200">
           <div className="text-gray-500 text-sm font-medium">{t("di.total")}</div>
           <div className="text-3xl font-bold text-gray-900 mt-1">{total}</div>
        </div>
        <div className="bg-white p-4 rounded-xl shadow-sm border border-gray-200">
           <div className="text-gray-500 text-sm font-medium flex items-center gap-1"><ShieldAlert size={16} className="text-red-500"/> {t("di.highRisk")}</div>
           <div className="text-3xl font-bold text-red-600 mt-1">{highRisk}</div>
        </div>
        <div className="bg-white p-4 rounded-xl shadow-sm border border-gray-200">
           <div className="text-gray-500 text-sm font-medium flex items-center gap-1"><Virus size={16} className="text-yellow-600"/> {t("di.zoonotic")}</div>
           <div className="text-3xl font-bold text-yellow-700 mt-1">{zoonotic}</div>
        </div>
        <div className="bg-white p-4 rounded-xl shadow-sm border border-gray-200">
           <div className="text-gray-500 text-sm font-medium flex items-center gap-1"><Syringe size={16} className="text-green-600"/> {t("di.vaccine")}</div>
           <div className="text-3xl font-bold text-green-700 mt-1">{vaccinePreventable}</div>
        </div>
      </div>

      {/* Filters Bar */}
      <div className="bg-white p-4 rounded-xl shadow-sm border border-gray-200 mb-6 flex flex-col md:flex-row gap-4">
        <div className="flex-1 relative">
           <Search className="absolute left-3 top-2.5 text-gray-400" size={20} />
           <input 
             type="text" 
             placeholder={t("di.search")}
             className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-brandBlue focus:border-brandBlue"
             value={search}
             onChange={e => setSearch(e.target.value)}
           />
        </div>
        
        <select value={species} onChange={e => setSpecies(e.target.value)} className="border border-gray-300 rounded-lg px-4 py-2 bg-white">
           <option value="All">All Species</option>
           <option value="Cattle">Cattle</option>
           <option value="Buffalo">Buffalo</option>
           <option value="Goat">Goat</option>
           <option value="Sheep">Sheep</option>
           <option value="Pig">Pig</option>
           <option value="Poultry">Poultry</option>
        </select>
        
        <select value={category} onChange={e => setCategory(e.target.value)} className="border border-gray-300 rounded-lg px-4 py-2 bg-white">
           <option value="All">All Categories</option>
           <option value="Viral">Viral</option>
           <option value="Bacterial">Bacterial</option>
           <option value="Parasitic">Parasitic</option>
           <option value="Fungal">Fungal</option>
           <option value="Zoonotic">Zoonotic</option>
           <option value="Nutritional">Nutritional</option>
        </select>
        
        <select value={riskLevel} onChange={e => setRiskLevel(e.target.value)} className="border border-gray-300 rounded-lg px-4 py-2 bg-white">
           <option value="All">All Risk Levels</option>
           <option value="Low">Low</option>
           <option value="Moderate">Moderate</option>
           <option value="High">High</option>
           <option value="Critical">Critical</option>
        </select>

        <button onClick={clearFilters} className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg font-medium flex items-center gap-2 transition-colors">
          <X size={18} /> {t("di.clearFilters")}
        </button>
      </div>

      {/* Disease Grid */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 opacity-50">
           {[1,2,3].map(i => (
             <div key={i} className="bg-white h-[300px] rounded-xl border border-gray-200 animate-pulse"></div>
           ))}
        </div>
      ) : diseases.length === 0 ? (
        <div className="bg-white p-12 rounded-xl border border-gray-200 text-center flex flex-col items-center">
           <Filter size={48} className="text-gray-300 mb-4" />
           <h3 className="text-xl font-bold text-gray-700">{t("di.notFound")}</h3>
           <button onClick={clearFilters} className="mt-4 text-brandBlue font-medium hover:underline">
              {t("di.clearFilters")}
           </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
           {diseases.map(disease => (
             <DiseaseCard 
               key={disease.id} 
               disease={disease} 
               language={language}
               onViewDetails={() => setSelectedDisease(disease)} 
               t={t}
             />
           ))}
        </div>
      )}

      {/* Details Modal */}
      {selectedDisease && (
        <DiseaseDetailModal 
           disease={selectedDisease} 
           language={language}
           t={t}
           onClose={() => setSelectedDisease(null)} 
        />
      )}
    </div>
  );
}

