import React, { useState, useEffect, useRef } from "react";
import { useMultilingual } from "../../context/MultilingualContext";
import { Mic, Square, Save, Languages, CheckCircle, WifiOff } from "lucide-react";

export default function VoiceFieldReport() {
  const { language, t, isSpeechAvailable, translateText, saveVoiceReport } = useMultilingual();
  
  const [isRecording, setIsRecording] = useState(false);
  const [animalId, setAnimalId] = useState("");
  const [location, setLocation] = useState("");
  const [transcript, setTranscript] = useState("");
  const [translated, setTranslated] = useState("");
  const [isTranslating, setIsTranslating] = useState(false);
  
  const recognitionRef = useRef<any>(null);

  useEffect(() => {
    if (isSpeechAvailable && !recognitionRef.current) {
      const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      if (SpeechRecognition) {
        recognitionRef.current = new SpeechRecognition();
        recognitionRef.current.continuous = true;
        recognitionRef.current.interimResults = true;
        
        recognitionRef.current.onresult = (event: any) => {
          let currentTranscript = "";
          for (let i = event.resultIndex; i < event.results.length; i++) {
            currentTranscript += event.results[i][0].transcript;
          }
          setTranscript(prev => prev + " " + currentTranscript);
        };
        
        recognitionRef.current.onerror = (event: any) => {
          console.error("Speech recognition error", event.error);
          setIsRecording(false);
        };
      }
    }
  }, [isSpeechAvailable]);

  const toggleRecording = () => {
    if (!recognitionRef.current) {
      alert("Speech recognition is not supported in this browser.");
      return;
    }
    
    if (isRecording) {
      recognitionRef.current.stop();
      setIsRecording(false);
    } else {
      // Map basic languages to BCP 47
      const langMap: Record<string, string> = { en: "en-IN", mr: "mr-IN", hi: "hi-IN", te: "te-IN", kn: "kn-IN", gu: "gu-IN", ta: "ta-IN", bn: "bn-IN" };
      recognitionRef.current.lang = langMap[language] || "en-US";
      recognitionRef.current.start();
      setIsRecording(true);
    }
  };

  const handleTranslate = async () => {
    if (!transcript) return;
    setIsTranslating(true);
    try {
      // If language is already English, just copy it, else translate to English for standardization
      if (language === "en") {
        setTranslated(transcript);
      } else {
        const result = await translateText(transcript, language, "en");
        setTranslated(result);
      }
    } finally {
      setIsTranslating(false);
    }
  };

  const handleSave = async () => {
    if (!animalId || !transcript) {
      alert("Animal ID and Voice Transcript are required.");
      return;
    }

    const report = {
      id: `VR-${Date.now()}`,
      animalId,
      location,
      originalLanguage: language,
      originalText: transcript,
      translatedText: translated,
      timestamp: new Date().toISOString(),
      officerId: "Govt. Officer (MH-123)",
      syncStatus: navigator.onLine ? "Synced" as const : "Pending" as const
    };

    await saveVoiceReport(report);
    alert(`Voice Report Saved! ${navigator.onLine ? "" : "(Offline Mode - Queued for sync)"}`);
    setAnimalId("");
    setLocation("");
    setTranscript("");
    setTranslated("");
  };

  const isOffline = !navigator.onLine;

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
      <div className="flex justify-between items-center mb-6 border-b border-gray-200 pb-4">
         <div>
            <h3 className="text-xl font-bold text-gray-900 flex items-center gap-2">
              <Mic className="text-brandBlue" />
              {t("card.voiceReport")}
            </h3>
            <p className="text-sm text-gray-500 mt-1">Speak in {language.toUpperCase()} to rapidly file field observations.</p>
         </div>
         {isOffline && (
           <div className="flex items-center gap-2 px-3 py-1 bg-yellow-50 text-yellow-800 rounded-lg text-sm font-medium border border-yellow-200">
             <WifiOff size={16} /> Offline Mode - Drafts will be saved locally
           </div>
         )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
         <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Animal ID *</label>
            <input type="text" value={animalId} onChange={e => setAnimalId(e.target.value)} className="w-full border-gray-300 rounded-lg p-2.5 border focus:ring-brandBlue text-lg font-mono" placeholder="MH-CAT-001" />
         </div>
         <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Village/Location</label>
            <input type="text" value={location} onChange={e => setLocation(e.target.value)} className="w-full border-gray-300 rounded-lg p-2.5 border focus:ring-brandBlue" placeholder="Shirur" />
         </div>
      </div>

      <div className="space-y-4">
         <div className="flex items-center justify-between">
            <label className="block text-sm font-bold text-gray-800">Officer Observations (Voice Input)</label>
            <button 
              onClick={toggleRecording} 
              className={`flex items-center gap-2 px-6 py-3 rounded-full font-bold text-white transition-all shadow-md ${isRecording ? "bg-red-500 hover:bg-red-600 animate-pulse" : "bg-brandBlue hover:bg-blue-700"}`}
            >
              {isRecording ? <><Square size={18} fill="currentColor"/> {t("btn.stop")}</> : <><Mic size={18} /> {t("btn.start")}</>}
            </button>
         </div>

         <div className="relative">
           <textarea 
             className="w-full border-2 border-gray-200 rounded-xl p-4 min-h-[150px] text-lg focus:border-brandBlue focus:ring-0 resize-y"
             placeholder="Click Start Recording and speak your observations..."
             value={transcript}
             onChange={e => setTranscript(e.target.value)}
           ></textarea>
           {isRecording && (
             <div className="absolute bottom-4 right-4 flex items-center gap-2 text-red-500 font-bold bg-white px-3 py-1 rounded-full border border-red-100 shadow-sm">
               <span className="w-2 h-2 rounded-full bg-red-500 animate-ping"></span>
               Listening...
             </div>
           )}
         </div>

         {transcript && (
           <div className="pt-2">
             <button onClick={handleTranslate} disabled={isTranslating} className="flex items-center gap-2 px-4 py-2 bg-purple-100 text-purple-800 rounded-lg font-medium hover:bg-purple-200 transition-colors">
                <Languages size={18} />
                {isTranslating ? "Translating..." : "Translate to Standardized English"}
             </button>
           </div>
         )}

         {translated && (
           <div className="bg-gray-50 border border-gray-200 rounded-xl p-4 mt-4">
             <h4 className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2 flex items-center gap-1"><CheckCircle size={14} className="text-green-500"/> Normalized English Translation</h4>
             <p className="text-gray-900 font-medium">{translated}</p>
           </div>
         )}
      </div>

      <div className="mt-8 pt-6 border-t border-gray-200 flex justify-end">
         <button onClick={handleSave} className="flex items-center gap-2 px-8 py-3 bg-green-600 text-white rounded-xl font-bold text-lg hover:bg-green-700 shadow-sm">
            <Save size={20} />
            {t("btn.save")}
         </button>
      </div>
    </div>
  );
}

