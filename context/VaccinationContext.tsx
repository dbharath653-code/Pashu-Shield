import React, { createContext, useContext, useState, useEffect } from "react";
import { dbService } from "../services/db/IndexedDBService";

export interface VaccinationCampaign {
  id: string;
  name: string;
  disease: string;
  vaccine: string;
  species: string[];
  targetDistricts: string[];
  startDate: string;
  endDate: string;
  status: "Draft" | "Planned" | "Active" | "Paused" | "Completed" | "Cancelled";
  targetPopulation: number;
  coverageTargetPercent: number;
}

export interface VaccinationRecord {
  id: string;
  animalId: string;
  herdId?: string;
  species: string;
  disease: string;
  vaccine: string;
  batchNumber: string;
  vaccinationDate: string;
  nextDueDate: string;
  campaignId?: string;
  location: string;
  district: string;
  provider: string;
  syncStatus: "Pending" | "Synced";
}

interface VaccinationContextType {
  campaigns: VaccinationCampaign[];
  vaccinations: VaccinationRecord[];
  addCampaign: (c: VaccinationCampaign) => Promise<void>;
  updateCampaign: (c: VaccinationCampaign) => Promise<void>;
  addVaccination: (v: VaccinationRecord) => Promise<void>;
}

const VaccinationContext = createContext<VaccinationContextType | undefined>(undefined);

export function VaccinationProvider({ children }: { children: React.ReactNode }) {
  const [campaigns, setCampaigns] = useState<VaccinationCampaign[]>([]);
  const [vaccinations, setVaccinations] = useState<VaccinationRecord[]>([]);

  useEffect(() => {
    const loadData = async () => {
      await dbService.init();
      const loadedCampaigns = await dbService.getAll("vaccination_campaigns");
      const loadedVaccinations = await dbService.getAll("vaccinations");

      if (loadedCampaigns.length === 0) {
        const mockCampaign: VaccinationCampaign = {
          id: "CAMP-MH-2026-FMD",
          name: "Maharashtra State FMD Drive",
          disease: "Foot-and-Mouth Disease",
          vaccine: "Raksha Ovac",
          species: ["Cattle", "Buffalo"],
          targetDistricts: ["Pune", "Nashik", "Satara", "Sangli"],
          startDate: new Date(Date.now() - 30 * 86400000).toISOString(), // 30 days ago
          endDate: new Date(Date.now() + 60 * 86400000).toISOString(),
          status: "Active",
          targetPopulation: 1500000,
          coverageTargetPercent: 95
        };
        await dbService.save("vaccination_campaigns", mockCampaign);
        setCampaigns([mockCampaign]);
      } else {
        setCampaigns(loadedCampaigns);
      }

      if (loadedVaccinations.length === 0) {
        const mockVaccination: VaccinationRecord = {
          id: "VAC-2026-0001",
          animalId: "MH-PUN-CAT-001",
          species: "Cattle",
          disease: "Foot-and-Mouth Disease",
          vaccine: "Raksha Ovac",
          batchNumber: "B-2026-04",
          vaccinationDate: new Date(Date.now() - 10 * 86400000).toISOString(),
          nextDueDate: new Date(Date.now() + 170 * 86400000).toISOString(), // ~6 months
          campaignId: "CAMP-MH-2026-FMD",
          location: "Shirur",
          district: "Pune",
          provider: "Dr. Sharma",
          syncStatus: "Synced"
        };
        await dbService.save("vaccinations", mockVaccination);
        setVaccinations([mockVaccination]);
      } else {
        setVaccinations(loadedVaccinations);
      }
    };
    loadData();
  }, []);

  const addCampaign = async (c: VaccinationCampaign) => {
    await dbService.save("vaccination_campaigns", c);
    setCampaigns(prev => [c, ...prev]);
  };

  const updateCampaign = async (c: VaccinationCampaign) => {
    await dbService.save("vaccination_campaigns", c);
    setCampaigns(prev => prev.map(camp => camp.id === c.id ? c : camp));
  };

  const addVaccination = async (v: VaccinationRecord) => {
    await dbService.save("vaccinations", v);
    setVaccinations(prev => [v, ...prev]);
  };

  return (
    <VaccinationContext.Provider value={{ campaigns, vaccinations, addCampaign, updateCampaign, addVaccination }}>
      {children}
    </VaccinationContext.Provider>
  );
}

export function useVaccination() {
  const context = useContext(VaccinationContext);
  if (context === undefined) throw new Error("useVaccination must be used within Provider");
  return context;
}

