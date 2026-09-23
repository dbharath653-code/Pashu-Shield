import { useState, useEffect, useRef } from "react";
import { Mic, Square, X, Volume2, Sparkles, AlertTriangle, Check, Loader2 } from "lucide-react";
import { useMultilingual } from "../context/MultilingualContext";
import { useAuth } from "../context/AuthContext";
import { useNavigate } from "react-router-dom";

export default function PersistentVoiceAssistant() {
  const { language, t, speak, stopSpeaking } = useMultilingual();
  const { user } = useAuth();
  const navigate = useNavigate();

  const [isOpen, setIsOpen] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [assistantReply, setAssistantReply] = useState("");
  const [pendingAction, setPendingAction] = useState<any>(null);
  const [isSubmittingAction, setIsSubmittingAction] = useState(false);

  const recognitionRef = useRef<any>(null);

  // Initialize Web Speech API recognition
  useEffect(() => {
    const SpeechRec = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (SpeechRec) {
      const rec = new SpeechRec();
      rec.continuous = false;
      rec.interimResults = false;

      rec.onresult = (event: any) => {
        const text = event.results[0][0].transcript;
        setTranscript(text);
        setIsListening(false);
        handleSendVoice(text);
      };

      rec.onerror = (e: any) => {
        console.warn("Speech recognition error:", e);
        setIsListening(false);
      };

      rec.onend = () => {
        setIsListening(false);
      };

      recognitionRef.current = rec;
    }

    return () => {
      stopSpeaking();
    };
  }, [language]);

  const toggleListening = () => {
    if (!recognitionRef.current) {
      // Fallback prompt for test environments without microphone
      const manual = prompt(
        language === "mr"
          ? "मायक्रोफोन उपलब्ध नाही. कृपया आपली तक्रार टाइप करा (उदा. माझी गाय आजारी आहे आणि चारा खात नाही):"
          : "Microphone unavailable. Type your query (e.g. My cow has fever and is not eating):"
      );
      if (manual) {
        setTranscript(manual);
        handleSendVoice(manual);
      }
      return;
    }

    if (isListening) {
      recognitionRef.current.stop();
      setIsListening(false);
    } else {
      const langMap: Record<string, string> = {
        en: "en-IN",
        mr: "mr-IN",
        hi: "hi-IN",
        te: "te-IN",
        kn: "kn-IN",
        gu: "gu-IN",
        ta: "ta-IN",
        bn: "bn-IN"
      };
      recognitionRef.current.lang = langMap[language] || "en-US";
      setTranscript("");
      setAssistantReply("");
      setPendingAction(null);
      stopSpeaking();
      recognitionRef.current.start();
      setIsListening(true);
    }
  };

  const handleSendVoice = async (queryText: string) => {
    if (!queryText.trim()) return;
    setIsProcessing(true);
    try {
      const res = await fetch("/api/v1/voice/intent", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          transcript: queryText,
          language: language,
          current_location: { district: user?.district || "Pune", village: user?.village || "Shirur" }
        })
      });

      if (res.ok) {
        const data = await res.json();
        setAssistantReply(data.fulfillment_text);
        speak(data.fulfillment_text, language);

        if (data.requires_confirmation) {
          setPendingAction(data);
        } else if (data.action_payload?.navigate) {
          setTimeout(() => {
            navigate(data.action_payload.navigate);
            setIsOpen(false);
          }, 1800);
        }
      } else {
        const fallback = language === "mr" ? "मी समजू शकलो नाही. कृपया पुन्हा बोला." : "I could not process that. Please try again.";
        setAssistantReply(fallback);
        speak(fallback, language);
      }
    } catch {
      const fallback = language === "mr" ? "सर्व्हरशी संपर्क होऊ शकला नाही." : "Connection failed. Please check network.";
      setAssistantReply(fallback);
      speak(fallback, language);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleConfirmAction = async () => {
    if (!pendingAction) return;
    setIsSubmittingAction(true);
    try {
      if (pendingAction.intent === "REPORT_DISEASE") {
        const payload = pendingAction.action_payload;
        const district = payload.district || user?.district;
        const village = payload.village || user?.village;
        if (!district || !village) {
          // Never invent a location: send the user to the form to enter it.
          const msg = language === "mr" ? "कृपया अहवाल फॉर्ममध्ये जिल्हा व गाव भरा." : "Please enter your district and village in the report form.";
          setAssistantReply(msg);
          speak(msg, language);
          setPendingAction(null);
          navigate("/reporting");
          return;
        }
        const res = await fetch("/api/v1/reports", {
          method: "POST",
          headers: { "Content-Type": "application/json", "Idempotency-Key": `voice-${pendingAction.intent}-${transcript}`.slice(0, 120) },
          body: JSON.stringify({
            species: payload.species || "Cattle",
            number_affected: payload.number_affected || 1,
            number_dead: payload.number_dead || 0,
            symptoms: payload.symptoms || [],
            district,
            village,
            suspected_disease: payload.suspected_disease || "Unknown",
            channel: "VOICE",
            notes: `Voice reported: ${transcript}`
          })
        });

        if (res.ok) {
          const result = await res.json();
          const successMsg =
            language === "mr"
              ? `अहवाल दाखल झाला${result.assignedCase?.caseNumber ? ` (केस ${result.assignedCase.caseNumber})` : ""}. पशुवैद्यकीय तपासणीसाठी रांगेत आहे.`
              : `Report submitted${result.assignedCase?.caseNumber ? ` (Case #${result.assignedCase.caseNumber})` : ""}. ${result.assignedCase?.assignedVet ? "A veterinarian has been assigned." : "It is queued for veterinary triage."}`;
          setAssistantReply(successMsg);
          speak(successMsg, language);
          setPendingAction(null);
          setTimeout(() => {
            navigate("/reporting");
            setIsOpen(false);
          }, 3000);
        } else {
          const err = await res.json().catch(() => null);
          const msg = `Report not submitted: ${err?.error?.message || err?.detail?.message || res.status}`;
          setAssistantReply(msg);
          speak(msg, language);
        }
      } else if (pendingAction.intent === "REQUEST_VETERINARIAN") {
        const confirmMsg =
          language === "mr"
            ? "कृपया 1962 वर कॉल करा किंवा पशुवैद्यकीय विनंती फॉर्म वापरा."
            : "Please call the 1962 helpline or submit a disease report so a veterinarian can be dispatched.";
        setAssistantReply(confirmMsg);
        speak(confirmMsg, language);
        setPendingAction(null);
      }
    } catch {
      alert("Error submitting voice action");
    } finally {
      setIsSubmittingAction(false);
    }
  };

  return (
    <>
      {/* Floating Persistent Voice Button */}
      <div className="fixed bottom-6 right-6 z-[999] mb-[env(safe-area-inset-bottom)] mr-[env(safe-area-inset-right)]">
        <button
          onClick={() => {
            setIsOpen(true);
            toggleListening();
          }}
          className="relative group flex items-center justify-center w-16 h-16 bg-blue-600 hover:bg-blue-700 text-white rounded-full shadow-2xl transition-all duration-300 transform hover:scale-105 active:scale-95 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-blue-600"
          title={t("card.voiceInput")}
          aria-label={t("card.voiceInput")}
        >
          <span className="absolute -top-1 -right-1 flex h-4 w-4">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-4 w-4 bg-red-500"></span>
          </span>
          <Mic size={30} className="drop-shadow-sm" />
        </button>
      </div>

      {/* Voice Assistant Modal */}
      {isOpen && (
        <div className="fixed inset-0 z-[1000] bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div
            className="bg-white rounded-2xl shadow-2xl border border-gray-100 max-w-lg w-full overflow-hidden flex flex-col max-h-[85vh] animate-in fade-in zoom-in-95 duration-200"
            role="dialog"
            aria-modal="true"
            aria-label={t("farmer.talk")}
          >
            {/* Header */}
            <div className="bg-gradient-to-r from-blue-600 to-indigo-700 p-5 text-white flex justify-between items-center">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-2xl bg-white/20 flex items-center justify-center">
                  <Sparkles size={22} className="text-white" />
                </div>
                <div>
                  <h3 className="font-bold text-lg leading-tight">{t("farmer.talk")}</h3>
                  <p className="text-xs text-white flex items-center gap-1">
                    <span>{language.toUpperCase()}</span> • <span>AI Clinical Assistant</span>
                  </p>
                </div>
              </div>
              <button
                onClick={() => {
                  stopSpeaking();
                  setIsOpen(false);
                }}
                className="w-8 h-8 rounded-full bg-white/10 hover:bg-white/20 flex items-center justify-center transition-colors text-white"
              >
                <X size={18} />
              </button>
            </div>

            {/* Conversation Flow Area */}
            <div className="p-6 flex-1 overflow-y-auto space-y-4 bg-gray-50/50">
              {/* Default Instruction */}
              {!transcript && !assistantReply && (
                <div className="text-center py-6 text-gray-500">
                  <div className="w-16 h-16 rounded-full bg-blue-50 text-blue-700 mx-auto flex items-center justify-center mb-3">
                    <Mic size={28} />
                  </div>
                  <h4 className="font-semibold text-gray-900 text-base">{t("voice.speakNow")}</h4>
                  <p className="text-xs text-gray-500 mt-1 max-w-xs mx-auto">
                    {language === "mr"
                      ? "उदा. 'माझी गाय आजारी आहे, ताप आहे', 'पशुवैद्यक बोलवा', किंवा 'लसीकरण कधी आहे?'"
                      : "e.g., 'My cow has fever and is not eating', 'Request a vet', or 'Show my animals'"}
                  </p>
                </div>
              )}

              {/* User Voice Query */}
              {transcript && (
                <div className="flex justify-end">
                  <div className="bg-blue-600 text-white rounded-2xl px-4 py-3 max-w-[85%] shadow-sm text-sm font-medium">
                    <p>{transcript}</p>
                  </div>
                </div>
              )}

              {/* AI Processing Status */}
              {isProcessing && (
                <div className="flex items-center gap-2 text-blue-700 bg-blue-50 px-4 py-3 rounded-2xl w-fit text-sm">
                  <Loader2 size={16} className="animate-spin text-blue-700" />
                  <span>{t("voice.processing")}</span>
                </div>
              )}

              {/* Assistant Reply */}
              {assistantReply && !isProcessing && (
                <div className="flex gap-3 items-start">
                  <div className="w-8 h-8 rounded-full bg-indigo-600 text-white flex items-center justify-center shrink-0 text-xs font-bold mt-1">
                    PS
                  </div>
                  <div className="bg-white border border-gray-200 text-gray-700 rounded-2xl p-4 shadow-sm text-sm space-y-2">
                    <p className="leading-relaxed whitespace-pre-wrap">{assistantReply}</p>
                    <button
                      onClick={() => speak(assistantReply, language)}
                      className="text-xs text-blue-700 font-semibold hover:underline flex items-center gap-1 pt-1"
                    >
                      <Volume2 size={14} /> {t("btn.play")}
                    </button>
                  </div>
                </div>
              )}

              {/* Action Confirmation Banner */}
              {pendingAction && (
                <div className="bg-amber-50 border border-amber-200 rounded-2xl p-4 text-amber-900 space-y-3">
                  <div className="flex items-center gap-2 font-bold text-sm text-amber-900">
                    <AlertTriangle size={16} className="text-amber-700" />
                    <span>{t("voice.confirmSubmit")}</span>
                  </div>
                  <p className="text-xs text-amber-700">
                    {language === "mr"
                      ? "आपल्या अहवालाची पडताळणी झाली आहे. पुष्टी केल्यास तात्काळ शासकीय पशुवैद्यकीय पथकाला सूचना जाईल."
                      : "Report has been triaged. Confirming will immediately notify the emergency veterinary network."}
                  </p>
                  <div className="flex gap-2 pt-1">
                    <button
                      disabled={isSubmittingAction}
                      onClick={handleConfirmAction}
                      className="flex-1 bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-3 rounded-xl text-xs flex items-center justify-center gap-1 shadow-sm transition-colors"
                    >
                      {isSubmittingAction ? (
                        <Loader2 size={14} className="animate-spin" />
                      ) : (
                        <Check size={14} />
                      )}
                      <span>{t("voice.yes")}</span>
                    </button>
                    <button
                      disabled={isSubmittingAction}
                      onClick={() => {
                        setPendingAction(null);
                        setAssistantReply(language === "mr" ? "अहवाल रद्द करण्यात आला." : "Report cancelled.");
                      }}
                      className="flex-1 bg-gray-200 hover:bg-gray-300 text-gray-700 font-semibold py-2 px-3 rounded-xl text-xs transition-colors"
                    >
                      {t("voice.no")}
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Bottom Mic Input Controls */}
            <div className="p-4 bg-white border-t border-gray-100 flex items-center gap-3">
              <input
                type="text"
                value={transcript}
                onChange={(e) => setTranscript(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSendVoice(transcript)}
                placeholder={language === "mr" ? "बोलण्यासाठी बटण दाबा किंवा येथे टाइप करा..." : "Tap mic to speak, or type here..."}
                className="flex-1 text-sm bg-gray-100 border-0 rounded-full px-4 py-2.5 focus:ring-2 focus:ring-blue-500 focus:bg-white transition-all"
              />
              <button
                onClick={toggleListening}
                className={`p-3 rounded-full text-white shadow-md transition-all ${
                  isListening
                    ? "bg-red-500 hover:bg-red-600 animate-pulse ring-4 ring-red-200"
                    : "bg-blue-600 hover:bg-blue-700"
                }`}
                title={isListening ? t("btn.stop") : t("btn.start")}
              >
                {isListening ? <Square size={18} fill="currentColor" /> : <Mic size={18} />}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
