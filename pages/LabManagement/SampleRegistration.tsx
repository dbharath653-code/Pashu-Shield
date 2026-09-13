import React, { useState } from "react";
import { useLab } from "../../context/LabContext";
import type { LabSample } from "../../context/LabContext";
import { Save, FileText } from "lucide-react";

export default function SampleRegistration({ onSuccess }: { onSuccess: () => void }) {
  const { addSample } = useLab();
  
  const [formData, setFormData] = useState<Partial<LabSample>>({
    species: "Cattle",
    sampleType: "Blood",
    priority: "Routine",
    collectionDate: new Date().toISOString().substring(0, 16),
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Auto-generate ID: MH-LAB-2026-XXXXXX
    const randomNum = Math.floor(Math.random() * 900000) + 100000;
    const newId = `MH-LAB-${new Date().getFullYear()}-${randomNum}`;
    
    const newSample: LabSample = {
      id: newId,
      caseId: formData.caseId,
      animalId: formData.animalId,
      species: formData.species!,
      diseaseSuspected: formData.diseaseSuspected || "Unknown",
      sampleType: formData.sampleType!,
      priority: formData.priority as "Routine" | "Urgent" | "Critical",
      status: "Collected",
      collectionDate: new Date(formData.collectionDate!).toISOString(),
      location: formData.location || "Unknown",
      district: formData.district || "Unknown",
      tests: [],
      syncStatus: navigator.onLine ? "Synced" : "Pending"
    };

    await addSample(newSample);
    onSuccess();
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 h-full overflow-y-auto">
      <h2 className="text-xl font-bold text-gray-900 mb-6 flex items-center gap-2">
        <FileText size={24} className="text-brandBlue" />
        Register New Lab Sample
      </h2>

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-4">
            <h3 className="font-semibold text-gray-800 border-b border-gray-200 pb-2">Subject Information</h3>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Linked Case ID (Optional)</label>
              <input type="text" className="w-full border-gray-300 rounded-lg p-2.5 border focus:ring-brandBlue focus:border-brandBlue" 
                     placeholder="e.g. VET-2026-12345"
                     onChange={e => setFormData({...formData, caseId: e.target.value})} />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Animal / Herd ID (Optional)</label>
              <input type="text" className="w-full border-gray-300 rounded-lg p-2.5 border focus:ring-brandBlue focus:border-brandBlue" 
                     placeholder="e.g. MH-PUN-CAT-001"
                     onChange={e => setFormData({...formData, animalId: e.target.value})} />
            </div>

            <div className="grid grid-cols-2 gap-4">
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
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Suspected Disease *</label>
                <input type="text" required className="w-full border-gray-300 rounded-lg p-2.5 border focus:ring-brandBlue focus:border-brandBlue" 
                       placeholder="e.g. Lumpy Skin Disease"
                       onChange={e => setFormData({...formData, diseaseSuspected: e.target.value})} />
              </div>
            </div>
          </div>

          <div className="space-y-4">
            <h3 className="font-semibold text-gray-800 border-b border-gray-200 pb-2">Sample & Collection</h3>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Sample Type *</label>
                <select required className="w-full border-gray-300 rounded-lg p-2.5 border focus:ring-brandBlue focus:border-brandBlue"
                        value={formData.sampleType} onChange={e => setFormData({...formData, sampleType: e.target.value})}>
                  <option value="Blood">Blood</option>
                  <option value="Serum">Serum</option>
                  <option value="Nasal Swab">Nasal Swab</option>
                  <option value="Oral Swab">Oral Swab</option>
                  <option value="Tissue">Tissue</option>
                  <option value="Fecal">Fecal</option>
                  <option value="Milk">Milk</option>
                  <option value="Other">Other</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Priority *</label>
                <select required className="w-full border-gray-300 rounded-lg p-2.5 border focus:ring-brandBlue focus:border-brandBlue"
                        value={formData.priority} onChange={e => setFormData({...formData, priority: e.target.value as any})}>
                  <option value="Routine">Routine</option>
                  <option value="Urgent">Urgent</option>
                  <option value="Critical">Critical</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Collection Date & Time *</label>
              <input type="datetime-local" required className="w-full border-gray-300 rounded-lg p-2.5 border focus:ring-brandBlue focus:border-brandBlue" 
                     value={formData.collectionDate}
                     onChange={e => setFormData({...formData, collectionDate: e.target.value})} />
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
        </div>

        <div className="pt-6 border-t border-gray-200 flex justify-end gap-4">
          <button type="submit" className="px-6 py-3 bg-brandBlue text-white font-medium rounded-lg hover:bg-blue-700 flex items-center gap-2">
            <Save size={20} /> Register & Generate Sample ID
          </button>
        </div>
      </form>
    </div>
  );
}

