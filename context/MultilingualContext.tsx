import React, { createContext, useContext, useState, useEffect } from "react";
import { en } from "../locales/en";
import { mr } from "../locales/mr";
import { dbService } from "../services/db/IndexedDBService";

type LanguageCode = "en" | "mr" | "hi" | "te" | "kn" | "gu" | "ta" | "bn";

const dictionaries: Record<string, Record<string, string>> = {
  en,
  mr,
};

interface VoiceReport {
  id: string;
  animalId: string;
  location: string;
  originalLanguage: string;
  originalText: string;
  translatedText: string;
  timestamp: string;
  officerId: string;
  syncStatus: "Pending" | "Synced";
}

interface MultilingualContextType {
  language: LanguageCode;
  setLanguage: (lang: LanguageCode) => void;
  t: (key: string) => string;
  isSpeechAvailable: boolean;
  translateText: (text: string, source: string, target: string) => Promise<string>;
  saveVoiceReport: (report: VoiceReport) => Promise<void>;
  speak: (text: string, lang?: string) => void;
  stopSpeaking: () => void;
}

const MultilingualContext = createContext<MultilingualContextType | undefined>(undefined);

export function MultilingualProvider({ children }: { children: React.ReactNode }) {
  const [language, setLanguageState] = useState<LanguageCode>("en");

  useEffect(() => {
    const saved = localStorage.getItem("app_lang") as LanguageCode;
    if (saved) setLanguageState(saved);
  }, []);

  const setLanguage = (lang: LanguageCode) => {
    setLanguageState(lang);
    localStorage.setItem("app_lang", lang);
  };

  const t = (key: string): string => {
    const dict = dictionaries[language] || dictionaries["en"];
    return dict[key] || dictionaries["en"][key] || key;
  };

  const isSpeechAvailable = "webkitSpeechRecognition" in window || "SpeechRecognition" in window;

  const translateText = async (text: string, _source: string, target: string): Promise<string> => {
    // Simulated translation service fallback
    return new Promise(resolve => {
      setTimeout(() => {
        resolve(`[Translated to ${target}]: ${text}`);
      }, 600);
    });
  };

  const saveVoiceReport = async (report: VoiceReport) => {
    await dbService.init();
    await dbService.save("voice_reports", report);
  };

  const speak = (text: string, lang: string = language) => {
    if (!("speechSynthesis" in window)) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    
    // Attempt to map our codes to BCP 47
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
    utterance.lang = langMap[lang] || "en-US";
    window.speechSynthesis.speak(utterance);
  };

  const stopSpeaking = () => {
    if ("speechSynthesis" in window) {
      window.speechSynthesis.cancel();
    }
  };

  return (
    <MultilingualContext.Provider value={{ language, setLanguage, t, isSpeechAvailable, translateText, saveVoiceReport, speak, stopSpeaking }}>
      {children}
    </MultilingualContext.Provider>
  );
}

export function useMultilingual() {
  const context = useContext(MultilingualContext);
  if (context === undefined) throw new Error("useMultilingual must be used within Provider");
  return context;
}

