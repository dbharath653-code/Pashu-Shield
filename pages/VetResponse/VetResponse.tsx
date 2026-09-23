import { useState } from "react";
import { VetResponseProvider } from "../../context/VetResponseContext";
import type { VetCase } from "../../context/VetResponseContext";
import OverviewTab from "./OverviewTab";
import QueueTab from "./QueueTab";
import CaseDetails from "./CaseDetails";
import CallsTab from "./CallsTab";
import { Plus, Wifi, WifiOff } from "lucide-react";

function VetResponseContent() {
  const [activeTab, setActiveTab] = useState("Response Overview");
  const [selectedCase, setSelectedCase] = useState<VetCase | null>(null);

  if (selectedCase) {
    return <CaseDetails vetCase={selectedCase} onBack={() => setSelectedCase(null)} />;
  }

  const tabs = ["Response Overview", "Response Queue", "IVR & Calls", "Active Cases", "Emergency Cases", "Field Visits"];
  const isOffline = !navigator.onLine;

  return (
    <div className="flex flex-col h-full bg-gray-50 p-2">
      <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200 mb-4">
        <div className="flex justify-between items-center mb-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">VETERINARY RESPONSE</h1>
            <p className="text-gray-500 text-sm mt-1">Coordinate veterinary assessment, field visits, treatment, referrals, sample collection and follow-up.</p>
          </div>
          <div className="flex items-center gap-4">
            <div className={`flex items-center gap-2 text-sm font-medium px-3 py-1 rounded-full ${isOffline ? "bg-red-100 text-red-800" : "bg-green-100 text-green-800"}`}>
               {isOffline ? <WifiOff size={16}/> : <Wifi size={16}/>}
               {isOffline ? "Offline" : "Online"}
            </div>
            <button onClick={() => alert("Assignment module opened.")} className="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 font-medium text-sm">
              Assign Cases
            </button>
            <button onClick={() => alert("Emergency protocol initiated!")} className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 font-medium text-sm">
              Emergency Response
            </button>
            <button onClick={() => alert("Response Case Form opened.")} className="px-4 py-2 bg-brandBlue text-white rounded-lg hover:bg-brandBlue/90 font-medium flex items-center gap-2 text-sm">
              <Plus size={16}/> Create Response Case
            </button>
          </div>
        </div>

        <div className="flex overflow-x-auto border-b border-gray-200 hide-scrollbar">
          {tabs.map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`whitespace-nowrap py-3 px-6 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab ? "border-brandBlue text-brandBlue" : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
              }`}
            >
              {tab}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        {activeTab === "Response Overview" && <OverviewTab />}
        {activeTab === "Response Queue" && <QueueTab onViewCase={setSelectedCase} />}
        {activeTab === "IVR & Calls" && <CallsTab />}
        {activeTab !== "Response Overview" && activeTab !== "Response Queue" && activeTab !== "IVR & Calls" && (
           <div className="bg-white p-12 text-center rounded-xl border border-gray-200">
             <h3 className="text-lg font-medium text-gray-500">{activeTab} logic is implemented via Queue and Case Details workflows.</h3>
           </div>
        )}
      </div>
    </div>
  );
}

export default function VetResponse() {
  return (
    <VetResponseProvider>
      <VetResponseContent />
    </VetResponseProvider>
  );
}

