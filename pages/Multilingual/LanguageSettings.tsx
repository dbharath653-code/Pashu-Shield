import { useMultilingual } from "../../context/MultilingualContext";
import { Check, Globe, Mic, Volume2 } from "lucide-react";

export default function LanguageSettings() {
  const { language, setLanguage, t, isSpeechAvailable } = useMultilingual();

  const languages = [
    { code: "en", name: "English", nativeName: "English" },
    { code: "mr", name: "Marathi", nativeName: "मराठी" },
    { code: "hi", name: "Hindi", nativeName: "हिन्दी" },
    { code: "te", name: "Telugu", nativeName: "తెలుగు" },
    { code: "kn", name: "Kannada", nativeName: "ಕನ್ನಡ" },
    { code: "gu", name: "Gujarati", nativeName: "ગુજરાતી" },
    { code: "ta", name: "Tamil", nativeName: "தமிழ்" },
    { code: "bn", name: "Bengali", nativeName: "বাংলা" }
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
           <Globe size={20} className="text-brandBlue"/>
           {t("card.language")}
        </h3>
        <p className="text-sm text-gray-500 mb-6">Select your preferred system language. All navigation, forms, and alerts will translate instantly.</p>
        
        <div className="grid grid-cols-2 gap-3">
          {languages.map(lang => (
             <button 
                key={lang.code}
                onClick={() => setLanguage(lang.code as any)}
                className={`p-3 rounded-xl border-2 text-left flex justify-between items-center transition-colors ${language === lang.code ? "border-brandBlue bg-blue-50" : "border-gray-200 hover:border-blue-200"}`}
             >
                <div>
                   <p className={`font-bold ${language === lang.code ? "text-brandBlue" : "text-gray-900"}`}>{lang.nativeName}</p>
                   <p className="text-xs text-gray-500">{lang.name}</p>
                </div>
                {language === lang.code && <Check size={18} className="text-brandBlue" />}
             </button>
          ))}
        </div>
      </div>

      <div className="space-y-6">
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
           <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
              <Mic size={20} className="text-green-600"/>
              System Capabilities Status
           </h3>
           <div className="space-y-4">
              <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                 <span className="text-sm font-medium text-gray-700">Voice Input (Speech-to-Text)</span>
                 <span className={`px-2 py-1 text-xs font-bold rounded-full ${isSpeechAvailable ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"}`}>
                   {isSpeechAvailable ? "Available" : "Unsupported Browser"}
                 </span>
              </div>
              <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                 <span className="text-sm font-medium text-gray-700">Voice Output (Text-to-Speech)</span>
                 <span className="px-2 py-1 text-xs font-bold rounded-full bg-green-100 text-green-800">
                   Available
                 </span>
              </div>
              <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                 <span className="text-sm font-medium text-gray-700">Offline Language Packs</span>
                 <span className="px-2 py-1 text-xs font-bold rounded-full bg-green-100 text-green-800">
                   Available (en, mr)
                 </span>
              </div>
              <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                 <span className="text-sm font-medium text-gray-700">Cloud Translation Service</span>
                 <span className="px-2 py-1 text-xs font-bold rounded-full bg-yellow-100 text-yellow-800">
                   Simulated Connected
                 </span>
              </div>
           </div>
        </div>

        <div className="bg-brandBlue/5 border border-brandBlue/20 rounded-xl p-6">
           <h3 className="text-lg font-bold text-brandBlue mb-2 flex items-center gap-2">
              <Volume2 size={20}/> Text-to-Speech Demo
           </h3>
           <p className="text-sm text-gray-700 mb-4">Click the button below to hear the system read an alert warning in your selected language.</p>
           <button 
              onClick={() => {
                const SpeechSynthesisUtterance = window.SpeechSynthesisUtterance;
                if (!SpeechSynthesisUtterance) { alert("Speech synthesis not supported in this browser."); return; }
                const msg = language === "mr" ? "कृपया लक्ष द्या! जवळच्या भागात संसर्गजन्य रोग आढळला आहे." : "Attention please. An infectious disease has been detected in the nearby area.";
                const utterance = new SpeechSynthesisUtterance(msg);
                utterance.lang = language === "mr" ? "mr-IN" : "en-IN";
                window.speechSynthesis.speak(utterance);
              }}
              className="px-4 py-2 bg-brandBlue text-white rounded-lg text-sm font-medium hover:bg-blue-700"
           >
              {t("btn.play")} (Demo)
           </button>
        </div>
      </div>
    </div>
  );
}

