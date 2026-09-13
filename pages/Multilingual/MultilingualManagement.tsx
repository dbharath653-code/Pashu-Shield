import { useMultilingual } from "../../context/MultilingualContext";
import { Languages } from "lucide-react";
import LanguageSettings from "./LanguageSettings";
import VoiceFieldReport from "./VoiceFieldReport";
import VoiceAssistant from "./VoiceAssistant";

export default function MultilingualManagement() {
  const { t } = useMultilingual();

  return (
    <div className="flex flex-col h-full bg-gray-50 p-2 md:p-4 overflow-y-auto">
      {/* Page Header */}
      <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200 mb-6">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-brandBlue/10 text-brandBlue rounded-xl">
            <Languages size={28} />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900 uppercase tracking-tight">
               {t("module.title")}
            </h1>
            <p className="text-gray-500 text-sm mt-1">{t("module.subtitle")}</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-3">
           <LanguageSettings />
        </div>
        
        <div className="lg:col-span-2">
           <VoiceFieldReport />
        </div>

        <div className="lg:col-span-1">
           <VoiceAssistant />
        </div>
      </div>
    </div>
  );
}

