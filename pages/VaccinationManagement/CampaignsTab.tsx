import { useVaccination } from "../../context/VaccinationContext";
import { Plus, Target } from "lucide-react";

export default function CampaignsTab() {
  const { campaigns } = useVaccination();

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden flex flex-col">
      <div className="p-4 border-b border-gray-200 flex justify-between items-center bg-gray-50">
        <h2 className="font-bold text-gray-800">Vaccination Campaigns</h2>
        <button onClick={() => alert("Campaign Creation Wizard initialized.")} className="px-4 py-2 bg-brandBlue text-white rounded-lg hover:bg-brandBlue/90 font-medium flex items-center gap-2 text-sm">
          <Plus size={16}/> Create Campaign
        </button>
      </div>

      <div className="overflow-x-auto custom-scrollbar">
        <table className="w-full text-left border-collapse min-w-[640px]">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200 text-xs font-medium text-gray-500 uppercase tracking-wider">
              <th className="px-6 py-4">Campaign Name</th>
              <th className="px-6 py-4">Disease / Vaccine</th>
              <th className="px-6 py-4">Target Audience</th>
              <th className="px-6 py-4">Timeline</th>
              <th className="px-6 py-4">Status</th>
              <th className="px-6 py-4">Progress</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {campaigns.map((c) => (
              <tr key={c.id} className="hover:bg-gray-50 transition-colors">
                <td className="px-6 py-4">
                  <p className="font-medium text-gray-900">{c.name}</p>
                  <p className="text-xs text-gray-500">{c.id}</p>
                </td>
                <td className="px-6 py-4">
                  <p className="text-sm font-bold text-gray-800">{c.disease}</p>
                  <p className="text-sm text-gray-500">{c.vaccine}</p>
                </td>
                <td className="px-6 py-4">
                  <p className="text-sm text-gray-800">{c.species.join(", ")}</p>
                  <p className="text-xs text-gray-500">Target: {c.targetPopulation.toLocaleString()} ({c.coverageTargetPercent}% cover)</p>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <p className="text-sm text-gray-800">{new Date(c.startDate).toLocaleDateString()}</p>
                  <p className="text-xs text-gray-500">to {new Date(c.endDate).toLocaleDateString()}</p>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                  <span className={`px-2 py-1 inline-flex text-xs leading-5 font-bold rounded-full 
                    ${c.status === "Active" ? "bg-green-100 text-green-800" : 
                      c.status === "Completed" ? "bg-gray-100 text-gray-800" : 
                      "bg-yellow-100 text-yellow-800"}`}>
                    {c.status}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex items-center gap-2">
                     <Target size={16} className="text-brandBlue"/>
                     <span className="text-sm font-bold text-brandBlue">42%</span>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

