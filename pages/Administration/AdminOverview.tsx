import React, { useEffect, useState } from "react";
import { AdminService } from "../../services/AdminService";
import { Users, UserCheck, Clock, MapPin, Building2, ShieldAlert, Activity } from "lucide-react";

export default function AdminOverview() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    AdminService.getOverview().then(res => {
      setData(res);
      setLoading(false);
    });
  }, []);

  if (loading || !data) {
    return <div className="grid grid-cols-2 md:grid-cols-4 gap-4 animate-pulse">
       {[1,2,3,4,5,6,7,8].map(i => <div key={i} className="h-24 bg-white rounded-xl border border-gray-200"></div>)}
    </div>;
  }

  const kpis = [
    { label: "Total Users", value: data.totalUsers, icon: <Users className="text-blue-500" /> },
    { label: "Active Users", value: data.activeUsers, icon: <UserCheck className="text-green-500" /> },
    { label: "Pending Approvals", value: data.pendingApprovals, icon: <Clock className="text-orange-500" /> },
    { label: "System Alerts", value: data.systemAlerts, icon: <ShieldAlert className="text-red-500" /> },
    { label: "Field Officers", value: data.fieldOfficers, icon: <Activity className="text-teal-500" /> },
    { label: "Veterinarians", value: data.veterinarians, icon: <Building2 className="text-indigo-500" /> },
    { label: "Districts", value: data.districts, icon: <MapPin className="text-purple-500" /> },
  ];

  return (
    <div className="space-y-6">
       <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {kpis.map((kpi, idx) => (
             <div key={idx} className="bg-white p-5 rounded-xl shadow-sm border border-gray-200 flex flex-col justify-between hover:shadow-md transition-shadow">
                <div className="flex justify-between items-start mb-2">
                   <span className="text-sm font-medium text-gray-500">{kpi.label}</span>
                   <div className="p-2 bg-gray-50 rounded-lg">{kpi.icon}</div>
                </div>
                <div className="text-3xl font-bold text-gray-900">{kpi.value}</div>
             </div>
          ))}
       </div>

       <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <div className="p-5 border-b border-gray-200 bg-gray-50">
             <h3 className="text-lg font-bold text-gray-900">Recent Administrative Activity</h3>
          </div>
          <div className="divide-y divide-gray-100">
             {data.recentActivity.map((act: any) => (
                <div key={act.id} className="p-4 flex justify-between items-center hover:bg-gray-50">
                   <div>
                      <p className="font-bold text-gray-900">{act.action}</p>
                      <p className="text-sm text-gray-500">{act.details}</p>
                   </div>
                   <span className="text-xs font-medium text-gray-400 bg-gray-100 px-2 py-1 rounded-md">{act.time}</span>
                </div>
             ))}
          </div>
       </div>
    </div>
  );
}
