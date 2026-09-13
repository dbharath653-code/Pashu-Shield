import React from "react";
import { useVetResponse } from "../../context/VetResponseContext";
import { AlertCircle, Clock, ShieldAlert, CheckCircle } from "lucide-react";

export default function OverviewTab() {
  const { cases } = useVetResponse();

  const pending = cases.filter(c => c.status === "Pending").length;
  const active = cases.filter(c => c.status !== "Pending" && c.status !== "Closed").length;
  const critical = cases.filter(c => c.priority === "CRITICAL").length;
  const closed = cases.filter(c => c.status === "Closed").length;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-500">Pending Responses</p>
            <p className="text-2xl font-bold text-gray-900">{pending}</p>
          </div>
          <div className="p-3 bg-yellow-50 text-yellow-600 rounded-lg"><Clock size={24} /></div>
        </div>
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-500">Active / Assigned</p>
            <p className="text-2xl font-bold text-blue-600">{active}</p>
          </div>
          <div className="p-3 bg-blue-50 text-blue-600 rounded-lg"><AlertCircle size={24} /></div>
        </div>
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-500">Critical Priority</p>
            <p className="text-2xl font-bold text-red-600">{critical}</p>
          </div>
          <div className="p-3 bg-red-50 text-red-600 rounded-lg"><ShieldAlert size={24} /></div>
        </div>
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-500">Closed Today</p>
            <p className="text-2xl font-bold text-green-600">{closed}</p>
          </div>
          <div className="p-3 bg-green-50 text-green-600 rounded-lg"><CheckCircle size={24} /></div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
          <h3 className="text-lg font-semibold mb-4">Priority Distribution</h3>
          <div className="space-y-4">
            {["CRITICAL", "HIGH", "MEDIUM", "LOW"].map(priority => {
              const count = cases.filter(c => c.priority === priority).length;
              return (
                <div key={priority} className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                  <span className={`font-semibold text-sm ${
                    priority === "CRITICAL" ? "text-red-700" :
                    priority === "HIGH" ? "text-orange-600" :
                    priority === "MEDIUM" ? "text-yellow-600" : "text-green-600"
                  }`}>{priority}</span>
                  <span className="font-bold">{count} cases</span>
                </div>
              );
            })}
          </div>
        </div>

        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
          <h3 className="text-lg font-semibold mb-4">Today's Veterinary Workload</h3>
          <div className="space-y-4">
             <div className="flex justify-between items-center p-3 hover:bg-gray-50 rounded-lg border border-gray-100">
                <div>
                  <p className="font-medium text-gray-900">Dr. Sharma</p>
                  <p className="text-sm text-gray-500">Active Cases: 1</p>
                </div>
                <div className="text-sm font-medium text-blue-600">On Duty</div>
             </div>
             <div className="flex justify-between items-center p-3 hover:bg-gray-50 rounded-lg border border-gray-100">
                <div>
                  <p className="font-medium text-gray-900">Para-vet Jadhav</p>
                  <p className="text-sm text-gray-500">Active Cases: 0</p>
                </div>
                <div className="text-sm font-medium text-green-600">Available</div>
             </div>
          </div>
        </div>
      </div>
    </div>
  );
}

