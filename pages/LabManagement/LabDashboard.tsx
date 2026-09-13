import React from "react";
import { useLab } from "../../context/LabContext";
import { FlaskConical, TestTube, AlertTriangle, CheckCircle, Clock } from "lucide-react";

export default function LabDashboard() {
  const { samples } = useLab();

  const total = samples.length;
  const received = samples.filter(s => s.status === "Received" || s.status === "Accepted").length;
  const inProgress = samples.filter(s => s.status === "Testing").length;
  const pendingVerification = samples.filter(s => s.status === "Result Pending").length;
  const positive = samples.filter(s => s?.tests?.some(t => t.result === "Positive")).length;
  const critical = samples.filter(s => s.priority === "Critical").length;
  const rejected = samples.filter(s => s.status === "Rejected").length;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-500">Total Samples</p>
            <p className="text-2xl font-bold text-gray-900">{total}</p>
          </div>
          <div className="p-3 bg-blue-50 text-blue-600 rounded-lg"><FlaskConical size={24} /></div>
        </div>
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-500">Testing In Progress</p>
            <p className="text-2xl font-bold text-purple-600">{inProgress}</p>
          </div>
          <div className="p-3 bg-purple-50 text-purple-600 rounded-lg"><TestTube size={24} /></div>
        </div>
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-500">Pending Verification</p>
            <p className="text-2xl font-bold text-yellow-600">{pendingVerification}</p>
          </div>
          <div className="p-3 bg-yellow-50 text-yellow-600 rounded-lg"><Clock size={24} /></div>
        </div>
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-500">Positive Results</p>
            <p className="text-2xl font-bold text-red-600">{positive}</p>
          </div>
          <div className="p-3 bg-red-50 text-red-600 rounded-lg"><AlertTriangle size={24} /></div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
          <h3 className="text-lg font-semibold mb-4">Needs Attention</h3>
          <div className="space-y-4">
            <div className="flex justify-between items-center p-3 bg-yellow-50 text-yellow-800 rounded-lg">
               <span className="font-semibold text-sm">Results pending verification</span>
               <span className="font-bold">{pendingVerification} samples</span>
            </div>
            <div className="flex justify-between items-center p-3 bg-red-50 text-red-800 rounded-lg">
               <span className="font-semibold text-sm">Critical priority samples</span>
               <span className="font-bold">{critical} samples</span>
            </div>
            <div className="flex justify-between items-center p-3 bg-gray-50 text-gray-800 rounded-lg">
               <span className="font-semibold text-sm">Rejected samples needing retest</span>
               <span className="font-bold">{rejected} samples</span>
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
          <h3 className="text-lg font-semibold mb-4">Recent Samples</h3>
          <div className="space-y-4">
             {samples.slice(0, 4).map(s => (
               <div key={s.id} className="flex justify-between items-center p-3 hover:bg-gray-50 rounded-lg border border-gray-100">
                  <div>
                    <p className="font-medium text-gray-900">{s.id}</p>
                    <p className="text-xs text-gray-500">{s.species} � {s.sampleType}</p>
                  </div>
                  <div className={`text-xs font-bold px-2 py-1 rounded-full ${s.status === "Verified" ? "bg-green-100 text-green-800" : s.status === "Result Pending" ? "bg-yellow-100 text-yellow-800" : "bg-blue-100 text-blue-800"}`}>
                    {s.status}
                  </div>
               </div>
             ))}
             {samples.length === 0 && <p className="text-sm text-gray-500">No recent samples.</p>}
          </div>
        </div>
      </div>
    </div>
  );
}

