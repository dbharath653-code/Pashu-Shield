import { useState } from "react";
import {
  Bell, Menu, Globe,
  ChevronDown, Shield, Check, Key, LogOut,
} from "lucide-react";
import { useAlerts } from "../context/AlertsContext";
import { useMultilingual, LANGUAGE_NAMES } from "../context/MultilingualContext";
import type { LanguageCode } from "../context/MultilingualContext";
import { useAuth } from "../context/AuthContext";
import type { RoleType } from "../context/AuthContext";
import { useSync } from "../services/SyncService";
import { useNavigate } from "react-router-dom";

interface TopbarProps {
  onOpenMobileMenu?: () => void;
}

export default function Topbar({ onOpenMobileMenu }: TopbarProps) {
  const { unreadCount } = useAlerts();
  const { language, setLanguage, t } = useMultilingual();
  const { user, role, setRole, logout } = useAuth();
  const {
    isOnline,
    serverReachable,
    pendingCount,
    isSyncing,
    openSyncModal,
    feedStatus
  } = useSync();
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

  // Issue 16: sync state + live-stream state merged into ONE status control.
  const statusLabel = !isOnline
    ? "Offline"
    : !serverReachable
    ? "Server Offline"
    : isSyncing
    ? "Syncing…"
    : pendingCount > 0
    ? `Sync: ${pendingCount}`
    : "Synced";
  const statusDot = !isOnline
    ? "bg-red-500"
    : !serverReachable || pendingCount > 0
    ? "bg-amber-500"
    : isSyncing
    ? "bg-blue-500 animate-pulse"
    : "bg-emerald-500";
  const feedDot = feedStatus === "LIVE"
    ? "bg-emerald-500 animate-pulse"
    : feedStatus === "UPDATING"
    ? "bg-amber-500"
    : "bg-gray-400";
  const statusDescription = `Sync status: ${statusLabel}. Live updates: ${feedStatus}. Open sync manager.`;

  return (
    <header className="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-3 sm:px-4 lg:px-6 sticky top-0 z-40 shadow-xs">
      {/* Left Title & Mobile Hamburger Button */}
      <div className="flex items-center gap-2.5 sm:gap-3">
        <button
          onClick={onOpenMobileMenu}
          aria-label="Open navigation menu"
          className="btn btn-ghost min-h-[40px] min-w-[40px] lg:hidden"
        >
          <Menu size={22} />
        </button>
        <div>
          {/* Issue 10: brand mark is a <p>, not an <h1> — each page owns the single H1. */}
          <p className="text-base lg:text-lg font-black text-gray-900 leading-tight tracking-tight">
            Pashu-Shield
          </p>
          {/* Issue 6: subtitle raised from 11px to the 12px minimum. */}
          <p className="text-xs text-gray-500 hidden sm:block truncate max-w-xs md:max-w-md">
            Maharashtra Livestock Disease Surveillance & Response
          </p>
        </div>
      </div>

      {/* Right Controls — Issue 16: roomier gaps + merged status control. */}
      <div className="flex items-center gap-2 sm:gap-3">
        {/* Combined Sync + Live-stream status (single control, neutral variant). */}
        <button
          onClick={openSyncModal}
          className="btn btn-neutral"
          title={statusDescription}
          aria-label={statusDescription}
        >
          <span className={`h-2 w-2 rounded-full shrink-0 ${statusDot}`} aria-hidden="true" />
          <span className="hidden sm:inline">{statusLabel}</span>

          {/* Live-stream state, grouped inside the same control on md+ screens. */}
          <span className="hidden md:inline text-gray-400" aria-hidden="true">·</span>
          <span
            className="hidden md:inline-flex items-center gap-1 text-gray-500"
            title={`Live updates: ${feedStatus}`}
          >
            <span className={`h-2 w-2 rounded-full ${feedDot}`} aria-hidden="true" />
            <span>{feedStatus}</span>
          </span>

          {/* On small mobile: show count badge if pending */}
          {pendingCount > 0 && (
            <span className="sm:hidden min-w-5 h-5 px-1 rounded-full text-xs font-bold bg-amber-200 text-amber-900 inline-flex items-center justify-center">
              {pendingCount}
            </span>
          )}
        </button>

        {/* Dedicated Portals entry — lg+ only; also reachable via Role menu + Profile menu. */}
        <button
          onClick={() => navigate("/login")}
          className="btn btn-primary hidden lg:inline-flex"
          title="Access Separate Role Login & Sign Up Portals"
        >
          <Key size={13} />
          <span>Role Portals</span>
        </button>

        {/* 8-Language Switcher Dropdown */}
        <div className="relative">
          <button
            onClick={() => {
              setShowLangDropdown(!showLangDropdown);
              setShowRoleDropdown(false);
              setShowUserDropdown(false);
            }}
            className="btn btn-neutral"
            aria-haspopup="listbox"
            aria-expanded={showLangDropdown}
            aria-label="Select language"
          >
            <Globe size={14} className="text-blue-700" />
            <span className="hidden sm:inline">{LANGUAGE_NAMES[language]?.native || "English"}</span>
            <span className="sm:hidden">{language.toUpperCase()}</span>
            <ChevronDown size={12} className="text-gray-400" />
          </button>

          {showLangDropdown && (
            <div className="absolute right-0 mt-2 w-44 bg-white rounded-xl shadow-xl border border-gray-100 py-1 z-50" role="listbox">
              <div className="px-3 py-1.5 border-b border-gray-100 text-xs font-bold text-gray-400 tracking-wide">
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
                    language === code ? "text-blue-700 font-bold bg-blue-50/50" : "text-gray-700"
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
            className="btn btn-neutral"
            aria-haspopup="listbox"
            aria-expanded={showRoleDropdown}
            aria-label="Switch role"
          >
            <Shield size={14} className="text-blue-700 shrink-0" />
            <span className="truncate max-w-[70px] sm:max-w-[120px]">
              {rolesList.find((r) => r.role === role)?.badge || role}
            </span>
            <ChevronDown size={12} className="text-gray-400" />
          </button>

          {showRoleDropdown && (
            <div className="absolute right-0 mt-2 w-64 bg-white rounded-xl shadow-2xl border border-gray-100 py-1.5 z-50" role="listbox">
              <div className="px-3 py-1.5 border-b border-gray-100 text-xs font-bold text-gray-400 tracking-wide flex justify-between items-center">
                <span>Quick Role Switch</span>
                <button
                  onClick={() => {
                    setShowRoleDropdown(false);
                    navigate("/login");
                  }}
                  className="text-blue-700 hover:underline lowercase font-normal"
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
                  className={`w-full text-left px-3 py-2 text-xs flex items-center justify-between hover:bg-blue-50 transition-colors ${
                    role === r.role ? "text-blue-700 font-bold bg-blue-50/60" : "text-gray-700"
                  }`}
                >
                  <div className="overflow-hidden">
                    <p className="font-medium truncate">{r.label}</p>
                  </div>
                  {role === r.role && <Check size={14} className="shrink-0 text-blue-700 ml-2" />}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Alert Bell */}
        <button
          onClick={() => navigate("/alerts")}
          className="btn btn-ghost min-h-[40px] min-w-[40px] relative"
          title={t("nav.alerts")}
          aria-label={t("nav.alerts")}
        >
          <Bell size={18} />
          {unreadCount > 0 && (
            <span className="absolute top-1 right-1 bg-red-600 text-white text-xs font-bold min-w-5 h-5 px-1 rounded-full inline-flex items-center justify-center animate-pulse">
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
            className="btn btn-ghost"
            aria-label="User Profile Menu"
            aria-haspopup="menu"
            aria-expanded={showUserDropdown}
          >
            <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-blue-600 to-indigo-700 text-white flex items-center justify-center text-xs font-bold shadow-xs">
              {user?.full_name ? user.full_name.charAt(0).toUpperCase() : "U"}
            </div>
            {/* Issue 7: wider cap + full-name tooltip so the name is never silently clipped. */}
            <div className="text-left hidden lg:block min-w-0">
              <p
                className="text-xs font-bold text-gray-900 leading-tight truncate max-w-[180px]"
                title={user?.full_name || "User"}
              >
                {user?.full_name || "User"}
              </p>
              <p className="text-xs text-gray-500 uppercase tracking-wider">{role}</p>
            </div>
            <ChevronDown size={12} className="text-gray-400 hidden lg:block" />
          </button>

          {showUserDropdown && (
            <div className="absolute right-0 mt-2 w-56 bg-white rounded-xl shadow-2xl border border-gray-100 py-2 z-50" role="menu">
              <div className="px-3 py-2 border-b border-gray-100">
                <p className="text-xs font-bold text-gray-900 truncate">{user?.full_name}</p>
                <p className="text-xs text-gray-500 truncate">{user?.email}</p>
                <span className="inline-block mt-1 px-2 py-0.5 text-xs font-bold rounded-lg bg-blue-50 text-blue-700 border border-blue-200">
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
                  <Key size={14} className="text-blue-700" />
                  <span>Switch Portal / Role</span>
                </button>

                <button
                  onClick={() => {
                    setShowUserDropdown(false);
                    logout();
                    navigate("/login");
                  }}
                  className="w-full text-left px-3 py-2 text-xs text-red-700 hover:bg-red-50 flex items-center gap-2 font-semibold"
                >
                  <LogOut size={14} className="text-red-700" />
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
