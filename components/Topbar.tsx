import { Bell, Menu } from "lucide-react";
import { useAlerts } from "../context/AlertsContext";

export default function Topbar() {
  const { unreadCount } = useAlerts();

  return (
    <header className="h-14 bg-white border-b border-gray-200 flex items-center justify-between px-6 sticky top-0 z-10">
      <div className="flex items-center gap-4">
        <button className="md:hidden text-gray-500 hover:text-gray-700">
          <Menu size={20} />
        </button>
        <h1 className="text-lg font-semibold text-gray-800">Livestock Health Surveillance - Maharashtra</h1>
      </div>
      
      <div className="flex items-center gap-6">
        <div className="text-sm text-gray-500 flex items-center gap-2">
          <span>{new Date().toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })}</span>
        </div>
        
        <div className="flex items-center gap-3">
          <button className="text-gray-500 hover:text-gray-700 relative">
            <Bell size={20} />
            {unreadCount > 0 && (
              <span className="absolute -top-1 -right-1 bg-red-600 text-white text-[10px] w-4 h-4 rounded-full flex items-center justify-center">
                {unreadCount}
              </span>
            )}
          </button>
          
          <div className="flex items-center gap-2 pl-3 border-l border-gray-200">
            <div className="w-8 h-8 rounded-full bg-[#0D8ABC] text-white flex items-center justify-center text-xs font-bold" aria-hidden="true">
              GO
            </div>
            <div className="hidden md:block">
              <p className="text-sm font-medium text-gray-700">Govt. Officer</p>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}

