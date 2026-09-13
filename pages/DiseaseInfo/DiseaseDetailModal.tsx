import type { Disease } from "../../services/DiseaseService";
import { useMultilingual } from "../../context/MultilingualContext";
import { useNavigate } from "react-router-dom";
import { X, Volume2, ShieldAlert, AlertTriangle, FileText, Map as MapIcon, Syringe, Bug, Activity } from "lucide-react";

interface Props {
  disease: Disease;
  language: string;
  t: (key: string) => string;
  onClose: () => void;
}

export default function DiseaseDetailModal({ disease, language, t, onClose }: Props) {
  const navigate = useNavigate();
  const { speak } = useMultilingual();

  const name = language === "mr" && disease.name_mr ? disease.name_mr : disease.name_en;
  const description = language === "mr" && disease.description_mr ? disease.description_mr : disease.description_en;
  const symptoms = language === "mr" && disease.symptoms_mr ? disease.symptoms_mr : disease.symptoms_en;
  const transmission = language === "mr" && disease.transmission_mr ? disease.transmission_mr : disease.transmission_en;
  const prevention = language === "mr" && disease.prevention_mr ? disease.prevention_mr : disease.prevention_en;

  const handleSpeak = () => {
     const textToRead = `${name}. ${description} Symptoms include ${symptoms.join(", ")}.`;
     speak(textToRead, language);
  };

  const navParams = `?disease=${encodeURIComponent(disease.aliases[0] || disease.name_en)}`;

  return (
    <div className="fixed inset-0 bg-black/60 z-50 flex justify-center items-center p-4">
      <div className="bg-white rounded-2xl w-full max-w-5xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
        
        {/* Header */}
        <div className="bg-brandBlue text-white p-6 flex justify-between items-start">
           <div>
              <div className="flex items-center gap-3 mb-2">
                 <h2 className="text-3xl font-bold">{name}</h2>
                 <button onClick={handleSpeak} className="p-2 bg-white/20 hover:bg-white/30 rounded-full transition-colors" title="Read Aloud">
                    <Volume2 size={20} />
                 </button>
              </div>
              <p className="text-blue-100 font-medium italic">{disease.scientificName}</p>
           </div>
           <button onClick={onClose} className="p-2 bg-white/10 hover:bg-white/20 rounded-xl transition-colors">
              <X size={24} />
           </button>
        </div>

        {/* Action Bar */}
        <div className="bg-blue-50 p-4 border-b border-blue-100 flex flex-wrap gap-3">
           <button onClick={() => navigate(`/reporting${navParams}`)} className="px-4 py-2 bg-red-600 text-white font-medium rounded-lg hover:bg-red-700 flex items-center gap-2">
              <AlertTriangle size={18} /> {t("di.reportCase")}
           </button>
           <button onClick={() => navigate(`/surveillance${navParams}`)} className="px-4 py-2 bg-white border border-blue-200 text-blue-800 font-medium rounded-lg hover:bg-blue-100 flex items-center gap-2">
              <Activity size={18} /> {t("di.viewSurveillance")}
           </button>
           <button onClick={() => navigate(`/gis${navParams}`)} className="px-4 py-2 bg-white border border-blue-200 text-blue-800 font-medium rounded-lg hover:bg-blue-100 flex items-center gap-2">
              <MapIcon size={18} /> {t("di.viewMap")}
           </button>
           <button onClick={() => navigate(`/vaccination${navParams}`)} className="px-4 py-2 bg-white border border-blue-200 text-blue-800 font-medium rounded-lg hover:bg-blue-100 flex items-center gap-2">
              <Syringe size={18} /> {t("di.vaccinationBtn")}
           </button>
        </div>

        {/* Content Scroll Area */}
        <div className="flex-1 overflow-y-auto p-6 bg-gray-50">
           
           {/* WARNING BANNER */}
           <div className="bg-yellow-50 border-l-4 border-yellow-500 p-4 rounded-r-lg mb-8 flex gap-3 shadow-sm">
              <ShieldAlert className="text-yellow-600 shrink-0" size={24} />
              <p className="text-sm font-medium text-yellow-800">{t("di.warning")}</p>
           </div>

           <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              {/* Left Column: Metadata */}
              <div className="md:col-span-1 space-y-6">
                 <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
                    <h4 className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-4 border-b pb-2">Quick Facts</h4>
                    <div className="space-y-4">
                       <div>
                          <span className="block text-xs text-gray-500 mb-1">Category</span>
                          <span className="font-medium text-gray-900">{disease.category}</span>
                       </div>
                       <div>
                          <span className="block text-xs text-gray-500 mb-1">Risk Level</span>
                          <span className={`font-bold ${disease.riskLevel === "Critical" ? "text-red-600" : "text-orange-600"}`}>{disease.riskLevel}</span>
                       </div>
                       <div>
                          <span className="block text-xs text-gray-500 mb-1">Affected Species</span>
                          <div className="flex flex-wrap gap-1">
                             {disease.affectedSpecies.map(s => <span key={s} className="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded-md">{s}</span>)}
                          </div>
                       </div>
                    </div>
                 </div>
              </div>

              {/* Right Column: Details */}
              <div className="md:col-span-2 space-y-8">
                 <section>
                    <h3 className="text-xl font-bold text-gray-900 mb-3 flex items-center gap-2">
                       <FileText className="text-brandBlue" /> {t("di.overview")}
                    </h3>
                    <p className="text-gray-700 leading-relaxed bg-white p-5 rounded-xl border border-gray-200 shadow-sm">{description}</p>
                 </section>

                 <section>
                    <h3 className="text-xl font-bold text-gray-900 mb-3 flex items-center gap-2">
                       <Activity className="text-red-500" /> {t("di.symptoms")}
                    </h3>
                    <ul className="grid grid-cols-1 sm:grid-cols-2 gap-3 bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
                       {symptoms.map((sym, idx) => (
                          <li key={idx} className="flex items-start gap-2">
                             <div className="w-2 h-2 rounded-full bg-red-400 mt-2 shrink-0"></div>
                             <span className="text-gray-700 font-medium">{sym}</span>
                          </li>
                       ))}
                    </ul>
                 </section>

                 <section>
                    <h3 className="text-xl font-bold text-gray-900 mb-3 flex items-center gap-2">
                       <Bug className="text-orange-500" /> {t("di.transmission")}
                    </h3>
                    <p className="text-gray-700 leading-relaxed bg-white p-5 rounded-xl border border-gray-200 shadow-sm">{transmission}</p>
                 </section>

                 <section>
                    <h3 className="text-xl font-bold text-gray-900 mb-3 flex items-center gap-2">
                       <ShieldAlert className="text-green-500" /> {t("di.prevention")}
                    </h3>
                    <p className="text-gray-700 leading-relaxed bg-white p-5 rounded-xl border border-gray-200 shadow-sm">{prevention}</p>
                 </section>

              </div>
           </div>
        </div>

      </div>
    </div>
  );
}
