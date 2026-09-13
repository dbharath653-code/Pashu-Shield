import React, { useState, useEffect } from "react";
import { AdminService } from "../../services/AdminService";
import type { Facility } from "../../services/AdminService";
import { Search, Plus, Building2, MapPin, Edit } from "lucide-react";

export default function FacilityManagement() {
  const [facilities, setFacilities] = useState<Facility[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    AdminService.getFacilities().then(res => {
      setFacilities(res);
      setLoading(false);
    });
  }, []);

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 flex flex-col h-[calc(100vh-10rem)]">
       <div className="p-5 border-b border-gray-200 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-gray-50 rounded-t-xl">
          <h3 className="text-lg font-bold text-gray-900">Departments & Facilities</h3>
          <div className="flex items-center gap-3 w-full sm:w-auto">
             <div className="relative flex-1 sm:w-64">
                <Search className="absolute left-3 top-2.5 text-gray-400" size={18} />
                <input type="text" placeholder="Search facility..." className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg text-sm" />
             </div>
             <button className="px-4 py-2 bg-brandBlue text-white font-medium rounded-lg hover:bg-blue-700 flex items-center gap-2 whitespace-nowrap">
                <Plus size={18} /> Add Facility
             </button>
          </div>
       </div>

       <div className="flex-1 overflow-auto">
          <table className="w-full text-left text-sm whitespace-nowrap">
             <thead className="bg-gray-100 text-gray-600 font-medium sticky top-0 shadow-sm z-10">
                <tr>
                   <th className="px-6 py-4">Facility Name & ID</th>
                   <th className="px-6 py-4">Type</th>
                   <th className="px-6 py-4">Location</th>
                   <th className="px-6 py-4">Contact</th>
                   <th className="px-6 py-4">Status</th>
                   <th className="px-6 py-4 text-right">Actions</th>
                </tr>
             </thead>
             <tbody className="divide-y divide-gray-100">
                {loading ? (
                   <tr><td colSpan={6} className="text-center p-8 text-gray-500">Loading facilities...</td></tr>
                ) : facilities.map(fac => (
                   <tr key={fac.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4">
                         <div className="font-bold text-gray-900 flex items-center gap-2"><Building2 size={16} className="text-blue-500"/> {fac.name}</div>
                         <div className="text-xs text-gray-500 ml-6">{fac.id}</div>
                      </td>
                      <td className="px-6 py-4 text-gray-700">{fac.type}</td>
                      <td className="px-6 py-4">
                         <div className="text-gray-900 flex items-center gap-1"><MapPin size={14}/> {fac.district}</div>
                         <div className="text-xs text-gray-500 ml-4">{fac.taluka}</div>
                      </td>
                      <td className="px-6 py-4 text-gray-700">{fac.contact}</td>
                      <td className="px-6 py-4">
                         <span className={`px-2 py-1 text-xs font-bold rounded-full ${fac.status === "Active" ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"}`}>{fac.status}</span>
                      </td>
                      <td className="px-6 py-4 text-right">
                         <button className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg"><Edit size={16}/></button>
                      </td>
                   </tr>
                ))}
             </tbody>
          </table>
       </div>
    </div>
  );
}
