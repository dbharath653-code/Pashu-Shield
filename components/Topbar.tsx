import { useState } from "react";
import { 
  Bell, Menu, Globe, 
  ChevronDown, Shield, Check, Key, LogOut
} from "lucide-react";
import { useAlerts } from "../context/AlertsContext";
import { useMultilingual, LANGUAGE_NAMES } from "../context/MultilingualContext";
import type { LanguageCode } from "../context/MultilingualContext";
import { useAuth } from "../context/AuthContext";
import type { RoleType } from "../context/AuthContext";
import { useNavigate } from "react-router-dom";

export default function Topbar() {
  const { unreadCount } = useAlerts();
  const { language, setLanguage, t } = useMultilingual();
  const { user, role, setRole, wsStatus, logout } = useAuth();
  const navigate = useNavigate();

  const [showRoleDropdown, setShowRoleDropdown] = useState(false);
  const [showLangDropdown, setShowLangDropdown] = useState(false);
  const [showUserDropdown, setShowUserDropdown] = useState(false);

  const rolesList: { role: RoleType; label: string; badge: string; loginUrl: string }[] = [
    { role: "FARMER", label: "Farmer / Livestock Keeper", badge: "🌾 Farmer", loginUrl: "/login/farmer" },
    { role: "VETERINARIAN", label: "Veterinary Officer (Dr. Deshmukh)", badge: "👨‍⚕️ Vet", loginUrl: "/login/veterinary" },
    { role: "LAB_TECHNICIAN", label: "Lab Diagnostic Officer (DIS Pune)", badge: "🧪 Lab", loginUrl: "/login/laboratory" },
    { role: "DISTRICT_OFFICER", label: "District Officer (Pune DAHO)", badge: "🏛️ District", loginUrl: "/login/government" },
    { role: "STATE_OFFICER", label: "State Surveillance Coordinator", badge: "🏢 State", loginUrl: "/login/government" },
    { role: "SYSTEM_ADMIN", label: "System Administrator", badge: "⚙️ Admin", loginUrl: "/login/admin" }
  ];

  return (
    <header className="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-4 lg:px-6 sticky top-0 z-40 shadow-xs">
      {/* Left Title & Mobile Menu */}
      <div className="flex items-center gap-3">
        <button className="lg:hidden text-gray-500 hover:text-gray-700 p-1">
          <Menu size={20} />
        </button>
        <div>
          <h1 className="text-base lg:text-lg font-bold text-gray-900 leading-tight">
            Pashu-Shield
          </h1>
          <p className="text-[11px] text-gray-500 hidden sm:block">
            Maharashtra Livestock Disease Surveillance & Response
          </p>
        </div>
      </div>

      {/* Right Controls */}
      <div className="flex items-center gap-2 sm:gap-3">
        {/* Real-time WebSocket Status Indicator */}
        <div 
          className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border ${
            wsStatus === "CONNECTED"
              ? "bg-emerald-50 text-emerald-700 border-emerald-200"
              : wsStatus === "SYNCING"
              ? "bg-blue-50 text-blue-700 border-blue-200"
              : "bg-amber-50 text-amber-700 border-amber-200"
          }`}
          title={`Real-Time Synchronization: ${wsStatus}`}
        >
          <span 
            className={`w-2 h-2 rounded-full ${
              wsStatus === "CONNECTED" ? "bg-emerald-500 animate-pulse" : "bg-amber-500"
            }`}
          />
          <span className="hidden md:inline">{wsStatus}</span>
        </div>

        {/* Dedicated Portals & Login Direct Button */}
        <button
          onClick={() => navigate("/login")}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold transition-all shadow-xs"
          title="Access Separate Role Login & Sign Up Portals"
        >
          <Key size={13} />
          <span className="hidden sm:inline">Role Portals</span>
          <span className="sm:hidden">Login</span>
        </button>

        {/* 8-Language Switcher Dropdown */}
        <div className="relative">
          <button
            onClick={() => {
              setShowLangDropdown(!showLangDropdown);
              setShowRoleDropdown(false);
              setShowUserDropdown(false);
            }}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-gray-200 text-xs font-semibold text-gray-700 hover:bg-gray-50 transition-colors"
          >
            <Globe size={14} className="text-blue-600" />
            <span>{LANGUAGE_NAMES[language]?.native || "English"}</span>
            <ChevronDown size={12} className="text-gray-400" />
          </button>

          {showLangDropdown && (
            <div className="absolute right-0 mt-2 w-44 bg-white rounded-xl shadow-xl border border-gray-100 py-1 z-50">
              <div className="px-3 py-1.5 border-b border-gray-100 text-[10px] font-bold text-gray-400 uppercase">
                Select Language
              </div>
              {(Object.keys(LANGUAGE_NAMES) as LanguageCode[]).map((code) => (
                <button
                  key={code}
                  onClick={() => {
                    setLanguage(code);
                    setShowLangDropdown(false);
                  }}
                  className={`w-full text-left px-3 py-2 text-xs flex items-center justify-between hover:bg-blue-50 transition-colors ${
                    language === code ? "text-blue-600 font-bold bg-blue-50/50" : "text-gray-700"
                  }`}
                >
                  <span>{LANGUAGE_NAMES[code].native}</span>
                  {language === code && <Check size={14} />}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Role Quick Switcher Dropdown */}
        <div className="relative">
          <button
            onClick={() => {
              setShowRoleDropdown(!showRoleDropdown);
              setShowLangDropdown(false);
              setShowUserDropdown(false);
            }}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-gray-100 hover:bg-gray-200 text-xs font-semibold text-gray-800 transition-colors border border-gray-300/70"
          >
            <Shield size={14} className="text-indigo-600" />
            <span className="truncate max-w-[110px] sm:max-w-none">
              {rolesList.find((r) => r.role === role)?.badge || role}
            </span>
            <ChevronDown size={12} className="text-gray-500" />
          </button>

          {showRoleDropdown && (
            <div className="absolute right-0 mt-2 w-64 bg-white rounded-xl shadow-2xl border border-gray-100 py-1.5 z-50">
              <div className="px-3 py-1.5 border-b border-gray-100 text-[10px] font-bold text-gray-400 uppercase flex justify-between items-center">
                <span>Quick Role Switch</span>
                <button
                  onClick={() => {
                    setShowRoleDropdown(false);
                    navigate("/login");
                  }}
                  className="text-blue-600 hover:underline lowercase font-normal"
                >
                  portal hub
                </button>
              </div>
              {rolesList.map((r) => (
                <button
                  key={r.role}
                  onClick={() => {
                    setRole(r.role);
                    setShowRoleDropdown(false);
                  }}
                  className={`w-full text-left px-3 py-2 text-xs flex items-center justify-between hover:bg-indigo-50 transition-colors ${
                    role === r.role ? "text-indigo-700 font-bold bg-indigo-50/60" : "text-gray-700"
                  }`}
                >
                  <div className="overflow-hidden">
                    <p className="font-medium truncate">{r.label}</p>
                  </div>
                  {role === r.role && <Check size={14} className="shrink-0 text-indigo-600 ml-2" />}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Alert Bell */}
        <button
          onClick={() => navigate("/alerts")}
          className="text-gray-500 hover:text-gray-700 relative p-1.5 rounded-lg hover:bg-gray-100 transition-colors"
          title={t("nav.alerts")}
        >
          <Bell size={18} />
          {unreadCount > 0 && (
            <span className="absolute 0 top-0.5 right-0.5 bg-red-600 text-white text-[10px] font-bold w-4 h-4 rounded-full flex items-center justify-center animate-pulse">
              {unreadCount}
            </span>
          )}
        </button>

        {/* User Badge & Profile Menu */}
        <div className="relative">
          <button
            onClick={() => {
              setShowUserDropdown(!showUserDropdown);
              setShowRoleDropdown(false);
              setShowLangDropdown(false);
            }}
            className="flex items-center gap-2 pl-2 border-l border-gray-200 hover:opacity-80 transition-opacity"
          >
            <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-blue-600 to-indigo-700 text-white flex items-center justify-center text-xs font-bold shadow-xs">
              {user?.full_name ? user.full_name.charAt(0).toUpperCase() : "U"}
            </div>
            <div className="text-left hidden lg:block">
              <p className="text-xs font-bold text-gray-800 leading-tight truncate max-w-[120px]">
                {user?.full_name || "User"}
              </p>
              <p className="text-[10px] text-gray-500 uppercase tracking-wider">{role}</p>
            </div>
            <ChevronDown size={12} className="text-gray-400 hidden lg:block" />
          </button>

          {showUserDropdown && (
            <div className="absolute right-0 mt-2 w-56 bg-white rounded-xl shadow-2xl border border-gray-100 py-2 z-50">
              <div className="px-3 py-2 border-b border-gray-100">
                <p className="text-xs font-bold text-gray-900 truncate">{user?.full_name}</p>
                <p className="text-[11px] text-gray-500 truncate">{user?.email}</p>
                <span className="inline-block mt-1 px-2 py-0.5 text-[10px] font-bold rounded bg-blue-50 text-blue-700 border border-blue-200">
                  {role}
                </span>
              </div>

              <div className="py-1">
                <button
                  onClick={() => {
                    setShowUserDropdown(false);
                    navigate("/login");
                  }}
                  className="w-full text-left px-3 py-2 text-xs text-gray-700 hover:bg-gray-50 flex items-center gap-2"
                >
                  <Key size={14} className="text-blue-600" />
                  <span>Switch Portal / Role</span>
                </button>

                <button
                  onClick={() => {
                    setShowUserDropdown(false);
                    logout();
                    navigate("/login");
                  }}
                  className="w-full text-left px-3 py-2 text-xs text-red-600 hover:bg-red-50 flex items-center gap-2 font-semibold"
                >
                  <LogOut size={14} className="text-red-500" />
                  <span>Sign Out</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
