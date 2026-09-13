import React from "react";
import type { DiseaseTrend } from "../../services/AnalyticsService";
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  BarChart, Bar, PieChart, Pie, Cell 
} from "recharts";

interface Props {
  trends: DiseaseTrend[];
  distribution: { name: string; confirmed: number; suspected: number; recovered: number; deaths: number }[];
  labData: { positive: number; negative: number; pending: number };
}

export default function AnalyticsCharts({ trends, distribution, labData }: Props) {
  const pieData = [
    { name: "Positive", value: labData.positive, color: "#ef4444" },
    { name: "Negative", value: labData.negative, color: "#10b981" },
    { name: "Pending", value: labData.pending, color: "#f59e0b" },
  ];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
      
      {/* Trends Chart */}
      <div className="bg-white p-5 rounded-xl shadow-sm border border-gray-200">
         <h3 className="text-lg font-bold text-gray-900 mb-4">Disease Trends</h3>
         <div className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
               <LineChart data={trends} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                 <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e5e7eb" />
                 <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: "#6b7280" }} dy={10} />
                 <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: "#6b7280" }} />
                 <Tooltip contentStyle={{ borderRadius: "8px", border: "none", boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)" }} />
                 <Legend wrapperStyle={{ paddingTop: "20px" }} />
                 <Line type="monotone" dataKey="FMD" stroke="#3b82f6" strokeWidth={3} dot={false} activeDot={{ r: 6 }} />
                 <Line type="monotone" dataKey="LSD" stroke="#ef4444" strokeWidth={3} dot={false} />
                 <Line type="monotone" dataKey="PPR" stroke="#10b981" strokeWidth={3} dot={false} />
                 <Line type="monotone" dataKey="Brucellosis" stroke="#f59e0b" strokeWidth={3} dot={false} />
               </LineChart>
            </ResponsiveContainer>
         </div>
      </div>

      {/* Distribution Chart */}
      <div className="bg-white p-5 rounded-xl shadow-sm border border-gray-200">
         <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-bold text-gray-900">Disease Burden Distribution</h3>
         </div>
         <div className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
               <BarChart data={distribution} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                 <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e5e7eb" />
                 <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: "#6b7280" }} dy={10} />
                 <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: "#6b7280" }} />
                 <Tooltip cursor={{ fill: "#f3f4f6" }} contentStyle={{ borderRadius: "8px", border: "none", boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)" }} />
                 <Legend wrapperStyle={{ paddingTop: "20px" }} />
                 <Bar dataKey="confirmed" name="Confirmed" fill="#ef4444" radius={[4, 4, 0, 0]} />
                 <Bar dataKey="suspected" name="Suspected" fill="#f59e0b" radius={[4, 4, 0, 0]} />
                 <Bar dataKey="recovered" name="Recovered" fill="#10b981" radius={[4, 4, 0, 0]} />
               </BarChart>
            </ResponsiveContainer>
         </div>
      </div>
      
    </div>
  );
}

