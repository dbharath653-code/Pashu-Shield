import { useState, useEffect, useRef } from "react";
import { useMultilingual } from "../../context/MultilingualContext";
import { Mic, Square, MessageSquare, PlayCircle, Loader2 } from "lucide-react";

export default function VoiceAssistant() {
  const { language, t, isSpeechAvailable, speak, stopSpeaking } = useMultilingual();
  const [isListening, setIsListening] = useState(false);
  const [query, setQuery] = useState("");
  const [response, setResponse] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  
  const recognitionRef = useRef<any>(null);

  useEffect(() => {
    if (isSpeechAvailable && !recognitionRef.current) {
      const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      if (SpeechRecognition) {
        recognitionRef.current = new SpeechRecognition();
        recognitionRef.current.continuous = false;
        recognitionRef.current.interimResults = false;
        
        recognitionRef.current.onend = () => {
          setIsListening(false);
        };
      }
    }
    return () => stopSpeaking();
  }, [isSpeechAvailable]);

  // Rebind the result handler so it always uses the freshest state closure
  useEffect(() => {
    if (recognitionRef.current) {
      recognitionRef.current.onresult = (event: any) => {
        const finalTranscript = event.results[0][0].transcript;
        setQuery(finalTranscript);
        handleAsk(finalTranscript);
      };
    }
  }, [language, speak]);

  const toggleListening = () => {
    if (!recognitionRef.current) return alert("Speech recognition unsupported.");
    if (isListening) {
      recognitionRef.current.stop();
      setIsListening(false);
    } else {
      const langMap: Record<string, string> = { en: "en-IN", mr: "mr-IN", hi: "hi-IN", te: "te-IN", kn: "kn-IN", gu: "gu-IN", ta: "ta-IN", bn: "bn-IN" };
      recognitionRef.current.lang = langMap[language] || "en-US";
      setQuery("");
      setResponse("");
      stopSpeaking();
      recognitionRef.current.start();
      setIsListening(true);
    }
  };

  const handleAsk = async (text: string) => {
    if (!text) return;
    setIsProcessing(true);
    try {
      await new Promise(r => setTimeout(r, 800));
      
      let answer = "";
      const lower = text.toLowerCase();
      
      // MOCK KNOWLEDGE BASE WITH HARDCODED MARATHI & ENGLISH RESPONSES
      if (language === "mr") {
         if (lower.includes("foot and mouth") || lower.includes("fmd") || lower.includes("लाळ्या") || lower.includes("खुरकूत")) {
            answer = "लाळ्या खुरकूत (FMD) ची लक्षणे: ताप, तोंडात आणि पायांवर फोड, दूध उत्पादनात घट आणि लंगडेपणा. तात्काळ अलग ठेवणे आवश्यक आहे.";
         } else if (lower.includes("lumpy") || lower.includes("लंपी")) {
            answer = "लंपी त्वचा रोग (Lumpy Skin Disease) ची लक्षणे: ताप, सुजलेल्या लिम्फ नोड्स आणि त्वचेवर 2-5 सेमी आकाराच्या गाठी.";
         } else {
            answer = "माफ करा, मला या आजाराची माहिती मिळाली नाही. कृपया लाळ्या खुरकूत किंवा लंपी आजाराबद्दल विचारा.";
         }
      } else {
         if (lower.includes("foot and mouth") || lower.includes("fmd")) {
            answer = "Foot and Mouth Disease (FMD) symptoms include: fever, blisters in the mouth and on feet, drop in milk production, and lameness. Immediate quarantine is required.";
         } else if (lower.includes("lumpy")) {
            answer = "Lumpy Skin Disease is characterized by fever, enlarged superficial lymph nodes, and multiple nodules on the skin.";
         } else {
            answer = "I could not find specific information for that query. Please try asking about specific livestock diseases like FMD or Lumpy Skin Disease.";
         }
      }

      setResponse(answer);
      speak(answer, language);

    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="bg-brandBlue/5 rounded-xl shadow-sm border border-brandBlue/20 p-6 flex flex-col h-full min-h-[400px]">
      <h3 className="text-xl font-bold text-brandBlue mb-2 flex items-center gap-2">
         <MessageSquare />
         {t("card.voiceInput")}
      </h3>
      <p className="text-sm text-gray-700 mb-6">Ask about livestock disease symptoms, protocols, and field instructions.</p>

      <div className="flex-1 bg-white rounded-xl border border-blue-100 p-4 flex flex-col gap-4 overflow-y-auto mb-4">
         {query && (
           <div className="self-end bg-blue-50 text-blue-900 rounded-xl rounded-tr-none px-4 py-3 max-w-[85%] border border-blue-100">
             <p className="font-medium">{query}</p>
           </div>
         )}
         
         {isProcessing && (
           <div className="self-start flex items-center gap-2 text-brandBlue">
             <Loader2 size={16} className="animate-spin" /> Retrieving knowledge...
           </div>
         )}

         {response && !isProcessing && (
           <div className="self-start bg-gray-50 text-gray-800 rounded-xl rounded-tl-none px-4 py-3 max-w-[85%] border border-gray-200">
             <p>{response}</p>
             <button onClick={() => speak(response, language)} className="mt-2 text-brandBlue hover:text-blue-800 flex items-center gap-1 text-sm font-medium">
                <PlayCircle size={16} /> Play Audio
             </button>
           </div>
         )}
      </div>

      <div className="flex gap-2">
        <input 
          type="text" 
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder="Type or tap microphone..." 
          className="flex-1 border border-blue-200 rounded-full px-4 focus:ring-brandBlue focus:border-brandBlue"
          onKeyDown={e => e.key === "Enter" && handleAsk(query)}
        />
        <button 
          onClick={toggleListening}
          className={`p-3 rounded-full text-white shadow-md transition-all ${isListening ? "bg-red-500 animate-pulse" : "bg-brandBlue hover:bg-blue-700"}`}
        >
          {isListening ? <Square size={20} fill="currentColor" /> : <Mic size={20} />}
        </button>
      </div>
    </div>
  );
}
