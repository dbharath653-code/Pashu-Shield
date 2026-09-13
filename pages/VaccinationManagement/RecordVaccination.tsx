import React, { useState } from "react";
import { useVaccination } from "../../context/VaccinationContext";
import type { VaccinationRecord } from "../../context/VaccinationContext";
import { Save, Syringe, WifiOff } from "lucide-react";

export default function RecordVaccination({ onSuccess }: { onSuccess: () => void }) {
  const { addVaccination, campaigns } = useVaccination();
  const isOffline = !navigator.onLine;
  
  const [formData, setFormData] = useState<Partial<VaccinationRecord>>({
    species: "Cattle",
    vaccinationDate: new Date().toISOString().substring(0, 10),
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Auto-generate ID: VAC-YYYY-XXXX
    const randomNum = Math.floor(Math.random() * 9000) + 1000;
    const newId = `VAC-${new Date().getFullYear()}-${randomNum}`;
    
    // Calculate next due date (defaulting to 6 months for demo purposes)
    const nextDue = new Date(formData.vaccinationDate!);
    nextDue.setMonth(nextDue.getMonth() + 6);

    const newRecord: VaccinationRecord = {
      id: newId,
      animalId: formData.animalId!,
      herdId: formData.herdId,
      species: formData.species!,
      disease: formData.disease!,
      vaccine: formData.vaccine!,
      batchNumber: formData.batchNumber || "UNKNOWN",
      vaccinationDate: new Date(formData.vaccinationDate!).toISOString(),
      nextDueDate: nextDue.toISOString(),
      campaignId: formData.campaignId,
      location: formData.location || "Unknown",
      district: formData.district || "Unknown",
      provider: "Current User",
      syncStatus: navigator.onLine ? "Synced" : "Pending"
    };

    await addVaccination(newRecord);
    alert(`Vaccination successfully recorded! ${isOffline ? "Saved offline." : "Synced."}\n\nVaccination ID: ${newId}\nNext Booster Due: ${nextDue.toLocaleDateString()}`);
    onSuccess();
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 h-full overflow-y-auto">
      <div className="flex justify-between items-center mb-6">
         <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
           <Syringe size={24} className="text-brandBlue" />
           Record New Vaccination
         </h2>
         {isOffline && (
           <div className="flex items-center gap-2 px-3 py-1 bg-yellow-50 text-yellow-800 rounded-lg text-sm font-medium border border-yellow-200">
             <WifiOff size={16} /> Offline Mode - Records will sync when connected
           </div>
         )}
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-4">
            <h3 className="font-semibold text-gray-800 border-b border-gray-200 pb-2">Animal Identification</h3>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Animal ID (Ear Tag) *</label>
              <input type="text" required className="w-full border-gray-300 rounded-lg p-2.5 border focus:ring-brandBlue focus:border-brandBlue" 
                     placeholder="e.g. MH-PUN-CAT-001"
                     onChange={e => setFormData({...formData, animalId: e.target.value})} />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Herd ID (Optional)</label>
                <input type="text" className="w-full border-gray-300 rounded-lg p-2.5 border focus:ring-brandBlue focus:border-brandBlue" 
                       placeholder="e.g. HRD-PUN-001"
                       onChange={e => setFormData({...formData, herdId: e.target.value})} />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Species *</label>
                <select required className="w-full border-gray-300 rounded-lg p-2.5 border focus:ring-brandBlue focus:border-brandBlue"
                        value={formData.species} onChange={e => setFormData({...formData, species: e.target.value})}>
                  <option value="Cattle">Cattle</option>
                  <option value="Buffalo">Buffalo</option>
                  <option value="Goat">Goat</option>
                  <option value="Sheep">Sheep</option>
                  <option value="Poultry">Poultry</option>
                  <option value="Pig">Pig</option>
                  <option value="Other">Other</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Village/Location *</label>
                <input type="text" required className="w-full border-gray-300 rounded-lg p-2.5 border focus:ring-brandBlue focus:border-brandBlue" 
                       placeholder="e.g. Shirur"
                       onChange={e => setFormData({...formData, location: e.target.value})} />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">District *</label>
                <input type="text" required className="w-full border-gray-300 rounded-lg p-2.5 border focus:ring-brandBlue focus:border-brandBlue" 
                       placeholder="e.g. Pune"
                       onChange={e => setFormData({...formData, district: e.target.value})} />
              </div>
            </div>
          </div>

          <div className="space-y-4">
            <h3 className="font-semibold text-gray-800 border-b border-gray-200 pb-2">Medical Details</h3>
            
            <div>
               <label className="block text-sm font-medium text-gray-700 mb-1">Campaign (Optional)</label>
               <select className="w-full border-gray-300 rounded-lg p-2.5 border focus:ring-brandBlue focus:border-brandBlue"
                       value={formData.campaignId || ""} onChange={e => setFormData({...formData, campaignId: e.target.value})}>
                  <option value="">-- No Campaign / Routine --</option>
                  {campaigns.map(c => (
                     <option key={c.id} value={c.id}>{c.name} ({c.disease})</option>
                  ))}
               </select>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Disease Targeted *</label>
                <input type="text" required className="w-full border-gray-300 rounded-lg p-2.5 border focus:ring-brandBlue focus:border-brandBlue" 
                       placeholder="e.g. Foot-and-Mouth Disease"
                       onChange={e => setFormData({...formData, disease: e.target.value})} />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Vaccine Name *</label>
                <input type="text" required className="w-full border-gray-300 rounded-lg p-2.5 border focus:ring-brandBlue focus:border-brandBlue" 
                       placeholder="e.g. Raksha Ovac"
                       onChange={e => setFormData({...formData, vaccine: e.target.value})} />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Batch Number *</label>
                <input type="text" required className="w-full border-gray-300 rounded-lg p-2.5 border focus:ring-brandBlue focus:border-brandBlue" 
                       placeholder="e.g. B-2026-04"
                       onChange={e => setFormData({...formData, batchNumber: e.target.value})} />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Vaccination Date *</label>
                <input type="date" required className="w-full border-gray-300 rounded-lg p-2.5 border focus:ring-brandBlue focus:border-brandBlue" 
                       value={formData.vaccinationDate}
                       onChange={e => setFormData({...formData, vaccinationDate: e.target.value})} />
              </div>
            </div>
          </div>
        </div>

        <div className="pt-6 border-t border-gray-200 flex justify-end gap-4">
          <button type="submit" className="px-6 py-3 bg-brandBlue text-white font-medium rounded-lg hover:bg-blue-700 flex items-center gap-2">
            <Save size={20} /> Record Vaccination
          </button>
        </div>
      </form>
    </div>
  );
}

