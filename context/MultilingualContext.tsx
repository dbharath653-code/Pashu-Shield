import React, { createContext, useContext, useState, useEffect } from "react";
import { en } from "../locales/en";
import { mr } from "../locales/mr";
import { hi } from "../locales/hi";
import { te } from "../locales/te";
import { kn } from "../locales/kn";
import { gu } from "../locales/gu";
import { ta } from "../locales/ta";
import { bn } from "../locales/bn";
import { dbService } from "../services/db/IndexedDBService";

export type LanguageCode = "en" | "mr" | "hi" | "te" | "kn" | "gu" | "ta" | "bn";

export const LANGUAGE_NAMES: Record<LanguageCode, { label: string; native: string }> = {
  en: { label: "English", native: "English" },
  mr: { label: "Marathi", native: "मराठी" },
  hi: { label: "Hindi", native: "हिन्दी" },
  te: { label: "Telugu", native: "తెలుగు" },
  kn: { label: "Kannada", native: "ಕನ್ನಡ" },
  gu: { label: "Gujarati", native: "ગુજરાતી" },
  ta: { label: "Tamil", native: "தமிழ்" },
  bn: { label: "Bengali", native: "বাংলা" }
};

const dictionaries: Record<LanguageCode, Record<string, string>> = {
  en,
  mr,
  hi,
  te,
  kn,
  gu,
  ta,
  bn
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
    if (saved && dictionaries[saved]) setLanguageState(saved);
  }, []);

  const setLanguage = (lang: LanguageCode) => {
    setLanguageState(lang);
    localStorage.setItem("app_lang", lang);
  };

  const t = (key: string): string => {
    const dict = dictionaries[language] || dictionaries["en"];
    return dict[key] || dictionaries["en"][key] || key;
  };

  const isSpeechAvailable = typeof window !== "undefined" && ("webkitSpeechRecognition" in window || "SpeechRecognition" in window);

  const translateText = async (text: string, source: string, target: string): Promise<string> => {
    try {
      const res = await fetch("/api/v1/voice/translate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, source_lang: source, target_lang: target })
      });
      if (res.ok) {
        const data = await res.json();
        return data.translated_text || text;
      }
    } catch {
      // Fallback
    }
    return text;
  };

  const saveVoiceReport = async (report: VoiceReport) => {
    await dbService.init();
    await dbService.save("voice_reports", report);
  };

  const speak = (text: string, lang: string = language) => {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    
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
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
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
