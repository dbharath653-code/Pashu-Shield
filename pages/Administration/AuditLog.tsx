import React, { useState, useEffect } from "react";
import { AdminService } from "../../services/AdminService";
import type { AuditLogEntry } from "../../services/AdminService";
import { Search, Download, Clock } from "lucide-react";

export default function AuditLog() {
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    AdminService.getAuditLogs().then(res => { setLogs(res); setLoading(false); });
  }, []);

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 flex flex-col h-[calc(100vh-10rem)]">
       <div className="p-5 border-b border-gray-200 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-gray-50 rounded-t-xl">
          <div>
             <h3 className="text-lg font-bold text-gray-900">Audit Log</h3>
             <p className="text-sm text-gray-500">Track all system activities and security events.</p>
          </div>
          <div className="flex items-center gap-3">
             <div className="relative w-64">
                <Search className="absolute left-3 top-2.5 text-gray-400" size={18} />
                <input type="text" placeholder="Search logs..." className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg text-sm" />
             </div>
             <button className="p-2 border border-gray-300 rounded-lg text-gray-600 hover:bg-gray-50"><Download size={18}/></button>
          </div>
       </div>

       <div className="flex-1 overflow-auto">
          <table className="w-full text-left text-sm whitespace-nowrap">
             <thead className="bg-gray-100 text-gray-600 font-medium sticky top-0 shadow-sm z-10">
                <tr>
                   <th className="px-6 py-4">Timestamp</th>
                   <th className="px-6 py-4">User</th>
                   <th className="px-6 py-4">Action</th>
                   <th className="px-6 py-4">Module</th>
                   <th className="px-6 py-4">Description</th>
                   <th className="px-6 py-4">IP Address</th>
                   <th className="px-6 py-4">Result</th>
                </tr>
             </thead>
             <tbody className="divide-y divide-gray-100">
                {loading ? <tr><td colSpan={7} className="text-center p-8">Loading...</td></tr> : logs.map(log => (
                   <tr key={log.id} className="hover:bg-gray-50 font-mono text-xs">
                      <td className="px-6 py-3 flex items-center gap-1 text-gray-500"><Clock size={12}/> {log.timestamp}</td>
                      <td className="px-6 py-3"><span className="font-bold text-gray-800 font-sans">{log.user}</span> <br/><span className="text-gray-500">{log.role}</span></td>
                      <td className="px-6 py-3"><span className="px-2 py-1 bg-blue-50 text-blue-700 rounded font-bold">{log.action}</span></td>
                      <td className="px-6 py-3 text-gray-700">{log.module}</td>
                      <td className="px-6 py-3 text-gray-700 max-w-xs truncate" title={log.description}>{log.description}</td>
                      <td className="px-6 py-3 text-gray-500">{log.ip}</td>
                      <td className="px-6 py-3">
                         <span className={`px-2 py-1 font-bold rounded ${log.result==="Success"?"text-green-700 bg-green-50":"text-red-700 bg-red-50"}`}>{log.result}</span>
                      </td>
                   </tr>
                ))}
             </tbody>
          </table>
       </div>
    </div>
  );
}
