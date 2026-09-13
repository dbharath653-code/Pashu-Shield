import { useAnimalHealth } from "../../context/AnimalHealthContext";
import { Activity, ShieldAlert, HeartPulse, ShieldCheck, AlertTriangle } from "lucide-react";

export default function OverviewTab() {
  const { animals, herds } = useAnimalHealth();

  const totalAnimals = animals.length;
  const healthyAnimals = animals.filter(a => a.healthStatus === "Healthy").length;
  const observation = animals.filter(a => a.healthStatus === "Under Observation").length;
  const diseased = animals.filter(a => a.healthStatus === "Diseased").length;
  const highRisk = animals.filter(a => a.riskScore > 50).length;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-500">Total Animals</p>
            <p className="text-2xl font-bold text-gray-900">{totalAnimals}</p>
          </div>
          <div className="p-3 bg-blue-50 text-blue-600 rounded-lg"><Activity size={24} /></div>
        </div>
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-500">Healthy</p>
            <p className="text-2xl font-bold text-green-600">{healthyAnimals}</p>
          </div>
          <div className="p-3 bg-green-50 text-green-600 rounded-lg"><ShieldCheck size={24} /></div>
        </div>
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-500">Under Observation</p>
            <p className="text-2xl font-bold text-orange-600">{observation}</p>
          </div>
          <div className="p-3 bg-orange-50 text-orange-600 rounded-lg"><AlertTriangle size={24} /></div>
        </div>
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-500">Diseased / Critical</p>
            <p className="text-2xl font-bold text-red-600">{diseased}</p>
          </div>
          <div className="p-3 bg-red-50 text-red-600 rounded-lg"><HeartPulse size={24} /></div>
        </div>
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-500">High Risk</p>
            <p className="text-2xl font-bold text-orange-600">{highRisk}</p>
          </div>
          <div className="p-3 bg-orange-50 text-orange-600 rounded-lg"><ShieldAlert size={24} /></div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
          <h3 className="text-lg font-semibold mb-4">Recent Health Events</h3>
          <div className="space-y-4">
            {animals.slice(0, 5).map(animal => (
              <div key={animal.id} className="flex justify-between items-center p-3 hover:bg-gray-50 rounded-lg border border-gray-100">
                <div>
                  <p className="font-medium text-gray-900">{animal.id}</p>
                  <p className="text-sm text-gray-500">{animal.species} • {animal.village}</p>
                </div>
                <div className={`px-3 py-1 rounded-full text-xs font-semibold 
                  ${animal.healthStatus === "Healthy" ? "bg-green-100 text-green-800" : 
                    animal.healthStatus === "Diseased" ? "bg-red-100 text-red-800" : 
                    "bg-orange-100 text-orange-800"}`}>
                  {animal.healthStatus}
                </div>
              </div>
            ))}
            {animals.length === 0 && <p className="text-sm text-gray-500">No events found.</p>}
          </div>
        </div>

        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
          <h3 className="text-lg font-semibold mb-4">High Risk Herds</h3>
          <div className="space-y-4">
            {herds.filter(h => h.riskScore > 50).map(herd => (
              <div key={herd.id} className="flex justify-between items-center p-3 hover:bg-gray-50 rounded-lg border border-gray-100">
                <div>
                  <p className="font-medium text-gray-900">{herd.id}</p>
                  <p className="text-sm text-gray-500">{herd.ownerName} � {herd.totalAnimals} animals</p>
                </div>
                <div className="flex items-center gap-1 text-red-600 text-sm font-semibold">
                  <AlertTriangle size={16} /> Risk: {herd.riskScore}
                </div>
              </div>
            ))}
            {herds.filter(h => h.riskScore > 50).length === 0 && <p className="text-sm text-gray-500">No high-risk herds detected.</p>}
          </div>
        </div>
      </div>
    </div>
  );
}

