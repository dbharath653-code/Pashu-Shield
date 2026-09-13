import React from "react";
import AlertsDashboard from "./AlertsDashboard";
import AlertList from "./AlertList";
import { Settings, RefreshCw, BellRing } from "lucide-react";
import { useAlerts } from "../../context/AlertsContext";

export default function AlertsManagement() {
  const { refreshAlerts, markAllAsRead, unreadCount } = useAlerts();

  return (
    <div className="flex flex-col h-full bg-gray-50 p-2 md:p-4">
      {/* Page Header */}
      <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200 mb-6">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
               <BellRing className="text-brandBlue" size={28} />
               ALERTS & NOTIFICATIONS
            </h1>
            <p className="text-gray-500 text-sm mt-1">Real-time livestock health surveillance and response alerts</p>
          </div>
          
          <div className="flex items-center gap-3 w-full md:w-auto">
            <div className="text-sm text-gray-500 font-medium px-4 border-r border-gray-200 hidden md:block">
               {new Date().toLocaleString()}
            </div>
            {unreadCount > 0 && (
              <button onClick={markAllAsRead} className="px-3 py-2 text-sm font-medium text-brandBlue hover:bg-blue-50 rounded-lg transition-colors">
                Mark all read
              </button>
            )}
            <button className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors" title="Notification Settings">
              <Settings size={20} />
            </button>
            <button onClick={refreshAlerts} className="p-2 text-brandBlue hover:bg-blue-50 bg-blue-50/50 rounded-lg transition-colors" title="Refresh Feed">
              <RefreshCw size={20} />
            </button>
          </div>
        </div>
      </div>

      <AlertsDashboard />

      {/* Main Alert List */}
      <AlertList />

    </div>
  );
}

