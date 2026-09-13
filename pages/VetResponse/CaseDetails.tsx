import React, { useState } from "react";
import { useVetResponse } from "../../context/VetResponseContext";
import type { VetCase } from "../../context/VetResponseContext";
import { ArrowLeft, MapPin, Clipboard, Stethoscope, Save, Clock } from "lucide-react";

export default function CaseDetails({ vetCase, onBack }: { vetCase: VetCase, onBack: () => void }) {
  const { updateCase } = useVetResponse();
  const [activeTab, setActiveTab] = useState("Overview");
  const [fieldExam, setFieldExam] = useState({ temp: "", symptoms: "", diagnosis: "" });

  const handleStatusChange = async (newStatus: VetCase["status"]) => {
    await updateCase({ ...vetCase, status: newStatus });
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 flex flex-col h-full overflow-y-auto">
      <div className="p-4 border-b border-gray-200 flex items-center justify-between sticky top-0 bg-white z-10">
        <div className="flex items-center gap-4">
          <button onClick={onBack} className="p-2 hover:bg-gray-100 rounded-full text-gray-500">
            <ArrowLeft size={20} />
          </button>
          <div>
             <h2 className="text-xl font-bold text-gray-900">CASE: {vetCase.id}</h2>
             <span className={`px-2 py-0.5 inline-flex text-xs leading-5 font-bold rounded-full mt-1
                    ${vetCase.priority === "CRITICAL" ? "bg-red-100 text-red-800" : 
                      vetCase.priority === "HIGH" ? "bg-orange-100 text-orange-800" : 
                      "bg-yellow-100 text-yellow-800"}`}>
                    {vetCase.priority} PRIORITY
             </span>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {vetCase.status === "Pending" && (
            <button onClick={() => handleStatusChange("Assigned")} className="px-4 py-2 bg-brandBlue text-white rounded-lg hover:bg-blue-700 text-sm font-medium">
              Accept Case
            </button>
          )}
          {vetCase.status === "Assigned" && (
            <button onClick={() => handleStatusChange("En Route")} className="px-4 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 text-sm font-medium">
              Start Travel
            </button>
          )}
          {vetCase.status === "En Route" && (
            <button onClick={() => handleStatusChange("Under Examination")} className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 text-sm font-medium">
              Arrived On Site
            </button>
          )}
          {vetCase.status === "Under Examination" && (
            <button onClick={() => handleStatusChange("Treatment Active")} className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 text-sm font-medium">
              Start Treatment
            </button>
          )}
          {vetCase.status === "Treatment Active" && (
            <button onClick={() => handleStatusChange("Closed")} className="px-4 py-2 bg-gray-800 text-white rounded-lg hover:bg-gray-900 text-sm font-medium">
              Close Case
            </button>
          )}
        </div>
      </div>

      <div className="p-6 grid grid-cols-3 gap-6">
         <div className="col-span-1 space-y-6">
            <div className="bg-gray-50 p-4 rounded-xl border border-gray-200">
               <h3 className="font-semibold mb-3 flex items-center gap-2"><Clipboard size={16}/> Case Info</h3>
               <div className="space-y-2 text-sm">
                  <p><span className="text-gray-500">Animal/Herd:</span> {vetCase.animalHerdId}</p>
                  <p><span className="text-gray-500">Species:</span> {vetCase.species}</p>
                  <p><span className="text-gray-500">Location:</span> {vetCase.location}</p>
                  <p><span className="text-gray-500">Reported Problem:</span> {vetCase.reportedProblem}</p>
                  <p><span className="text-gray-500">Risk Score:</span> {vetCase.riskScore}/100</p>
                  <p><span className="text-gray-500">Status:</span> <span className="font-bold">{vetCase.status}</span></p>
               </div>
            </div>

            <div className="bg-orange-50 p-4 rounded-xl border border-orange-100">
               <h3 className="font-semibold text-orange-800 mb-2">Priority Engine</h3>
               <p className="text-sm text-orange-700 font-bold mb-2">Why is this case {vetCase.priority}?</p>
               <ul className="text-sm text-orange-700 space-y-1">
                  <li>+20 Multiple affected suspected</li>
                  <li>+15 {vetCase.reportedProblem}</li>
                  <li>+20 Rule-based geographical risk</li>
               </ul>
            </div>
         </div>

         <div className="col-span-2">
            <div className="flex border-b border-gray-200 mb-4">
               {["Overview", "Clinical Examination", "Treatment", "Follow-up"].map(tab => (
                 <button key={tab} onClick={() => setActiveTab(tab)} className={`py-2 px-4 text-sm font-medium border-b-2 ${activeTab === tab ? "border-brandBlue text-brandBlue" : "border-transparent text-gray-500"}`}>
                   {tab}
                 </button>
               ))}
            </div>

            {activeTab === "Overview" && (
               <div className="space-y-4">
                 <h3 className="font-semibold text-gray-800">Response Timeline</h3>
                 <div className="border-l-2 border-gray-200 pl-4 space-y-4 py-2">
                    <div className="relative">
                       <div className="absolute -left-[21px] top-1 w-3 h-3 bg-gray-400 rounded-full border-2 border-white"></div>
                       <p className="text-xs text-gray-500">{new Date(vetCase.reportedAt).toLocaleString()}</p>
                       <p className="text-sm font-medium">Case reported</p>
                    </div>
                    {vetCase.status !== "Pending" && (
                      <div className="relative">
                         <div className="absolute -left-[21px] top-1 w-3 h-3 bg-blue-500 rounded-full border-2 border-white"></div>
                         <p className="text-sm font-medium">Veterinarian assigned and accepted</p>
                      </div>
                    )}
                    {(vetCase.status === "Treatment Active" || vetCase.status === "Closed") && (
                      <div className="relative">
                         <div className="absolute -left-[21px] top-1 w-3 h-3 bg-green-500 rounded-full border-2 border-white"></div>
                         <p className="text-sm font-medium">Treatment initiated</p>
                      </div>
                    )}
                 </div>
               </div>
            )}

            {activeTab === "Clinical Examination" && (
               <div className="bg-gray-50 p-6 rounded-xl border border-gray-200">
                  <h3 className="font-semibold mb-4 flex items-center gap-2"><Stethoscope size={18}/> Field Examination Form</h3>
                  <div className="grid grid-cols-2 gap-4">
                     <div>
                       <label className="block text-sm font-medium text-gray-700 mb-1">Temperature (°C)</label>
                       <input type="text" value={fieldExam.temp} onChange={e => setFieldExam({...fieldExam, temp: e.target.value})} className="w-full border-gray-300 rounded-md p-2 border" placeholder="e.g. 39.5" />
                     </div>
                     <div>
                       <label className="block text-sm font-medium text-gray-700 mb-1">Clinical Impressions / Symptoms</label>
                       <input type="text" value={fieldExam.symptoms} onChange={e => setFieldExam({...fieldExam, symptoms: e.target.value})} className="w-full border-gray-300 rounded-md p-2 border" placeholder="Fever, cough..." />
                     </div>
                     <div className="col-span-2">
                       <label className="block text-sm font-medium text-gray-700 mb-1">Suspected Disease</label>
                       <input type="text" value={fieldExam.diagnosis} onChange={e => setFieldExam({...fieldExam, diagnosis: e.target.value})} className="w-full border-gray-300 rounded-md p-2 border" placeholder="Enter suspected diagnosis" />
                     </div>
                  </div>
                  <button onClick={() => alert("Field Examination successfully saved to offline local database!")} className="mt-4 px-4 py-2 bg-brandBlue text-white rounded-lg flex items-center gap-2 text-sm font-medium">
                    <Save size={16}/> Save Examination (Offline Available)
                  </button>
               </div>
            )}
         </div>
      </div>
    </div>
  );
}

