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
}

const AnimalHealthContext = createContext<AnimalHealthContextType | undefined>(undefined);

export function AnimalHealthProvider({ children }: { children: React.ReactNode }) {
  const [animals, setAnimals] = useState<Animal[]>([]);
  const [herds, setHerds] = useState<Herd[]>([]);

  useEffect(() => {
    const loadData = async () => {
      await dbService.init();
      const loadedAnimals = await dbService.getAll("animals");
      const loadedHerds = await dbService.getAll("herds");
      
      // Seed some mock data if empty for demo purposes
      if (loadedAnimals.length === 0) {
        const mockAnimal: Animal = {
          id: "MH-PUN-CAT-001", tagId: "TAG-9921", species: "Cattle", breed: "Gir", sex: "Female", age: 4, ownerName: "Ramesh Patil", village: "Shirur", district: "Pune", healthStatus: "Under Observation", riskScore: 68, syncStatus: "Synced"
        };
        await dbService.save("animals", mockAnimal);
        setAnimals([mockAnimal]);
      } else {
        setAnimals(loadedAnimals);
      }

      if (loadedHerds.length === 0) {
        const mockHerd: Herd = {
          id: "HRD-PUN-001", ownerName: "Ramesh Patil", village: "Shirur", district: "Pune", species: "Cattle", totalAnimals: 45, healthStatus: "Moderate Risk", riskScore: 45, syncStatus: "Synced"
        };
        await dbService.save("herds", mockHerd);
        setHerds([mockHerd]);
      } else {
        setHerds(loadedHerds);
      }
    };
    loadData();
  }, []);

  const addAnimal = async (animal: Animal) => {
    await dbService.save("animals", animal);
    setAnimals(prev => [animal, ...prev]);
  };

  const updateAnimal = async (animal: Animal) => {
    await dbService.save("animals", animal);
    setAnimals(prev => prev.map(a => a.id === animal.id ? animal : a));
  };

  const addHerd = async (herd: Herd) => {
    await dbService.save("herds", herd);
    setHerds(prev => [herd, ...prev]);
  };

  return (
    <AnimalHealthContext.Provider value={{ animals, herds, addAnimal, updateAnimal, addHerd }}>
      {children}
    </AnimalHealthContext.Provider>
  );
}

export function useAnimalHealth() {
  const context = useContext(AnimalHealthContext);
  if (context === undefined) throw new Error("useAnimalHealth must be used within Provider");
  return context;
}

