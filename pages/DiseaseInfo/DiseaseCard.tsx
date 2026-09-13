import type { Disease } from "../../services/DiseaseService";
import { Info, Syringe, Virus } from "lucide-react";

interface Props {
  disease: Disease;
  language: string;
  t: (key: string) => string;
  onViewDetails: () => void;
}

export default function DiseaseCard({ disease, language, t, onViewDetails }: Props) {
  const name = language === "mr" && disease.name_mr ? disease.name_mr : disease.name_en;
  const description = language === "mr" && disease.description_mr ? disease.description_mr : disease.description_en;

  const riskColors = {
    Low: "bg-green-100 text-green-800 border-green-200",
    Moderate: "bg-yellow-100 text-yellow-800 border-yellow-200",
    High: "bg-orange-100 text-orange-800 border-orange-200",
    Critical: "bg-red-100 text-red-800 border-red-200 animate-pulse"
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden flex flex-col hover:shadow-md transition-shadow">
      <div className="p-5 flex-1">
        <div className="flex justify-between items-start mb-3">
           <h3 className="text-lg font-bold text-gray-900 line-clamp-2">{name}</h3>
           <span className={`px-2 py-1 text-xs font-bold rounded-full border ${riskColors[disease.riskLevel]}`}>
             {disease.riskLevel}
           </span>
        </div>
        
        <p className="text-xs text-gray-500 italic mb-3">{disease.scientificName}</p>
        
        <div className="flex flex-wrap gap-2 mb-4">
           <span className="px-2 py-1 bg-gray-100 text-gray-700 text-xs font-medium rounded-lg">
             {disease.category}
           </span>
           {disease.zoonotic && (
             <span className="px-2 py-1 bg-purple-100 text-purple-800 text-xs font-medium rounded-lg flex items-center gap-1">
               <Virus size={12}/> Zoonotic
             </span>
           )}
           {disease.vaccinePreventable && (
             <span className="px-2 py-1 bg-blue-100 text-blue-800 text-xs font-medium rounded-lg flex items-center gap-1">
               <Syringe size={12}/> Preventable
             </span>
           )}
        </div>

        <p className="text-sm text-gray-600 line-clamp-3 mb-4">{description}</p>
        
        <div className="text-xs text-gray-500">
           <strong>Species:</strong> {disease.affectedSpecies.join(", ")}
        </div>
      </div>
      
      <div className="p-4 border-t border-gray-100 bg-gray-50">
        <button 
           onClick={onViewDetails}
           className="w-full py-2 bg-white border border-gray-300 text-gray-700 font-medium rounded-lg hover:bg-gray-50 hover:text-brandBlue hover:border-brandBlue transition-colors flex justify-center items-center gap-2"
        >
           <Info size={18} />
           {t("di.viewDetails")}
        </button>
      </div>
    </div>
  );
}
