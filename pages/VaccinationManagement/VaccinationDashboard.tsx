import React from "react";
import { useVaccination } from "../../context/VaccinationContext";
import { ShieldCheck, CalendarClock, AlertTriangle, Syringe, Users, CheckCircle, BarChart } from "lucide-react";

export default function VaccinationDashboard() {
  const { campaigns, vaccinations } = useVaccination();

  const totalVaccinations = vaccinations.length;
  const activeCampaigns = campaigns.filter(c => c.status === "Active").length;
  
  // Basic mock KPIs based on real array lengths where applicable
  const dueForVaccination = 1245; // Real app would filter AnimalContext
  const boostersOverdue = vaccinations.filter(v => new Date(v.nextDueDate) < new Date()).length;
  const vaccinationsToday = vaccinations.filter(v => new Date(v.vaccinationDate).toDateString() === new Date().toDateString()).length;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-500">Vaccinations Recorded</p>
            <p className="text-2xl font-bold text-gray-900">{totalVaccinations}</p>
          </div>
          <div className="p-3 bg-green-50 text-green-600 rounded-lg"><ShieldCheck size={24} /></div>
        </div>
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-500">Active Campaigns</p>
            <p className="text-2xl font-bold text-blue-600">{activeCampaigns}</p>
          </div>
          <div className="p-3 bg-blue-50 text-blue-600 rounded-lg"><BarChart size={24} /></div>
        </div>
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-500">Boosters Overdue</p>
            <p className="text-2xl font-bold text-red-600">{boostersOverdue}</p>
          </div>
          <div className="p-3 bg-red-50 text-red-600 rounded-lg"><AlertTriangle size={24} /></div>
        </div>
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-500">Vaccinations Today</p>
            <p className="text-2xl font-bold text-purple-600">{vaccinationsToday}</p>
          </div>
          <div className="p-3 bg-purple-50 text-purple-600 rounded-lg"><Syringe size={24} /></div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
          <h3 className="text-lg font-semibold mb-4 text-gray-800">Needs Attention</h3>
          <div className="space-y-4">
             <div className="flex items-center gap-3 p-3 bg-red-50 text-red-800 rounded-lg border border-red-100">
               <AlertTriangle size={20} className="shrink-0" />
               <p className="text-sm font-medium"><strong>Pune District:</strong> High-risk FMD cluster detected with &lt; 40% herd coverage.</p>
             </div>
             <div className="flex items-center gap-3 p-3 bg-orange-50 text-orange-800 rounded-lg border border-orange-100">
               <CalendarClock size={20} className="shrink-0" />
               <p className="text-sm font-medium"><strong>{boostersOverdue} boosters</strong> are currently overdue across 4 districts.</p>
             </div>
             <div className="flex items-center gap-3 p-3 bg-yellow-50 text-yellow-800 rounded-lg border border-yellow-100">
               <Users size={20} className="shrink-0" />
               <p className="text-sm font-medium"><strong>{dueForVaccination} animals</strong> are eligible for the upcoming PPR vaccination drive.</p>
             </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
          <h3 className="text-lg font-semibold mb-4 text-gray-800">Campaigns Progress</h3>
          <div className="space-y-6">
             {campaigns.filter(c => c.status === "Active").map(camp => (
                <div key={camp.id}>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="font-medium text-gray-900">{camp.name}</span>
                    <span className="font-bold text-brandBlue">42%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2.5">
                    <div className="bg-brandBlue h-2.5 rounded-full" style={{ width: "42%" }}></div>
                  </div>
                  <div className="flex justify-between text-xs text-gray-500 mt-1">
                    <span>Target: {camp.targetPopulation.toLocaleString()} animals</span>
                    <span>Ends: {new Date(camp.endDate).toLocaleDateString()}</span>
                  </div>
                </div>
             ))}
             {campaigns.filter(c => c.status === "Active").length === 0 && (
                <p className="text-gray-500 text-sm">No active campaigns.</p>
             )}
          </div>
        </div>
      </div>
    </div>
  );
}

