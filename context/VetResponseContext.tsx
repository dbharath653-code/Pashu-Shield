import React, { createContext, useContext, useState, useEffect } from "react";
import { dbService } from "../services/db/IndexedDBService";

export interface VetCase {
  id: string;
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
}

const VetResponseContext = createContext<VetResponseContextType | undefined>(undefined);

export function VetResponseProvider({ children }: { children: React.ReactNode }) {
  const [cases, setCases] = useState<VetCase[]>([]);

  useEffect(() => {
    const loadData = async () => {
      await dbService.init();
      const loadedCases = await dbService.getAll("vet_cases");
      
      if (loadedCases.length === 0) {
        const mockCases: VetCase[] = [
          {
            id: "VET-2026-004821",
            animalHerdId: "MH-PUN-CAT-001",
            species: "Cattle",
            location: "Shirur, Pune",
            reportedProblem: "High fever and reduced appetite",
            riskScore: 72,
            priority: "HIGH",
            reportedAt: new Date().toISOString(),
            assignedVet: "Dr. Sharma",
            status: "Assigned",
            syncStatus: "Synced"
          },
          {
            id: "VET-2026-004822",
            animalHerdId: "HRD-NAS-009",
            species: "Goat",
            location: "Sinnar, Nashik",
            reportedProblem: "Sudden mortality in 3 kids",
            riskScore: 95,
            priority: "CRITICAL",
            reportedAt: new Date(Date.now() - 3600000).toISOString(),
            assignedVet: null,
            status: "Pending",
            syncStatus: "Synced"
          }
        ];
        for (const c of mockCases) {
          await dbService.save("vet_cases", c);
        }
        setCases(mockCases);
      } else {
        setCases(loadedCases);
      }
    };
    loadData();
  }, []);

  const addCase = async (vetCase: VetCase) => {
    await dbService.save("vet_cases", vetCase);
    setCases(prev => [vetCase, ...prev]);
  };

  const updateCase = async (vetCase: VetCase) => {
    await dbService.save("vet_cases", vetCase);
    setCases(prev => prev.map(c => c.id === vetCase.id ? vetCase : c));
  };

  return (
    <VetResponseContext.Provider value={{ cases, addCase, updateCase }}>
      {children}
    </VetResponseContext.Provider>
  );
}

export function useVetResponse() {
  const context = useContext(VetResponseContext);
  if (context === undefined) throw new Error("useVetResponse must be used within Provider");
  return context;
}

