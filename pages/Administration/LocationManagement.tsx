import { FolderTree, MapPin, Plus } from "lucide-react";

export default function LocationManagement() {
  const hierarchy = [
    { name: "Pune Division", type: "Division", children: [
       { name: "Pune", type: "District", children: ["Haveli", "Khed", "Baramati"] },
       { name: "Satara", type: "District", children: ["Satara", "Karad"] }
    ]},
    { name: "Nashik Division", type: "Division", children: [
       { name: "Nashik", type: "District", children: ["Nashik", "Malegaon"] }
    ]}
  ];

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 h-[calc(100vh-10rem)] flex flex-col">
       <div className="p-5 border-b border-gray-200 bg-gray-50 flex justify-between items-center">
          <div>
             <h3 className="text-lg font-bold text-gray-900">Maharashtra Administrative Hierarchy</h3>
             <p className="text-sm text-gray-500">Manage districts, talukas, and villages.</p>
          </div>
          <button className="px-4 py-2 bg-brandBlue text-white text-sm font-medium rounded-lg hover:bg-blue-700 flex items-center gap-2">
             <Plus size={16} /> Add Location
          </button>
       </div>
       <div className="p-6 overflow-auto">
          <div className="space-y-4">
             {hierarchy.map((div, i) => (
                <div key={i} className="border border-gray-200 rounded-lg p-4 bg-gray-50">
                   <div className="font-bold flex items-center gap-2 text-gray-800 mb-3">
                      <FolderTree size={18} className="text-blue-600"/> {div.name} ({div.type})
                   </div>
                   <div className="pl-6 space-y-3">
                      {div.children.map((dist, j) => (
                         <div key={j} className="bg-white p-3 rounded border border-gray-200">
                            <div className="font-bold text-gray-700 flex items-center gap-2 mb-2">
                               <MapPin size={16} className="text-orange-500"/> {dist.name} District
                            </div>
                            <div className="pl-6 flex flex-wrap gap-2">
                               {dist.children.map(tal => (
                                  <span key={tal} className="px-2 py-1 bg-gray-100 text-xs rounded-md text-gray-600 border border-gray-200">
                                     {tal} Taluka
                                  </span>
                               ))}
                            </div>
                         </div>
                      ))}
                   </div>
                </div>
             ))}
          </div>
       </div>
    </div>
  );
}
