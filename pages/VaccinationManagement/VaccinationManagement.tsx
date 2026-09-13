import { useState } from "react";
import { VaccinationProvider } from "../../context/VaccinationContext";
import VaccinationDashboard from "./VaccinationDashboard";
import CampaignsTab from "./CampaignsTab";
import RecordVaccination from "./RecordVaccination";
import VaccinationRegistry from "./VaccinationRegistry";
import { Shield, Plus, QrCode } from "lucide-react";

function VaccinationContent() {
  const [activeTab, setActiveTab] = useState("Dashboard");

  const tabs = ["Dashboard", "Campaigns", "Record Vaccination", "Vaccination Registry", "Inventory & Cold Chain"];

  return (
    <div className="flex flex-col h-full bg-gray-50 p-2">
      <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200 mb-4">
        <div className="flex justify-between items-center mb-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">VACCINATION & PREVENTION</h1>
            <p className="text-gray-500 text-sm mt-1">Manage campaigns, track herd immunity gaps, record field vaccinations, and issue certificates.</p>
          </div>
          <div className="flex items-center gap-4">
            <button onClick={() => alert("Scanner Initialized.")} className="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 font-medium text-sm flex items-center gap-2">
              <QrCode size={16}/> Scan Tag/QR
            </button>
            <button className="px-4 py-2 bg-brandBlue text-white rounded-lg hover:bg-brandBlue/90 font-medium flex items-center gap-2 text-sm" onClick={() => setActiveTab("Record Vaccination")}>
              <Plus size={16}/> Record Vaccination
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
              {tab === "Dashboard" && <Shield size={16} />}
              {tab}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        {activeTab === "Dashboard" && <VaccinationDashboard />}
        {activeTab === "Campaigns" && <CampaignsTab />}
        {activeTab === "Record Vaccination" && <RecordVaccination onSuccess={() => setActiveTab("Vaccination Registry")} />}
        {activeTab === "Vaccination Registry" && <VaccinationRegistry />}
        {activeTab === "Inventory & Cold Chain" && (
           <div className="bg-white p-12 text-center rounded-xl border border-gray-200">
             <h3 className="text-lg font-medium text-gray-500">Inventory Management & Cold-Chain IoT sensors will connect here.</h3>
           </div>
        )}
      </div>
    </div>
  );
}

export default function VaccinationManagement() {
  return (
    <VaccinationProvider>
      <VaccinationContent />
    </VaccinationProvider>
  );
}

