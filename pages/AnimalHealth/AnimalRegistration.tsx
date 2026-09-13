import React, { useState } from "react";
import { useAnimalHealth } from "../../context/AnimalHealthContext";
import type { Animal } from "../../context/AnimalHealthContext";
import { ArrowLeft, Save, MapPin } from "lucide-react";
import { DISTRICT_NAMES, getBreedsForSpecies } from "../../services/ReferenceData";

export default function AnimalRegistration({ onBack }: { onBack: () => void }) {
  const { addAnimal } = useAnimalHealth();
  const [formData, setFormData] = useState<Partial<Animal>>({
    species: "Cattle",
    breed: "Gir",
    sex: "Female",
    healthStatus: "Healthy",
    age: 1,
    village: "",
    district: "",
    ownerName: ""
  });

  const generateId = () => `MH-${formData.district ? formData.district.substring(0,3).toUpperCase() : "XXX"}-CAT-${Math.floor(Math.random()*10000).toString().padStart(4,"0")}`;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const newAnimal: Animal = {
      id: generateId(),
      tagId: `TAG-${Math.floor(Math.random()*10000)}`,
      species: formData.species!,
      breed: formData.breed!,
      sex: formData.sex as any,
      age: Number(formData.age),
      ownerName: formData.ownerName || "Unknown",
      village: formData.village || "Unknown",
      district: formData.district || "Unknown",
      lat: formData.lat,
      lng: formData.lng,
      healthStatus: formData.healthStatus as any,
      riskScore: formData.healthStatus === "Healthy" ? 10 : 65,
      syncStatus: navigator.onLine ? "Synced" : "Pending"
    };
    
    await addAnimal(newAnimal);
    onBack();
  };

  const handleUseLocation = () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          setFormData(prev => ({
            ...prev,
            village: prev.village || "GPS Acquired",
            district: prev.district || "Pune",
            lat: Number(pos.coords.latitude.toFixed(6)),
            lng: Number(pos.coords.longitude.toFixed(6)),
          }));
        },
        () => {
          setFormData(prev => ({...prev, village: prev.village || "Location unavailable"}));
        }
      );
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 flex flex-col h-full overflow-y-auto">
      <div className="p-4 border-b border-gray-200 flex items-center justify-between sticky top-0 bg-white z-10">
        <div className="flex items-center gap-4">
          <button onClick={onBack} className="p-2 hover:bg-gray-100 rounded-full text-gray-500">
            <ArrowLeft size={20} />
          </button>
          <h2 className="text-xl font-bold text-gray-900">Register New Animal</h2>
        </div>
        <button onClick={handleSubmit} className="px-6 py-2 bg-brandBlue text-white rounded-lg font-medium flex items-center gap-2 hover:bg-blue-700">
          <Save size={18} /> Save Animal
        </button>
      </div>

      <div className="p-8 max-w-4xl mx-auto w-full space-y-8">
        {/* Section A */}
        <section>
          <h3 className="text-lg font-bold text-gray-800 border-b pb-2 mb-4">A. Identification</h3>
          <div className="grid grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Species</label>
              <select value={formData.species} onChange={e => setFormData({...formData, species: e.target.value})} className="w-full border-gray-300 rounded-md shadow-sm p-2 border">
                <option>Cattle</option><option>Buffalo</option><option>Goat</option><option>Sheep</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Breed</label>
              <input type="text" list="breed-options" placeholder="e.g. Gir, Pandharpuri…" value={formData.breed} onChange={e => setFormData({...formData, breed: e.target.value})} className="w-full border-gray-300 rounded-md shadow-sm p-2 border" />
              {/* ICAR-NBAGR registered indigenous breeds found in Maharashtra */}
              <datalist id="breed-options">
                {getBreedsForSpecies(formData.species).map(breed => (
                  <option key={breed} value={breed} />
                ))}
              </datalist>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Sex</label>
              <select value={formData.sex} onChange={e => setFormData({...formData, sex: e.target.value as any})} className="w-full border-gray-300 rounded-md shadow-sm p-2 border">
                <option>Female</option><option>Male</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Age (Years)</label>
              <input type="number" value={formData.age} onChange={e => setFormData({...formData, age: Number(e.target.value)})} className="w-full border-gray-300 rounded-md shadow-sm p-2 border" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Owner Name</label>
              <input type="text" value={formData.ownerName} onChange={e => setFormData({...formData, ownerName: e.target.value})} className="w-full border-gray-300 rounded-md shadow-sm p-2 border" />
            </div>
          </div>
        </section>

        {/* Section B */}
        <section>
          <h3 className="text-lg font-bold text-gray-800 border-b pb-2 mb-4 flex justify-between items-center">
            G. Location
            <button onClick={handleUseLocation} className="text-sm text-brandBlue flex items-center gap-1 font-medium bg-blue-50 px-3 py-1 rounded">
              <MapPin size={14}/> Use Current Location
            </button>
          </h3>
          <div className="grid grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Village</label>
              <input type="text" value={formData.village} onChange={e => setFormData({...formData, village: e.target.value})} className="w-full border-gray-300 rounded-md shadow-sm p-2 border" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">District</label>
              <input type="text" list="district-options" placeholder="Select district" value={formData.district} onChange={e => setFormData({...formData, district: e.target.value})} className="w-full border-gray-300 rounded-md shadow-sm p-2 border" />
              {/* All 36 districts of Maharashtra (Govt. of Maharashtra) */}
              <datalist id="district-options">
                {DISTRICT_NAMES.map(district => (
                  <option key={district} value={district} />
                ))}
              </datalist>
            </div>
          </div>
        </section>
        
        {/* Section C */}
        <section>
          <h3 className="text-lg font-bold text-gray-800 border-b pb-2 mb-4">B. Health Status</h3>
          <div className="grid grid-cols-1 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Current Health Status</label>
              <select value={formData.healthStatus} onChange={e => setFormData({...formData, healthStatus: e.target.value as any})} className="w-full border-gray-300 rounded-md shadow-sm p-2 border">
                <option>Healthy</option><option>Under Observation</option><option>Diseased</option><option>Critical</option><option>Recovered</option>
              </select>
            </div>
          </div>
        </section>

      </div>
    </div>
  );
}

