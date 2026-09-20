import { useState, useEffect, useRef } from 'react';
import { MapPin, Mic, Edit2, CheckCircle, AlertTriangle, Save, WifiOff, RefreshCw, Download, Check, Database } from 'lucide-react';
import { useAppContext } from '../context/AppContext';
import type { Report } from '../context/AppContext';
import { ReportingService, mlSymptoms } from '../services/ReportingService';
import type { ReportDraft } from '../services/ReportingService';
import { localMLService } from '../services/LocalMLService';
import { DISTRICT_NAMES } from '../services/ReferenceData';
import { useSync } from '../services/SyncService';

// HTML number inputs always hand back strings; ReportDraft expects numbers or "".
const toFloatOrEmpty = (value: string): number | "" => {
  if (value.trim() === '') return '';
  const parsed = Number(value);
  return Number.isNaN(parsed) ? '' : parsed;
};
const toIntOrEmpty = (value: string): number | "" => {
  const parsed = toFloatOrEmpty(value);
  return parsed === '' ? '' : Math.trunc(parsed);
};

const diseaseKnowledgeBase: Record<string, { description: string, remedies: string }> = {
  "LSD": { description: "Lumpy Skin Disease is a viral infection causing fever and skin nodules.", remedies: "Separate the infected animal immediately. Apply neem oil on skin lesions." },
  "FMD": { description: "Foot and Mouth Disease is a highly contagious virus.", remedies: "Wash the mouth and feet with mild potassium permanganate solution." },
  "Brucellosis": { description: "Brucellosis is a bacterial infection.", remedies: "Isolate the animal. Handle with strict hygiene." },
  "PPR": { description: "PPR, also known as Goat Plague.", remedies: "Keep animal warm and hydrated. Clean eyes and nose." },
  "BND": { description: "A severe disease affecting livestock.", remedies: "Ensure adequate hydration with electrolytes." },
  "Healthy": { description: "The animal appears healthy.", remedies: "Continue normal feeding." },
  "Unknown": { description: "Symptoms do not strongly match a specific disease.", remedies: "Keep isolated, monitor temperature, and contact a vet." }
};

export default function CaseReporting() {
  const { reports, addReport } = useAppContext();
  const { isOnline, enqueueOfflineItem, syncQueue, openSyncModal } = useSync();

  const [step, setStep] = useState(1);
  const [activeTab, setActiveTab] = useState('New Report');
  const [formData, setFormData] = useState<ReportDraft>({
    species: 'Cattle', gender: 'Female', age: '', temperature: '', numberAffected: 1, numberDead: 0,
    symptoms: [], village: '', district: '', state: '', disease: 'Unknown'
  });

  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [isPredicting, setIsPredicting] = useState(false);
  const [predictionResult, setPredictionResult] = useState<any>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [offlineSavedMessage, setOfflineSavedMessage] = useState(false);

  // Offline WebAssembly STT State
  const worker = useRef<Worker | null>(null);
  const mediaRecorder = useRef<MediaRecorder | null>(null);
  const audioChunks = useRef<BlobPart[]>([]);
  const [modelReady, setModelReady] = useState(false);
  const [modelLoading, setModelLoading] = useState(false);
  const [modelProgress, setModelProgress] = useState(0);
  const [language, setLanguage] = useState('english');

  useEffect(() => {
    localMLService.loadModel();

    // Initialize Web Worker
    worker.current = new Worker(new URL('../workers/whisperWorker.ts', import.meta.url), { type: 'module' });
    worker.current.onerror = (e) => {
      console.error('Worker failed to spawn:', e);
    };
    worker.current.onmessage = (event) => {
      const msg = event.data;
      if (msg.type === 'progress') {
        if (msg.data && msg.data.progress) setModelProgress(msg.data.progress);
      } else if (msg.type === 'ready') {
        setModelReady(true);
        setModelLoading(false);
      } else if (msg.type === 'result') {
        const text = msg.text;
        setTranscript((prev) => prev.replace("Transcribing locally...", "") + " " + text);
        processTranscript(text);
      } else if (msg.type === 'error') {
        console.error('Worker error', msg.error);
        setModelLoading(false);
        setTranscript("Error transcribing audio: " + msg.error);
      }
    };

    const draft = ReportingService.getDraft();
    if (draft && Object.keys(draft).length > 0) {
      if (window.confirm("Resume unfinished report?")) {
        setFormData({ ...formData, ...draft });
      } else {
        ReportingService.clearDraft();
      }
    }

    return () => {
      if (worker.current) worker.current.terminate();
    };
  }, []);

  useEffect(() => {
    if (step > 1 && step < 6 && activeTab === 'New Report') {
      ReportingService.saveDraft(formData);
    }
  }, [formData, step, activeTab]);

  const speak = (text: string) => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      window.speechSynthesis.speak(utterance);
    }
  };

  const validateStep = () => {
    const newErrors: Record<string, string> = {};
    if (step === 2) {
      if (!formData.species) newErrors.species = "Species is required";
      if (formData.numberAffected === '' || Number(formData.numberAffected) < 1) newErrors.numberAffected = "At least 1 animal must be affected";
      if (Number(formData.numberDead) > Number(formData.numberAffected)) newErrors.numberDead = "Number dead cannot exceed number affected";
      if (formData.age !== '' && Number(formData.age) < 0) newErrors.age = "Age cannot be negative";
    }
    if (step === 3) {
      if (formData.symptoms.length === 0) newErrors.symptoms = "Select at least one symptom for AI prediction.";
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const nextStep = () => { if (validateStep()) setStep(s => Math.min(s + 1, 6)); };
  const prevStep = () => setStep(s => Math.max(s - 1, 1));

  const loadOfflineModel = () => {
    setModelLoading(true);
    worker.current?.postMessage({ type: 'load' });
  };

  const startVoiceReporting = async () => {
    if (!modelReady) return alert('Please download the offline voice model first.');
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      return alert('Microphone access unavailable. Ensure you are using HTTPS or localhost.');
    }
    
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorder.current = new MediaRecorder(stream);
      audioChunks.current = [];

      mediaRecorder.current.ondataavailable = (event) => {
        if (event.data.size > 0) audioChunks.current.push(event.data);
      };

      mediaRecorder.current.onstop = async () => {
        const audioBlob = new Blob(audioChunks.current, { type: 'audio/webm' });
        const arrayBuffer = await audioBlob.arrayBuffer();
        const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 16000 });
        const decoded = await audioContext.decodeAudioData(arrayBuffer);
        const float32Array = decoded.getChannelData(0);

        setTranscript('Transcribing locally...');
        worker.current?.postMessage({ type: 'transcribe', audio: float32Array, language: language });
      };

      mediaRecorder.current.start();
      setIsListening(true);
      setTranscript('Listening... Speak your report, then click Stop.');
      speak('Listening.');
    } catch {
      alert('Microphone access denied or unavailable.');
    }
  };

  const stopVoiceReporting = () => {
      if (mediaRecorder.current && mediaRecorder.current.state === 'recording') {
        mediaRecorder.current.stop();
        mediaRecorder.current.stream.getTracks().forEach(track => track.stop());
      }
      setIsListening(false);
  };

  const processTranscript = async (textToProcess: string) => {
    if (textToProcess && textToProcess.length > 5) {
        const extracted = await ReportingService.extractEntities(textToProcess);
        setFormData(prev => {
          const merged = { ...prev, ...extracted, symptoms: Array.from(new Set([...prev.symptoms, ...(extracted.symptoms || [])])) };
          speak(`Finished. Extracted species ${merged.species}, and ${merged.symptoms.length} symptoms.`);
          return merged;
        });
        setTimeout(() => { nextStep(); }, 3000);
    }
  };

  const useCurrentLocation = async () => {
    try {
      setTranscript("Acquiring GPS location...");
      const loc = await ReportingService.getLocation();
      setFormData(prev => ({...prev, lat: loc.lat, lng: loc.lng, village: loc.village, district: loc.district, state: loc.state}));
      setTranscript(`Location found: ${loc.village}, ${loc.district}`);
    } catch {
      alert("Location permission unavailable. Enter location manually.");
    }
  };

  const handlePredictDisease = async () => {
    speak(!isOnline ? "Analyzing locally without internet..." : "Analyzing symptoms...");
    setIsPredicting(true);
    try {
        if (!localMLService.isModelReady()) {
            await localMLService.loadModel();
        }

        const symptomsData: Record<string, number> = {};
        mlSymptoms.forEach(sym => { symptomsData[sym] = formData.symptoms.includes(sym) ? 1 : 0; });
        const data = { Species: formData.species, Age_Years: Number(formData.age) || 3, Gender: formData.gender, Temperature_C: Number(formData.temperature) || 38.5, ...symptomsData };

        const result = localMLService.predict(data);

        if (result && result.disease) {
            const knowledge = diseaseKnowledgeBase[result.disease] || diseaseKnowledgeBase["Unknown"];
            setFormData(prev => ({...prev, disease: result.disease}));
            setPredictionResult({ disease: result.disease, confidence: Math.round(result.confidence * 100), action: 'Consult veterinarian', description: knowledge.description, remedies: knowledge.remedies });
            speak(`The local AI predicts ${result.disease} with ${Math.round(result.confidence * 100)} percent confidence.`);
        } else {
          throw new Error("Prediction failed");
        }
    } catch (error) {
        console.error(error);
        const isFMD = formData.symptoms.includes("Salivation") && formData.symptoms.includes("Fever");
        const disease = isFMD ? "FMD" : "Unknown";
        setPredictionResult({ disease, confidence: 60, action: "Rule Engine: Consult Vet", description: "Rule-based fallback used.", remedies: "Keep isolated." });
        setFormData(prev => ({...prev, disease}));
        speak(`Offline fallback used. Risk of ${disease}.`);
    } finally { setIsPredicting(false); }
  };

  const handleSubmit = async () => {
    const clientUuid = `PS-OFFLINE-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`;
    const report: Report = {
      id: clientUuid,
      date: new Date().toISOString().split('T')[0],
      species: formData.species || 'Unknown',
      numberAffected: Number(formData.numberAffected) || 1,
      numberDead: Number(formData.numberDead) || 0,
      district: formData.district || 'Unknown',
      village: formData.village || 'Unknown',
      symptoms: formData.symptoms || [],
      status: !isOnline ? 'QUEUED' : 'SUBMITTED',
      disease: formData.disease || 'Unknown',
    };

    if (!isOnline) {
      // 1. Save to IndexedDB sync queue with client UUID
      await enqueueOfflineItem(
        "reports",
        report.id,
        `Disease Report (${report.species} - ${report.disease})`,
        report
      );
      // 2. Also save to local AppContext state
      addReport(report);
      setOfflineSavedMessage(true);
      speak("Report saved offline. It will automatically sync when internet is restored.");
    } else {
      try {
        const res = await fetch('/api/v1/reports', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            species: report.species,
            number_affected: report.numberAffected,
            number_dead: report.numberDead,
            symptoms: report.symptoms,
            district: report.district,
            village: report.village,
            suspected_disease: report.disease,
            temperature: Number(formData.temperature) || null,
            notes: formData.disease !== 'Unknown' ? `Suspected ${formData.disease}` : undefined
          })
        });
        if (res.ok) {
          const result = await res.json();
          report.status = 'Confirmed';
          if (result.assignedCase) {
            alert(`Report successfully submitted to Veterinary Network!\nCase #${result.assignedCase.caseNumber}\nTriage: ${result.triage.risk_level} (${result.triage.urgency})\nAssigned Vet: ${result.assignedCase.assignedVet?.full_name || 'Emergency Unit'}`);
          }
        }
      } catch (e) {
        console.warn('Backend report submission error:', e);
        // Fallback to offline queue
        await enqueueOfflineItem(
          "reports",
          report.id,
          `Disease Report (${report.species} - ${report.disease})`,
          report
        );
      }
      addReport(report);
      speak("Report submitted successfully.");
    }

    ReportingService.clearDraft();
    setStep(1);
    setActiveTab('My Reports');
  };

  const pendingQueueReports = syncQueue.filter(q => q.store === "reports" && (q.status === "Pending" || q.status === "Failed"));

  return (
    <div className="bg-white rounded-xl shadow-xs border border-gray-200 flex flex-col h-full overflow-hidden">
      {/* Top Tab Bar */}
      <div className="flex border-b border-gray-200 px-3 sm:px-4 bg-gray-50/50 overflow-x-auto">
        {['New Report', 'My Reports', 'Report History'].map(tab => (
          <button 
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 sm:px-6 py-3.5 text-xs sm:text-sm font-semibold border-b-2 whitespace-nowrap transition-colors touch-manipulation ${
              activeTab === tab 
                ? 'border-brandBlue text-brandBlue' 
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto bg-gray-50 p-3 sm:p-4 md:p-6">
        {activeTab === 'New Report' && (
          <div className="max-w-3xl mx-auto w-full">
            {!isOnline && (
              <div className="bg-amber-50 border-l-4 border-amber-400 p-3.5 sm:p-4 mb-4 rounded-r-xl flex items-start gap-3 shadow-2xs">
                 <WifiOff className="text-amber-600 shrink-0 mt-0.5" size={18} />
                 <div className="text-xs sm:text-sm text-amber-800">
                   <strong>Offline Data Collection Active.</strong> Reports created without internet will be saved safely to local IndexedDB and automatically synchronized when network connectivity is restored.
                 </div>
              </div>
            )}

            {offlineSavedMessage && (
              <div className="bg-emerald-50 border-l-4 border-emerald-500 p-3.5 mb-4 rounded-r-xl flex items-center justify-between shadow-2xs">
                 <div className="flex items-center gap-2 text-xs sm:text-sm text-emerald-800 font-semibold">
                   <CheckCircle className="text-emerald-600 shrink-0" size={18} />
                   <span>Report saved offline. It will automatically sync when internet is restored.</span>
                 </div>
                 <button
                   onClick={() => setOfflineSavedMessage(false)}
                   className="text-xs text-emerald-700 hover:underline font-bold"
                 >
                   Dismiss
                 </button>
              </div>
            )}

            <div className="bg-white shadow-xs border border-gray-200 rounded-2xl p-4 sm:p-6">
              {/* Stepper bar */}
              <div className="flex items-center justify-between mb-6 sm:mb-8 gap-1">
                 {[1, 2, 3, 4, 5, 6].map(i => (
                   <div key={i} className={`flex-1 h-2 rounded-full ${step >= i ? 'bg-brandBlue' : 'bg-gray-200'}`} />
                 ))}
              </div>

              {step === 1 && (
                <div className="text-center py-6 sm:py-8 max-w-lg mx-auto">
                   <h2 className="text-xl sm:text-2xl font-black text-gray-800 mb-2">🎙 REPORT BY VOICE</h2>
                   <p className="text-xs sm:text-sm text-gray-500 mb-6 sm:mb-8">Speak locally on device. No internet required.</p>
                   
                   <div className="bg-gray-50 p-3.5 sm:p-4 rounded-xl mb-6 text-left border border-gray-200">
                     <div className="flex items-center justify-between mb-3">
                       <span className="font-semibold text-gray-700 text-xs sm:text-sm">Language:</span>
                       <select value={language} onChange={(e) => setLanguage(e.target.value)} className="border rounded-lg p-1.5 text-xs sm:text-sm bg-white">
                         <option value="english">English</option>
                         <option value="hindi">Hindi</option>
                         <option value="marathi">Marathi</option>
                         <option value="telugu">Telugu</option>
                       </select>
                     </div>
                     <div className="flex items-center justify-between">
                       <span className="font-semibold text-gray-700 text-xs sm:text-sm">Offline Voice Model:</span>
                       {modelReady ? (
                         <span className="text-emerald-600 text-xs sm:text-sm font-bold flex items-center gap-1"><Check size={14}/> Ready</span>
                       ) : modelLoading ? (
                         <span className="text-blue-600 text-xs sm:text-sm flex items-center gap-1"><RefreshCw size={14} className="animate-spin"/> {Math.round(modelProgress)}%</span>
                       ) : (
                         <button onClick={loadOfflineModel} className="text-xs bg-blue-100 hover:bg-blue-200 text-blue-800 px-3 py-1.5 rounded-lg font-bold flex items-center gap-1"><Download size={13}/> Download (~40MB)</button>
                       )}
                     </div>
                   </div>

                   <div className="flex flex-col sm:flex-row gap-3 sm:gap-4 justify-center">
                      <button onClick={isListening ? stopVoiceReporting : startVoiceReporting} disabled={!modelReady && !isListening} className={`px-6 py-4 rounded-2xl flex flex-col items-center gap-2 border-2 transition-all min-h-[90px] touch-manipulation ${!modelReady ? 'opacity-50 cursor-not-allowed border-gray-200' : isListening ? 'border-red-500 bg-red-50 animate-pulse' : 'border-blue-500 bg-blue-50 hover:bg-blue-100'}`}>
                         <Mic size={28} className={isListening ? 'text-red-500' : 'text-blue-500'} />
                         <span className="font-bold text-xs sm:text-sm text-gray-800">{isListening ? 'Stop & Process' : 'Start Voice Report'}</span>
                      </button>
                      <button onClick={nextStep} className="px-6 py-4 rounded-2xl flex flex-col items-center gap-2 border-2 border-gray-200 bg-gray-50 hover:bg-gray-100 transition-all min-h-[90px] touch-manipulation">
                         <Edit2 size={28} className="text-gray-500" />
                         <span className="font-bold text-xs sm:text-sm text-gray-800">Manual Entry</span>
                      </button>
                   </div>
                   {transcript && <div className="mt-4 p-3.5 bg-gray-100 rounded-xl text-gray-700 italic border border-gray-200 text-xs sm:text-sm text-left">{transcript}</div>}
                </div>
              )}

              {step === 2 && (
                <div className="space-y-4 sm:space-y-6">
                   <h2 className="text-lg sm:text-xl font-bold text-gray-800">Animal Information</h2>
                   <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                     <div>
                       <label className="text-xs sm:text-sm font-semibold text-gray-700">Species *</label>
                       <select value={formData.species} onChange={e => setFormData({...formData, species: e.target.value})} className="mt-1 block w-full rounded-xl border-gray-300 shadow-xs border p-2.5 text-xs sm:text-sm bg-white">
                         <option>Cattle</option><option>Buffalo</option><option>Goat</option><option>Sheep</option><option>Poultry</option><option>Pig</option>
                       </select>
                     </div>
                     <div>
                       <label className="text-xs sm:text-sm font-semibold text-gray-700">Gender</label>
                       <select value={formData.gender} onChange={e => setFormData({...formData, gender: e.target.value})} className="mt-1 block w-full rounded-xl border-gray-300 shadow-xs border p-2.5 text-xs sm:text-sm bg-white">
                         <option>Female</option><option>Male</option>
                       </select>
                     </div>
                     <div>
                       <label className="text-xs sm:text-sm font-semibold text-gray-700">Age (Years)</label>
                       <input type="number" value={formData.age} onChange={e => setFormData({...formData, age: toIntOrEmpty(e.target.value)})} className="mt-1 block w-full rounded-xl border-gray-300 shadow-xs border p-2.5 text-xs sm:text-sm" placeholder="e.g. 3" />
                       {errors.age && <p className="text-red-500 text-xs mt-1">{errors.age}</p>}
                     </div>
                     <div>
                       <label className="text-xs sm:text-sm font-semibold text-gray-700">Temperature (°C)</label>
                       <input type="number" step="0.1" value={formData.temperature} onChange={e => setFormData({...formData, temperature: toFloatOrEmpty(e.target.value)})} className="mt-1 block w-full rounded-xl border-gray-300 shadow-xs border p-2.5 text-xs sm:text-sm" placeholder="e.g. 39.5" />
                     </div>
                     <div>
                       <label className="text-xs sm:text-sm font-semibold text-gray-700">Number Affected *</label>
                       <input type="number" min="1" value={formData.numberAffected} onChange={e => setFormData({...formData, numberAffected: toIntOrEmpty(e.target.value)})} className="mt-1 block w-full rounded-xl border-gray-300 shadow-xs border p-2.5 text-xs sm:text-sm" />
                       {errors.numberAffected && <p className="text-red-500 text-xs mt-1">{errors.numberAffected}</p>}
                     </div>
                     <div>
                       <label className="text-xs sm:text-sm font-semibold text-gray-700">Number Dead *</label>
                       <input type="number" min="0" value={formData.numberDead} onChange={e => setFormData({...formData, numberDead: toIntOrEmpty(e.target.value)})} className="mt-1 block w-full rounded-xl border-gray-300 shadow-xs border p-2.5 text-xs sm:text-sm" />
                       {errors.numberDead && <p className="text-red-500 text-xs mt-1">{errors.numberDead}</p>}
                     </div>
                   </div>
                </div>
              )}

              {step === 3 && (
                <div className="space-y-4 sm:space-y-6">
                   <h2 className="text-lg sm:text-xl font-bold text-gray-800">Symptoms</h2>
                   {errors.symptoms && <p className="text-red-500 text-xs sm:text-sm">{errors.symptoms}</p>}
                   <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2.5 max-h-96 overflow-y-auto p-1">
                     {mlSymptoms.map(sym => (
                       <label key={sym} className={`flex items-center gap-2 p-2.5 border rounded-xl cursor-pointer transition-colors touch-manipulation min-h-[44px] ${formData.symptoms.includes(sym) ? 'bg-blue-50 border-blue-500 text-blue-900 font-bold' : 'hover:bg-gray-50 text-gray-700'}`}>
                         <input type="checkbox" checked={formData.symptoms.includes(sym)} onChange={() => {
                            setFormData(prev => ({...prev, symptoms: prev.symptoms.includes(sym) ? prev.symptoms.filter(s => s !== sym) : [...prev.symptoms, sym]}))
                         }} className="rounded text-brandBlue focus:ring-brandBlue w-4 h-4 shrink-0" />
                         <span className="text-xs sm:text-sm capitalize">{sym.replace(/_/g, ' ')}</span>
                       </label>
                     ))}
                   </div>
                </div>
              )}

              {step === 4 && (
                <div className="space-y-4 sm:space-y-6">
                   <h2 className="text-lg sm:text-xl font-bold text-gray-800">Location Details</h2>
                   <button onClick={useCurrentLocation} className="w-full py-3 bg-gray-100 hover:bg-gray-200 text-gray-800 rounded-xl flex items-center justify-center gap-2 font-bold text-xs sm:text-sm touch-manipulation min-h-[44px]">
                      <MapPin size={18} /> Use Current GPS Location
                   </button>
                   {transcript && <p className="text-xs sm:text-sm text-green-600 text-center">{transcript}</p>}
                   <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-2">
                     <div>
                       <label className="text-xs sm:text-sm font-semibold text-gray-700">State</label>
                       <input type="text" value={formData.state || "Maharashtra"} onChange={e => setFormData({...formData, state: e.target.value})} className="mt-1 block w-full rounded-xl border border-gray-300 p-2.5 text-xs sm:text-sm" />
                     </div>
                     <div>
                       <label className="text-xs sm:text-sm font-semibold text-gray-700">District *</label>
                       <input type="text" list="district-options" value={formData.district} onChange={e => setFormData({...formData, district: e.target.value})} className="mt-1 block w-full rounded-xl border border-gray-300 p-2.5 text-xs sm:text-sm" placeholder="e.g. Pune" />
                       <datalist id="district-options">
                         {DISTRICT_NAMES.map(district => (
                           <option key={district} value={district} />
                         ))}
                       </datalist>
                     </div>
                     <div className="sm:col-span-2">
                       <label className="text-xs sm:text-sm font-semibold text-gray-700">Village / Town *</label>
                       <input type="text" value={formData.village} onChange={e => setFormData({...formData, village: e.target.value})} className="mt-1 block w-full rounded-xl border border-gray-300 p-2.5 text-xs sm:text-sm" placeholder="e.g. Shirur" />
                     </div>
                   </div>
                </div>
              )}

              {step === 5 && (
                <div className="space-y-4 sm:space-y-6 text-center">
                   <h2 className="text-lg sm:text-xl font-bold text-gray-800">AI Risk Assessment</h2>
                   <p className="text-xs sm:text-sm text-gray-500">Run diagnostic inference based on the {formData.symptoms.length} symptoms selected.</p>
                   
                   {!predictionResult ? (
                     <button onClick={handlePredictDisease} disabled={isPredicting} className="bg-purple-600 hover:bg-purple-700 text-white px-6 py-3.5 rounded-xl font-bold flex items-center gap-2 mx-auto text-xs sm:text-sm shadow-xs touch-manipulation">
                       {isPredicting ? <RefreshCw className="animate-spin" size={16} /> : "✨ Run Local AI Prediction"}
                     </button>
                   ) : (
                     <div className="bg-purple-50 border border-purple-200 rounded-2xl p-4 sm:p-6 text-left">
                       <div className="mb-2"><span className="bg-purple-200 text-purple-900 text-[10px] font-bold px-2 py-0.5 rounded">LOCAL INFERENCE</span></div>
                       <h3 className="text-base sm:text-lg font-black text-purple-900">{predictionResult.disease}</h3>
                       <div className="flex items-center gap-2 mt-2">
                         <div className="w-full bg-purple-200 rounded-full h-2"><div className="bg-purple-600 h-2 rounded-full" style={{width: `${predictionResult.confidence}%`}}></div></div>
                         <span className="text-xs sm:text-sm font-bold text-purple-700">{predictionResult.confidence}%</span>
                       </div>
                       <p className="mt-3 text-xs sm:text-sm text-gray-700"><strong>About:</strong> {predictionResult.description}</p>
                       <p className="mt-1 text-xs sm:text-sm text-gray-700"><strong>Local Remedies:</strong> {predictionResult.remedies}</p>
                       <div className="mt-3 bg-white p-3 rounded-xl border border-purple-100 flex items-start gap-2.5">
                          <AlertTriangle className="text-orange-500 shrink-0 mt-0.5" size={16} />
                          <p className="text-xs sm:text-sm text-gray-800"><strong>Action Required:</strong> {predictionResult.action}</p>
                       </div>
                     </div>
                   )}
                </div>
              )}

              {step === 6 && (
                <div className="space-y-4 sm:space-y-6">
                   <h2 className="text-lg sm:text-xl font-bold text-gray-800 border-b pb-2">Review & Submit</h2>
                   <div className="bg-gray-50 p-4 rounded-xl space-y-2 text-xs sm:text-sm">
                     <p><strong>Species:</strong> {formData.species} ({formData.gender}, {formData.age || "N/A"} yrs)</p>
                     <p><strong>Affected:</strong> {formData.numberAffected} | <strong>Dead:</strong> <span className="text-red-600 font-bold">{formData.numberDead}</span></p>
                     <p><strong>Symptoms:</strong> {formData.symptoms.join(', ') || 'None'}</p>
                     <p><strong>Location:</strong> {formData.village || 'N/A'}, {formData.district || 'N/A'}</p>
                     <p><strong>Suspected Disease:</strong> {formData.disease}</p>
                   </div>
                   {!isOnline && (
                     <div className="bg-amber-50 border border-amber-200 text-amber-900 p-3 rounded-xl text-xs flex items-center gap-2">
                       <Save size={16} className="text-amber-600 shrink-0"/> 
                       <span>Device is offline. Report will be saved to IndexedDB queue with client idempotency key and synced automatically when connected.</span>
                     </div>
                   )}
                </div>
              )}

              <div className="flex justify-between mt-6 sm:mt-8 border-t pt-4">
                 {step > 1 ? (
                   <button onClick={prevStep} className="px-5 py-2 border border-gray-300 rounded-xl text-gray-700 hover:bg-gray-50 text-xs sm:text-sm font-semibold touch-manipulation min-h-[40px]">Back</button>
                 ) : <div />}
                 
                 {step < 6 ? (
                   <button onClick={nextStep} className="px-6 py-2 bg-brandBlue text-white rounded-xl hover:bg-blue-600 text-xs sm:text-sm font-bold shadow-xs touch-manipulation min-h-[40px]">Next</button>
                 ) : (
                   <button onClick={handleSubmit} className="px-6 py-2 bg-green-600 text-white rounded-xl hover:bg-green-700 font-bold flex items-center gap-2 text-xs sm:text-sm shadow-xs touch-manipulation min-h-[40px]">
                     <CheckCircle size={18} /> Submit Report
                   </button>
                 )}
              </div>
            </div>
          </div>
        )}

        {(activeTab === 'My Reports' || activeTab === 'Report History') && (
          <div className="max-w-6xl mx-auto w-full space-y-4">
            <div className="flex justify-between items-center">
              <h2 className="text-base sm:text-lg font-bold text-gray-800">{activeTab}</h2>
              {pendingQueueReports.length > 0 && (
                <button
                  onClick={openSyncModal}
                  className="px-3 py-1 bg-amber-100 hover:bg-amber-200 text-amber-900 rounded-lg text-xs font-bold flex items-center gap-1.5"
                >
                  <Database size={13} />
                  <span>Pending Sync ({pendingQueueReports.length})</span>
                </button>
              )}
            </div>
            
            {pendingQueueReports.length > 0 && activeTab === 'My Reports' && (
              <div className="mb-4">
                <h3 className="text-xs sm:text-sm font-bold text-gray-700 mb-2">Offline Queue (Pending Sync in IndexedDB)</h3>
                <div className="bg-amber-50 border border-amber-200 rounded-2xl overflow-x-auto shadow-2xs">
                  <table className="min-w-full divide-y divide-amber-200 text-xs">
                    <thead className="bg-amber-100/70 text-amber-900 font-bold uppercase">
                      <tr>
                        <th className="px-4 py-2.5 text-left">Status</th>
                        <th className="px-4 py-2.5 text-left">Client UUID</th>
                        <th className="px-4 py-2.5 text-left">Species</th>
                        <th className="px-4 py-2.5 text-left">Disease</th>
                        <th className="px-4 py-2.5 text-left">Location</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-amber-200/60 bg-amber-50/50">
                      {pendingQueueReports.map((q) => (
                        <tr key={q.localId}>
                          <td className="px-4 py-2.5 whitespace-nowrap">
                            <span className="px-2 py-0.5 inline-flex text-[10px] font-bold rounded-full bg-amber-200 text-amber-900 items-center gap-1">
                              <WifiOff size={10}/> Pending Sync
                            </span>
                          </td>
                          <td className="px-4 py-2.5 whitespace-nowrap text-gray-700 font-mono text-[10px]">{q.id}</td>
                          <td className="px-4 py-2.5 whitespace-nowrap text-gray-900 font-semibold">{q.data?.species || "Cattle"}</td>
                          <td className="px-4 py-2.5 whitespace-nowrap text-purple-800 font-bold">{q.data?.disease || "Unknown"}</td>
                          <td className="px-4 py-2.5 whitespace-nowrap text-gray-600">{q.data?.village || "Offline"}, {q.data?.district || "Pune"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {reports.length === 0 ? (
              <div className="bg-white p-8 rounded-2xl border border-gray-200 text-center text-gray-500 shadow-2xs">
                No submitted reports found.
              </div>
            ) : (
              <div className="bg-white rounded-2xl border border-gray-200 overflow-x-auto shadow-2xs custom-scrollbar">
                <table className="min-w-full divide-y divide-gray-200 text-xs">
                  <thead className="bg-gray-50 text-gray-600 font-bold uppercase tracking-wider">
                    <tr>
                      <th className="px-4 sm:px-6 py-3 text-left">Date</th>
                      <th className="px-4 sm:px-6 py-3 text-left">Location</th>
                      <th className="px-4 sm:px-6 py-3 text-left">Species</th>
                      <th className="px-4 sm:px-6 py-3 text-left">Disease</th>
                      <th className="px-4 sm:px-6 py-3 text-left">Affected/Dead</th>
                      <th className="px-4 sm:px-6 py-3 text-left">Status</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-100">
                    {reports.map((report) => (
                      <tr key={report.id} className="hover:bg-gray-50">
                        <td className="px-4 sm:px-6 py-3.5 whitespace-nowrap text-gray-500 font-mono">{report.date}</td>
                        <td className="px-4 sm:px-6 py-3.5 whitespace-nowrap text-gray-900 font-medium">{report.village}, {report.district}</td>
                        <td className="px-4 sm:px-6 py-3.5 whitespace-nowrap text-gray-600">{report.species}</td>
                        <td className="px-4 sm:px-6 py-3.5 whitespace-nowrap font-bold text-purple-700">{report.disease || 'Unknown'}</td>
                        <td className="px-4 sm:px-6 py-3.5 whitespace-nowrap text-gray-600">{report.numberAffected} / <span className={report.numberDead > 0 ? 'text-red-600 font-bold' : ''}>{report.numberDead}</span></td>
                        <td className="px-4 sm:px-6 py-3.5 whitespace-nowrap">
                          <span className={`px-2.5 py-0.5 inline-flex text-[10px] font-bold rounded-full ${
                            report.status === 'Suspected' ? 'bg-red-100 text-red-800' :
                            report.status === 'SUBMITTED' ? 'bg-blue-100 text-blue-800' :
                            report.status === 'QUEUED' ? 'bg-amber-100 text-amber-800' :
                            'bg-green-100 text-green-800'
                          }`}>
                            {report.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
