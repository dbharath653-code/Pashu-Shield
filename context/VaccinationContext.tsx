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
  refreshVaccinations: () => Promise<void>;
}

const VaccinationContext = createContext<VaccinationContextType | undefined>(undefined);

export function VaccinationProvider({ children }: { children: React.ReactNode }) {
  const [campaigns, setCampaigns] = useState<VaccinationCampaign[]>([]);
  const [vaccinations, setVaccinations] = useState<VaccinationRecord[]>([]);

  const loadData = async () => {
    await dbService.init();

    try {
      const token = localStorage.getItem("auth_token");
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const [cRes, vRes] = await Promise.all([
        fetch("/api/v1/vaccination/campaigns", { headers }),
        fetch("/api/v1/vaccination/records", { headers })
      ]);

      if (cRes.ok) {
        const apiC = await cRes.json();
        if (Array.isArray(apiC) && apiC.length > 0) {
          for (const c of apiC) await dbService.save("vaccination_campaigns", c);
          setCampaigns(apiC);
        }
      }

      if (vRes.ok) {
        const apiV = await vRes.json();
        if (Array.isArray(apiV) && apiV.length > 0) {
          for (const v of apiV) await dbService.save("vaccinations", v);
          setVaccinations(apiV);
        }
      }
    } catch {
      // Offline fallback
    }

    const loadedC = await dbService.getAll("vaccination_campaigns");
    if (loadedC.length > 0) setCampaigns(loadedC);

    const loadedV = await dbService.getAll("vaccinations");
    if (loadedV.length > 0) setVaccinations(loadedV);
  };

  useEffect(() => {
    loadData();
  }, []);

  const addCampaign = async (campaign: VaccinationCampaign) => {
    await dbService.save("vaccination_campaigns", campaign);
    setCampaigns(prev => [campaign, ...prev]);

    try {
      const token = localStorage.getItem("auth_token");
      await fetch("/api/v1/vaccination/campaigns", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {})
        },
        body: JSON.stringify({
          name: campaign.name,
          disease: campaign.disease,
          vaccine: campaign.vaccine,
          species: campaign.species,
          target_districts: campaign.targetDistricts,
          start_date: new Date(campaign.startDate).toISOString(),
          end_date: new Date(campaign.endDate).toISOString(),
          target_population: campaign.targetPopulation,
          coverage_target_percent: campaign.coverageTargetPercent
        })
      });
    } catch {
      // Offline fallback
    }
  };

  const updateCampaign = async (campaign: VaccinationCampaign) => {
    await dbService.save("vaccination_campaigns", campaign);
    setCampaigns(prev => prev.map(c => c.id === campaign.id ? campaign : c));
  };

  const addVaccination = async (vaccination: VaccinationRecord) => {
    await dbService.save("vaccinations", vaccination);
    setVaccinations(prev => [vaccination, ...prev]);

    try {
      const token = localStorage.getItem("auth_token");
      await fetch("/api/v1/vaccination/records", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {})
        },
        body: JSON.stringify({
          animal_id: vaccination.animalId,
          species: vaccination.species,
          disease: vaccination.disease,
          vaccine: vaccination.vaccine,
          batch_number: vaccination.batchNumber,
          vaccination_date: new Date(vaccination.vaccinationDate).toISOString(),
          district: vaccination.district,
          location: vaccination.location
        })
      });
    } catch {
      // Offline fallback
    }
  };

  return (
    <VaccinationContext.Provider value={{ campaigns, vaccinations, addCampaign, updateCampaign, addVaccination, refreshVaccinations: loadData }}>
      {children}
    </VaccinationContext.Provider>
  );
}

export function useVaccination() {
  const context = useContext(VaccinationContext);
  if (context === undefined) throw new Error("useVaccination must be used within Provider");
  return context;
}
