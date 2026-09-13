import React, { useState } from "react";
import { useAnimalHealth } from "../../context/AnimalHealthContext";
import type { Herd } from "../../context/AnimalHealthContext";
import { ArrowLeft, Save, MapPin } from "lucide-react";
import { DISTRICT_NAMES } from "../../services/ReferenceData";

export default function HerdRegistration({ onBack }: { onBack: () => void }) {
  const { addHerd } = useAnimalHealth();
  const [formData, setFormData] = useState<Partial<Herd>>({
    species: "Mixed",
    totalAnimals: 10,
    village: "",
    district: "",
    ownerName: "",
    healthStatus: "Low Risk"
  });

  const generateId = () => `HRD-${formData.district ? formData.district.substring(0,3).toUpperCase() : "XXX"}-${Math.floor(Math.random()*10000).toString().padStart(4,"0")}`;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const newHerd: Herd = {
      id: generateId(),
      ownerName: formData.ownerName || "Unknown",
      village: formData.village || "Unknown",
      district: formData.district || "Unknown",
      species: formData.species!,
      totalAnimals: Number(formData.totalAnimals),
      lat: formData.lat,
      lng: formData.lng,
      healthStatus: formData.healthStatus || "Low Risk",
      riskScore: formData.healthStatus === "High Risk" ? 85 : 20,
      syncStatus: navigator.onLine ? "Synced" : "Pending"
    };
    
    await addHerd(newHerd);
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
          <h2 className="text-xl font-bold text-gray-900">Register New Herd</h2>
        </div>
        <button onClick={handleSubmit} className="px-6 py-2 bg-brandBlue text-white rounded-lg font-medium flex items-center gap-2 hover:bg-blue-700">
          <Save size={18} /> Save Herd
        </button>
      </div>

      <div className="p-8 max-w-4xl mx-auto w-full space-y-8">
        <section>
          <h3 className="text-lg font-bold text-gray-800 border-b pb-2 mb-4">Herd Information</h3>
          <div className="grid grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Owner Name</label>
              <input type="text" value={formData.ownerName} onChange={e => setFormData({...formData, ownerName: e.target.value})} className="w-full border-gray-300 rounded-md shadow-sm p-2 border" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Primary Species</label>
              <select value={formData.species} onChange={e => setFormData({...formData, species: e.target.value})} className="w-full border-gray-300 rounded-md shadow-sm p-2 border">
                <option>Cattle</option><option>Buffalo</option><option>Goat</option><option>Sheep</option><option>Mixed</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Total Animals</label>
              <input type="number" value={formData.totalAnimals} onChange={e => setFormData({...formData, totalAnimals: Number(e.target.value)})} className="w-full border-gray-300 rounded-md shadow-sm p-2 border" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Herd Health Risk</label>
              <select value={formData.healthStatus} onChange={e => setFormData({...formData, healthStatus: e.target.value})} className="w-full border-gray-300 rounded-md shadow-sm p-2 border">
                <option>Low Risk</option><option>Moderate Risk</option><option>High Risk</option>
              </select>
            </div>
          </div>
        </section>

        <section>
          <h3 className="text-lg font-bold text-gray-800 border-b pb-2 mb-4 flex justify-between items-center">
            Location
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
      </div>
    </div>
  );
}

