import { useState } from "react";
import { Settings, Users, Shield, MapPin, Building2, Sliders, ScrollText, CheckSquare } from "lucide-react";
import AdminOverview from "./AdminOverview";
import UserManagement from "./UserManagement";
import RoleManagement from "./RoleManagement";
import LocationManagement from "./LocationManagement";
import FacilityManagement from "./FacilityManagement";
import SystemConfig from "./SystemConfig";
import AuditLog from "./AuditLog";
import ApprovalCenter from "./ApprovalCenter";

export default function AdminManagement() {
  const [activeTab, setActiveTab] = useState("overview");

  const tabs = [
    { id: "overview", label: "Overview", icon: <Settings size={18} /> },
    { id: "users", label: "User Management", icon: <Users size={18} /> },
    { id: "roles", label: "Roles & Permissions", icon: <Shield size={18} /> },
    { id: "locations", label: "Districts & Locations", icon: <MapPin size={18} /> },
    { id: "facilities", label: "Departments & Facilities", icon: <Building2 size={18} /> },
    { id: "config", label: "System Configuration", icon: <Sliders size={18} /> },
    { id: "audit", label: "Audit Log", icon: <ScrollText size={18} /> },
    { id: "approvals", label: "Approval Center", icon: <CheckSquare size={18} /> },
  ];

  return (
    <div className="flex flex-col h-full bg-gray-50 overflow-hidden">
      {/* Module Header */}
      <div className="bg-white p-4 lg:p-6 border-b border-gray-200 shrink-0">
        <h1 className="text-2xl font-bold text-gray-900 tracking-tight">Administration</h1>
        <p className="text-gray-500 text-sm mt-1">Manage users, roles, departments, locations and system configuration.</p>
      </div>

      <div className="flex flex-1 overflow-hidden flex-col md:flex-row">
        {/* Local Sidebar / Top Tabs (Mobile) */}
        <div className="w-full md:w-64 bg-white border-r border-gray-200 shrink-0 overflow-x-auto md:overflow-y-auto">
           <div className="flex md:flex-col p-2 md:p-4 gap-1 min-w-max md:min-w-0">
              {tabs.map(tab => (
                 <button
                   key={tab.id}
                   onClick={() => setActiveTab(tab.id)}
                   className={`flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors ${activeTab === tab.id ? "bg-brandBlue text-white shadow-sm" : "text-gray-600 hover:bg-gray-100"}`}
                 >
                   {tab.icon}
                   {tab.label}
                 </button>
              ))}
           </div>
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-y-auto p-4 lg:p-6">
           {activeTab === "overview" && <AdminOverview />}
           {activeTab === "users" && <UserManagement />}
           {activeTab === "roles" && <RoleManagement />}
           {activeTab === "locations" && <LocationManagement />}
           {activeTab === "facilities" && <FacilityManagement />}
           {activeTab === "config" && <SystemConfig />}
           {activeTab === "audit" && <AuditLog />}
           {activeTab === "approvals" && <ApprovalCenter />}
        </div>
      </div>
    </div>
  );
}
