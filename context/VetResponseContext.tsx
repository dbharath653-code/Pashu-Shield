import React, { createContext, useContext, useState, useEffect } from "react";
import { dbService } from "../services/db/IndexedDBService";

export interface VetCase {
  id: string;
  caseNumber?: string;
  animalHerdId: string;
  species: string;
  location: string;
  reportedProblem: string;
  riskScore: number;
  priority: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  reportedAt: string;
  assignedVet: string | null;
  status: "Pending" | "Assigned" | "En Route" | "Under Examination" | "Treatment Active" | "Closed";
  syncStatus: "Pending" | "Synced";
}

interface VetResponseContextType {
  cases: VetCase[];
  addCase: (vetCase: VetCase) => Promise<void>;
  updateCase: (vetCase: VetCase) => Promise<void>;
  refreshCases: () => Promise<void>;
}

const VetResponseContext = createContext<VetResponseContextType | undefined>(undefined);

export function VetResponseProvider({ children }: { children: React.ReactNode }) {
  const [cases, setCases] = useState<VetCase[]>([]);

  const loadData = async () => {
    await dbService.init();

    // Try online API fetch first
    try {
      const token = localStorage.getItem("auth_token");
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const res = await fetch("/api/v1/cases", { headers });
      if (res.ok) {
        const apiCases = await res.json();
        if (Array.isArray(apiCases) && apiCases.length > 0) {
          const mappedCases: VetCase[] = apiCases.map((c: any) => ({
            id: c.id,
            caseNumber: c.caseNumber,
            animalHerdId: c.animalHerdId,
            species: c.species,
            location: c.location,
            reportedProblem: c.reportedProblem,
            riskScore: c.riskScore,
            priority: c.priority,
            reportedAt: c.reportedAt,
            assignedVet: c.assignedVet,
            status: c.status,
            syncStatus: "Synced"
          }));

          for (const c of mappedCases) {
            await dbService.save("vet_cases", c);
          }
          setCases(mappedCases);
          return;
        }
      }
    } catch {
      // offline fallback to IndexedDB
    }

    const loadedCases = await dbService.getAll("vet_cases");
    if (loadedCases.length > 0) {
      setCases(loadedCases);
    }
  };

  useEffect(() => {
    loadData();

    // Listen to real-time WebSocket events
    const handleRealtime = (e: any) => {
      const ev = e.detail;
      if (ev?.type === "CASE_CREATED" || ev?.type === "CASE_STATUS_CHANGED") {
        loadData();
      }
    };
    window.addEventListener("pashu_realtime_event", handleRealtime);
    return () => window.removeEventListener("pashu_realtime_event", handleRealtime);
  }, []);

  const addCase = async (vetCase: VetCase) => {
    await dbService.save("vet_cases", vetCase);
    setCases(prev => [vetCase, ...prev]);
  };

  const updateCase = async (vetCase: VetCase) => {
    await dbService.save("vet_cases", vetCase);
    setCases(prev => prev.map(c => (c.id === vetCase.id ? vetCase : c)));

    // Sync to backend API if online
    try {
      const token = localStorage.getItem("auth_token");
      await fetch(`/api/v1/cases/${vetCase.id}/status`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {})
        },
        body: JSON.stringify({ status: vetCase.status })
      });
    } catch {
      // Offline fallback already in IndexedDB
    }
  };

  return (
    <VetResponseContext.Provider value={{ cases, addCase, updateCase, refreshCases: loadData }}>
      {children}
    </VetResponseContext.Provider>
  );
}

export function useVetResponse() {
  const context = useContext(VetResponseContext);
  if (context === undefined) throw new Error("useVetResponse must be used within Provider");
  return context;
}
