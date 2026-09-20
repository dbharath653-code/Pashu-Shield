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
  refreshSamples: () => Promise<void>;
}

const LabContext = createContext<LabContextType | undefined>(undefined);

export function LabProvider({ children }: { children: React.ReactNode }) {
  const [samples, setSamples] = useState<LabSample[]>([]);

  const loadData = async () => {
    await dbService.init();

    // Try online API fetch
    try {
      const token = localStorage.getItem("auth_token");
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const res = await fetch("/api/v1/labs/samples", { headers });
      if (res.ok) {
        const apiSamples = await res.json();
        if (Array.isArray(apiSamples) && apiSamples.length > 0) {
          for (const s of apiSamples) {
            await dbService.save("lab_samples", s);
          }
          setSamples(apiSamples);
          return;
        }
      }
    } catch {
      // offline fallback
    }

    const loadedSamples = await dbService.getAll("lab_samples");
    if (loadedSamples.length > 0) {
      setSamples(loadedSamples);
    }
  };

  useEffect(() => {
    loadData();

    const handleRealtime = (e: any) => {
      const ev = e.detail;
      if (ev?.type === "LAB_SAMPLE_COLLECTED" || ev?.type === "SAMPLE_STATUS_CHANGED" || ev?.type === "LAB_RESULT_VERIFIED") {
        loadData();
      }
    };
    window.addEventListener("pashu_realtime_event", handleRealtime);
    return () => window.removeEventListener("pashu_realtime_event", handleRealtime);
  }, []);

  const addSample = async (sample: LabSample) => {
    await dbService.save("lab_samples", sample);
    setSamples(prev => [sample, ...prev]);

    try {
      const token = localStorage.getItem("auth_token");
      await fetch("/api/v1/labs/samples", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {})
        },
        body: JSON.stringify({
          case_id: sample.caseId,
          animal_id: sample.animalId,
          species: sample.species,
          disease_suspected: sample.diseaseSuspected,
          sample_type: sample.sampleType,
          priority: sample.priority,
          district: sample.district || "Pune",
          location: sample.location,
          tests: sample.tests?.map(t => t.testName) || ["RT-PCR"]
        })
      });
    } catch {
      // Fallback in IndexedDB
    }
  };

  const updateSample = async (sample: LabSample) => {
    await dbService.save("lab_samples", sample);
    setSamples(prev => prev.map(s => s.id === sample.id ? sample : s));

    try {
      const token = localStorage.getItem("auth_token");
      await fetch(`/api/v1/labs/samples/${sample.id}/status`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {})
        },
        body: JSON.stringify({ status: sample.status })
      });
    } catch {
      // Offline fallback
    }
  };

  return (
    <LabContext.Provider value={{ samples, addSample, updateSample, refreshSamples: loadData }}>
      {children}
    </LabContext.Provider>
  );
}

export function useLab() {
  const context = useContext(LabContext);
  if (context === undefined) throw new Error("useLab must be used within LabProvider");
  return context;
}
