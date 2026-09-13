import React, { useState } from "react";
import { AnimalHealthProvider } from "../../context/AnimalHealthContext";
import OverviewTab from "./OverviewTab";
import AnimalsTab from "./AnimalsTab";
import AnimalRegistration from "./AnimalRegistration";
import HerdsTab from "./HerdsTab";
import HerdRegistration from "./HerdRegistration";
import { Plus } from "lucide-react";

function AnimalHealthContent() {
  const [activeTab, setActiveTab] = useState("Overview");
  const [isRegisteringAnimal, setIsRegisteringAnimal] = useState(false);
  const [isRegisteringHerd, setIsRegisteringHerd] = useState(false);

  if (isRegisteringAnimal) {
    return <AnimalRegistration onBack={() => setIsRegisteringAnimal(false)} />;
  }
  if (isRegisteringHerd) {
    return <HerdRegistration onBack={() => setIsRegisteringHerd(false)} />;
  }

  const tabs = ["Overview", "Animals", "Herds", "Health Records", "Vaccination", "Treatment", "High-Risk Animals", "High-Risk Herds"];

  return (
    <div className="flex flex-col h-full bg-gray-50 p-2">
      <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200 mb-4">
        <div className="flex justify-between items-center mb-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">ANIMAL & HERD HEALTH</h1>
            <p className="text-gray-500 text-sm mt-1">Unified animal-level and herd-level health records for surveillance, prevention and veterinary response.</p>
          </div>
          <div className="flex gap-3">
            <button onClick={() => setIsRegisteringHerd(true)} className="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 font-medium flex items-center gap-2">
              <Plus size={18}/> Register Herd
            </button>
            <button onClick={() => setIsRegisteringAnimal(true)} className="px-4 py-2 bg-brandBlue text-white rounded-lg hover:bg-brandBlue/90 font-medium flex items-center gap-2">
              <Plus size={18}/> Register Animal
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
        {activeTab === "Overview" && <OverviewTab />}
        {activeTab === "Animals" && <AnimalsTab onRegister={() => setIsRegisteringAnimal(true)} />}
        {activeTab === "Herds" && <HerdsTab onRegister={() => setIsRegisteringHerd(true)} />}
        {activeTab !== "Overview" && activeTab !== "Animals" && activeTab !== "Herds" && (
           <div className="bg-white p-12 text-center rounded-xl border border-gray-200">
             <h3 className="text-lg font-medium text-gray-500">{activeTab} module is fully architecturalized but UI is under construction for this prototype.</h3>
           </div>
        )}
      </div>
    </div>
  );
}

export default function AnimalHealth() {
  return (
    <AnimalHealthProvider>
      <AnimalHealthContent />
    </AnimalHealthProvider>
  );
}

