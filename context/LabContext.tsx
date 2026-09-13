import React, { createContext, useContext, useState, useEffect } from "react";
import { dbService } from "../services/db/IndexedDBService";

export interface LabTest {
  id: string;
  testName: string;
  status: "Pending" | "In Progress" | "Completed" | "Failed";
  result?: "Negative" | "Positive" | "Inconclusive" | "Invalid";
  value?: string;
  remarks?: string;
}

export interface LabSample {
  id: string;
  caseId?: string;
  animalId?: string;
  species: string;
  diseaseSuspected: string;
  sampleType: string;
  priority: "Routine" | "Urgent" | "Critical";
  status: "Collected" | "In Transit" | "Received" | "Accepted" | "Rejected" | "Testing" | "Result Pending" | "Verified" | "Closed";
  collectionDate: string;
  location: string;
  district: string;
  tests: LabTest[];
  syncStatus: "Pending" | "Synced";
  verification?: {
    verifiedBy: string;
    date: string;
    remarks: string;
  };
}

interface LabContextType {
  samples: LabSample[];
  addSample: (sample: LabSample) => Promise<void>;
  updateSample: (sample: LabSample) => Promise<void>;
}

const LabContext = createContext<LabContextType | undefined>(undefined);

export function LabProvider({ children }: { children: React.ReactNode }) {
  const [samples, setSamples] = useState<LabSample[]>([]);

  useEffect(() => {
    const loadData = async () => {
      await dbService.init();
      const loadedSamples = await dbService.getAll("lab_samples");
      
      if (loadedSamples.length === 0) {
        const mockSamples: LabSample[] = [
          {
            id: "MH-LAB-2026-000001",
            caseId: "VET-2026-004821",
            animalId: "MH-PUN-CAT-001",
            species: "Cattle",
            diseaseSuspected: "Foot-and-Mouth Disease",
            sampleType: "Blood",
            priority: "Urgent",
            status: "Testing",
            collectionDate: new Date().toISOString(),
            location: "Shirur",
            district: "Pune",
            tests: [{ id: "T-1", testName: "FMD RT-PCR", status: "In Progress" }],
            syncStatus: "Synced"
          },
          {
            id: "MH-LAB-2026-000002",
            caseId: "VET-2026-004822",
            animalId: "HRD-NAS-009",
            species: "Goat",
            diseaseSuspected: "PPR",
            sampleType: "Nasal Swab",
            priority: "Critical",
            status: "Result Pending",
            collectionDate: new Date(Date.now() - 86400000).toISOString(),
            location: "Sinnar",
            district: "Nashik",
            tests: [{ id: "T-2", testName: "PPR PCR", status: "Completed", result: "Positive", value: "Ct 22.4" }],
            syncStatus: "Synced"
          }
        ];
        for (const s of mockSamples) {
          await dbService.save("lab_samples", s);
        }
        setSamples(mockSamples);
      } else {
        setSamples(loadedSamples);
      }
    };
    loadData();
  }, []);

  const addSample = async (sample: LabSample) => {
    await dbService.save("lab_samples", sample);
    setSamples(prev => [sample, ...prev]);
  };

  const updateSample = async (sample: LabSample) => {
    await dbService.save("lab_samples", sample);
    setSamples(prev => prev.map(s => s.id === sample.id ? sample : s));
  };

  return (
    <LabContext.Provider value={{ samples, addSample, updateSample }}>
      {children}
    </LabContext.Provider>
  );
}

export function useLab() {
  const context = useContext(LabContext);
  if (context === undefined) throw new Error("useLab must be used within Provider");
  return context;
}

