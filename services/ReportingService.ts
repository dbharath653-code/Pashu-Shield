import { assetUrl } from './AssetPaths';

export const mlSymptoms = [
  "Difficulty_swallowing", "Lethargy", "Fever", "Diarrhea", "Appetite_loss", "Abnormal_milk", 
  "Weight_loss", "Swelling_neck", "Blisters_on_gums", "Abortion", "Vomiting", "Salivation", 
  "Lameness", "Milk_decrease", "Sudden_death", "Retained_placenta", "Paralysis", "Skin_discoloration", 
  "Swollen_lymph_nodes", "Mouth_ulcers", "Swelling_head", "Drop_in_egg_production", "Swelling_udder", 
  "Cough", "Difficulty_breathing", "Nasal_discharge", "Bleeding_orifices", "Swelling_limbs", 
  "Neurological", "Skin_lesions", "Aggression", "Swelling_muscle"
];

export interface ReportDraft {
  species?: string;
  gender?: string;
  age?: number | "";
  temperature?: number | "";
  numberAffected?: number | "";
  numberDead?: number | "";
  symptoms: string[];
  village?: string;
  district?: string;
  state?: string;
  lat?: number;
  lng?: number;
  disease?: string;
  timestamp?: string;
}

export const ReportingService = {
  extractEntities: async (text: string): Promise<Partial<ReportDraft>> => {
    const extracted: Partial<ReportDraft> = { symptoms: [] };
    const lowerText = text.toLowerCase();
    
    if (lowerText.includes('cattle') || lowerText.includes('cow') || lowerText.includes('bull') || lowerText.includes('गाय')) extracted.species = 'Cattle';
    else if (lowerText.includes('buffalo') || lowerText.includes('भैंस')) extracted.species = 'Buffalo';
    else if (lowerText.includes('goat') || lowerText.includes('bakri') || lowerText.includes('बकरी')) extracted.species = 'Goat';
    else if (lowerText.includes('sheep') || lowerText.includes('भेड़')) extracted.species = 'Sheep';
    else if (lowerText.includes('pig') || lowerText.includes('सुअर')) extracted.species = 'Pig';
    else if (lowerText.includes('poultry') || lowerText.includes('chicken') || lowerText.includes('hen')) extracted.species = 'Poultry';

    if (lowerText.includes('female') || lowerText.includes('cow') || lowerText.includes('hen')) extracted.gender = 'Female';
    else if (lowerText.includes('male') || lowerText.includes('bull')) extracted.gender = 'Male';

    const ageMatch = lowerText.match(/(\d+)\s*(year|yr|month|day|साल|वर्ष)s?/);
    if (ageMatch) extracted.age = Number(ageMatch[1]);
    
    const tempMatch = lowerText.match(/(\d+\.?\d*)\s*(degrees?|celsius|f|temperature|डिग्री|तापमान)/);
    if (tempMatch) extracted.temperature = Number(tempMatch[1]);
    
    const countMatch = lowerText.match(/(\d+)\s*(animals?|affected|जानवर|बीमार)/);
    if (countMatch) extracted.numberAffected = Number(countMatch[1]);
    
    const deadMatch = lowerText.match(/(\d+)\s*(dead|died|मर)/);
    if (deadMatch) extracted.numberDead = Number(deadMatch[1]);

    try {
        const response = await fetch(assetUrl('symptomDictionary.json'));
        if (response.ok) {
            const dictionary = await response.json();
            for (const [symId, langs] of Object.entries(dictionary)) {
                let found = false;
                for (const words of Object.values(langs as Record<string, string[]>)) {
                    if (words.some((w: string) => lowerText.includes(w))) {
                        found = true;
                        break;
                    }
                }
                if (found) {
                    const formattedSym = symId.charAt(0).toUpperCase() + symId.slice(1);
                    if (!extracted.symptoms) extracted.symptoms = [];
                    extracted.symptoms.push(formattedSym);
                }
            }
        }
    } catch (e) {
        console.error('Failed to load symptom dictionary', e);
    }
    
    return extracted;
  },

  getLocation: async (): Promise<{lat: number, lng: number, village: string, district: string, state: string}> => {
    return new Promise((resolve, reject) => {
      if (!navigator.geolocation) {
        reject(new Error("Geolocation is not supported by your browser"));
        return;
      }
      
      navigator.geolocation.getCurrentPosition(
        async (position) => {
          const { latitude, longitude } = position.coords;
          
          if (!navigator.onLine) {
            // OFFLINE REVERSE GEOCODING
            try {
              const res = await fetch(assetUrl('maharashtra_locations.json'));
              const districts = await res.json();
              let closest = districts[0];
              let minD = Infinity;
              districts.forEach((d: any) => {
                const dist = Math.sqrt(Math.pow(d.lat - latitude, 2) + Math.pow(d.lng - longitude, 2));
                if (dist < minD) { minD = dist; closest = d; }
              });
              resolve({
                lat: latitude, lng: longitude,
                village: "Offline GPS",
                district: closest.district,
                state: "Maharashtra"
              });
            } catch {
              resolve({ lat: latitude, lng: longitude, village: "Unknown Offline Location", district: "Unknown District", state: "Maharashtra" });
            }
            return;
          }

          try {
            const res = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${latitude}&lon=${longitude}`);
            if (res.ok) {
                const data = await res.json();
                resolve({
                    lat: latitude,
                    lng: longitude,
                    village: data.address.village || data.address.town || data.address.city || "Unknown Location",
                    district: data.address.county || data.address.state_district || "Unknown District",
                    state: data.address.state || "Maharashtra"
                });
            } else {
                throw new Error("Geocoding failed");
            }
          } catch {
            resolve({
                lat: latitude,
                lng: longitude,
                village: "Unknown Location",
                district: "Unknown District",
                state: "Maharashtra"
            });
          }
        },
        (error) => {
          reject(error);
        },
        { enableHighAccuracy: true, timeout: 10000 }
      );
    });
  },

  saveDraft: (data: ReportDraft) => {
    try {
      localStorage.setItem("livestock_report_draft", JSON.stringify(data));
    } catch (error) {
      console.warn("Could not persist the report draft", error);
    }
  },
  
  getDraft: (): ReportDraft | null => {
    try {
      const data = localStorage.getItem("livestock_report_draft");
      if (!data) return null;
      const parsed = JSON.parse(data);
      return parsed && typeof parsed === "object" ? (parsed as ReportDraft) : null;
    } catch (error) {
      console.warn("Stored report draft was unreadable and has been cleared", error);
      try {
        localStorage.removeItem("livestock_report_draft");
      } catch {
        /* storage unavailable */
      }
      return null;
    }
  },

  clearDraft: () => {
    try {
      localStorage.removeItem("livestock_report_draft");
    } catch {
      /* storage unavailable */
    }
  },

  queueForSync: (report: any) => {
    const queue = ReportingService.getSyncQueue();
    queue.push({...report, syncStatus: "QUEUED", queuedAt: new Date().toISOString()});
    ReportingService.writeQueue(queue);
  },

  getSyncQueue: (): any[] => {
    // Guard against corrupted storage: a bad value must never break the offline
    // reporting screen, so anything unreadable is reset to an empty queue.
    try {
      const raw = localStorage.getItem("livestock_sync_queue");
      if (!raw) return [];
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed : [];
    } catch (error) {
      console.warn("Offline queue was unreadable and has been reset", error);
      try {
        localStorage.setItem("livestock_sync_queue", "[]");
      } catch {
        /* storage unavailable – keep the in-memory value */
      }
      return [];
    }
  },

  writeQueue: (queue: any[]) => {
    try {
      localStorage.setItem("livestock_sync_queue", JSON.stringify(queue));
    } catch (error) {
      console.warn("Could not persist the offline queue", error);
    }
  },

  clearSyncQueue: () => {
    ReportingService.writeQueue([]);
  }
};

