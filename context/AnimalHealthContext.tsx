import React, { createContext, useContext, useState, useEffect } from "react";
import { dbService } from "../services/db/IndexedDBService";

export interface Animal {
  id: string;
  tagId: string;
  species: string;
  breed: string;
  sex: "Male" | "Female";
  age: number;
  ownerName: string;
  village: string;
  district: string;
  lat?: number;
  lng?: number;
  healthStatus: "Healthy" | "Under Observation" | "Diseased" | "Critical" | "Recovered";
  riskScore: number;
  syncStatus: "Pending" | "Synced";
}

export interface Herd {
  id: string;
  ownerName: string;
  village: string;
  district: string;
  species: string;
  totalAnimals: number;
  lat?: number;
  lng?: number;
  healthStatus: string;
  riskScore: number;
  syncStatus: "Pending" | "Synced";
}

interface AnimalHealthContextType {
  animals: Animal[];
  herds: Herd[];
  addAnimal: (animal: Animal) => Promise<void>;
  updateAnimal: (animal: Animal) => Promise<void>;
  addHerd: (herd: Herd) => Promise<void>;
  refreshData: () => Promise<void>;
}

const AnimalHealthContext = createContext<AnimalHealthContextType | undefined>(undefined);

export function AnimalHealthProvider({ children }: { children: React.ReactNode }) {
  const [animals, setAnimals] = useState<Animal[]>([]);
  const [herds, setHerds] = useState<Herd[]>([]);

  const loadData = async () => {
    await dbService.init();

    // Fetch from backend API
    try {
      const token = localStorage.getItem("auth_token");
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const [animalsRes, herdsRes] = await Promise.all([
        fetch("/api/v1/animals", { headers }),
        fetch("/api/v1/animals/herds", { headers })
      ]);

      if (animalsRes.ok) {
        const apiAnimals = await animalsRes.json();
        if (Array.isArray(apiAnimals) && apiAnimals.length > 0) {
          for (const a of apiAnimals) {
            await dbService.save("animals", a);
          }
          setAnimals(apiAnimals);
        }
      }

      if (herdsRes.ok) {
        const apiHerds = await herdsRes.json();
        if (Array.isArray(apiHerds) && apiHerds.length > 0) {
          for (const h of apiHerds) {
            await dbService.save("herds", h);
          }
          setHerds(apiHerds);
        }
      }
    } catch {
      // offline fallback
    }

    const loadedAnimals = await dbService.getAll("animals");
    if (loadedAnimals.length > 0) setAnimals(loadedAnimals);

    const loadedHerds = await dbService.getAll("herds");
    if (loadedHerds.length > 0) setHerds(loadedHerds);
  };

  useEffect(() => {
    loadData();

    const handleRealtime = (e: any) => {
      const ev = e.detail;
      if (ev?.type === "ANIMAL_REGISTERED") {
        loadData();
      }
    };
    window.addEventListener("pashu_realtime_event", handleRealtime);
    return () => window.removeEventListener("pashu_realtime_event", handleRealtime);
  }, []);

  const addAnimal = async (animal: Animal) => {
    await dbService.save("animals", animal);
    setAnimals(prev => [animal, ...prev]);

    try {
      const token = localStorage.getItem("auth_token");
      await fetch("/api/v1/animals", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {})
        },
        body: JSON.stringify({
          tag_id: animal.tagId,
          species: animal.species,
          breed: animal.breed,
          sex: animal.sex,
          age_years: animal.age,
          village: animal.village,
          district: animal.district
        })
      });
    } catch {
      // Offline fallback in IndexedDB
    }
  };

  const updateAnimal = async (animal: Animal) => {
    await dbService.save("animals", animal);
    setAnimals(prev => prev.map(a => a.id === animal.id ? animal : a));
  };

  const addHerd = async (herd: Herd) => {
    await dbService.save("herds", herd);
    setHerds(prev => [herd, ...prev]);

    try {
      const token = localStorage.getItem("auth_token");
      await fetch("/api/v1/animals/herds", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {})
        },
        body: JSON.stringify({
          species: herd.species,
          total_animals: herd.totalAnimals,
          village: herd.village,
          district: herd.district
        })
      });
    } catch {
      // Offline fallback in IndexedDB
    }
  };

  return (
    <AnimalHealthContext.Provider value={{ animals, herds, addAnimal, updateAnimal, addHerd, refreshData: loadData }}>
      {children}
    </AnimalHealthContext.Provider>
  );
}

export function useAnimalHealth() {
  const context = useContext(AnimalHealthContext);
  if (context === undefined) throw new Error("useAnimalHealth must be used within Provider");
  return context;
}
