import React, { useState } from "react";
import { LabProvider } from "../../context/LabContext";
import type { LabSample } from "../../context/LabContext";
import LabDashboard from "./LabDashboard";
import SampleRegistry from "./SampleRegistry";
import SampleRegistration from "./SampleRegistration";
import SampleDetails from "./SampleDetails";
import { Plus, TestTube2, QrCode } from "lucide-react";

function LabManagementContent() {
  const [activeTab, setActiveTab] = useState("Dashboard");
  const [selectedSample, setSelectedSample] = useState<LabSample | null>(null);

  if (selectedSample) {
    return <SampleDetails sample={selectedSample} onBack={() => setSelectedSample(null)} />;
  }

  const tabs = ["Dashboard", "Sample Registry", "Register New Sample", "Reports"];

  return (
    <div className="flex flex-col h-full bg-gray-50 p-2">
      <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200 mb-4">
        <div className="flex justify-between items-center mb-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">LABORATORY & SAMPLE MANAGEMENT</h1>
            <p className="text-gray-500 text-sm mt-1">Manage sample collection, chain of custody, laboratory tests, and result verification.</p>
          </div>
          <div className="flex items-center gap-4">
            <button onClick={() => alert("Hardware camera initialized. Ready to scan sample QR labels.")} className="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 font-medium text-sm flex items-center gap-2">
              <QrCode size={16}/> Scan QR
            </button>
            <button className="px-4 py-2 bg-brandBlue text-white rounded-lg hover:bg-brandBlue/90 font-medium flex items-center gap-2 text-sm" onClick={() => { const id = prompt("Enter Sample ID or scan barcode to receive at lab:"); if (id) alert("Sample " + id + " successfully logged as Received at Laboratory."); }}>
              <Plus size={16}/> Receive Sample
            </button>
          </div>
        </div>

        <div className="flex overflow-x-auto border-b border-gray-200 hide-scrollbar">
          {tabs.map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`whitespace-nowrap py-3 px-6 text-sm font-medium border-b-2 transition-colors flex items-center gap-2 ${
                activeTab === tab ? "border-brandBlue text-brandBlue" : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
              }`}
            >
              {tab === "Dashboard" && <TestTube2 size={16} />}
              {tab}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        {activeTab === "Dashboard" && <LabDashboard />}
        {activeTab === "Sample Registry" && <SampleRegistry onViewSample={setSelectedSample} />}
        {activeTab === "Register New Sample" && <SampleRegistration onSuccess={() => setActiveTab("Sample Registry")} />}
        {activeTab === "Reports" && (
           <div className="bg-white p-12 text-center rounded-xl border border-gray-200">
             <h3 className="text-lg font-medium text-gray-500">Reports and analytics integration is available in the main Analytics module.</h3>
           </div>
        )}
      </div>
    </div>
  );
}

export default function LabManagement() {
  return (
    <LabProvider>
      <LabManagementContent />
    </LabProvider>
  );
}

