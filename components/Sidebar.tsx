import { NavLink } from "react-router-dom";
import { useMultilingual } from "../context/MultilingualContext";
import { useAuth } from "../context/AuthContext";
import { 
  LayoutDashboard, Activity, Map as MapIcon, BrainCircuit, FileText, 
  HeartPulse, Stethoscope, TestTube2, Syringe, BellRing, Languages, 
  WifiOff, Info, BarChart3, Settings, Home, Shield, Key, UserPlus, X
} from "lucide-react";

interface SidebarProps {
  onClose?: () => void;
  className?: string;
  isMobile?: boolean;
}

export default function Sidebar({ onClose, className = "", isMobile = false }: SidebarProps) {
  const { t } = useMultilingual();
  const { role } = useAuth();

  // Role-based Navigation configuration
  const getNavGroups = () => {
    let groups: { title: string; items: { id: string; label: string; icon: any; path: string }[] }[] = [];

    if (role === "FARMER") {
      groups = [
        {
          title: "Farmer Services",
          items: [
            { id: "farmer-home", label: t("nav.farmerHome"), icon: Home, path: "/" },
            { id: "reporting", label: t("nav.reporting"), icon: FileText, path: "/reporting" },
            { id: "animal-health", label: t("nav.animalHealth"), icon: HeartPulse, path: "/animal-health" },
            { id: "vet-response", label: t("nav.vetResponse"), icon: Stethoscope, path: "/vet-response" },
            { id: "vaccination", label: t("nav.vaccination"), icon: Syringe, path: "/vaccination" },
            { id: "lab", label: t("nav.lab"), icon: TestTube2, path: "/lab" },
            { id: "alerts", label: t("nav.alerts"), icon: BellRing, path: "/alerts" }
          ]
        },
        {
          title: "Knowledge & Tools",
          items: [
            { id: "disease-info", label: t("di.title"), icon: Info, path: "/disease-info" },
            { id: "multilingual", label: t("nav.multilingual"), icon: Languages, path: "/multilingual" },
            { id: "offline", label: t("nav.offline"), icon: WifiOff, path: "/offline" }
          ]
        }
      ];
    } else if (role === "VETERINARIAN") {
      groups = [
        {
          title: "Clinical Response",
          items: [
            { id: "vet-response", label: t("nav.vetResponse"), icon: Stethoscope, path: "/vet-response" },
            { id: "reporting", label: t("nav.reporting"), icon: FileText, path: "/reporting" },
            { id: "animal-health", label: t("nav.animalHealth"), icon: HeartPulse, path: "/animal-health" },
            { id: "lab", label: t("nav.lab"), icon: TestTube2, path: "/lab" },
            { id: "vaccination", label: t("nav.vaccination"), icon: Syringe, path: "/vaccination" },
            { id: "gis", label: t("nav.gis"), icon: MapIcon, path: "/gis" }
          ]
        },
        {
          title: "Epidemiology",
          items: [
            { id: "dashboard", label: t("nav.dashboard"), icon: LayoutDashboard, path: "/surveillance" },
            { id: "alerts", label: t("nav.alerts"), icon: BellRing, path: "/alerts" },
            { id: "offline", label: t("nav.offline"), icon: WifiOff, path: "/offline" }
          ]
        }
      ];
    } else if (role === "LAB_TECHNICIAN") {
      groups = [
        {
          title: "Laboratory Operations",
          items: [
            { id: "lab", label: t("nav.lab"), icon: TestTube2, path: "/lab" },
            { id: "vet-response", label: t("nav.vetResponse"), icon: Stethoscope, path: "/vet-response" },
            { id: "reporting", label: t("nav.reporting"), icon: FileText, path: "/reporting" },
            { id: "alerts", label: t("nav.alerts"), icon: BellRing, path: "/alerts" }
          ]
        },
        {
          title: "Surveillance",
          items: [
            { id: "surveillance", label: t("nav.surveillance"), icon: Activity, path: "/surveillance" },
            { id: "offline", label: t("nav.offline"), icon: WifiOff, path: "/offline" }
          ]
        }
      ];
    } else {
      // Default: Government Official & System Admin (Full Oversight)
      groups = [
        {
          title: "Surveillance & GIS",
          items: [
            { id: "dashboard", label: t("nav.dashboard"), icon: LayoutDashboard, path: "/" },
            { id: "surveillance", label: t("nav.surveillance"), icon: Activity, path: "/surveillance" },
            { id: "gis", label: t("nav.gis"), icon: MapIcon, path: "/gis" },
            { id: "ai", label: t("nav.ai"), icon: BrainCircuit, path: "/ai" },
            { id: "reporting", label: t("nav.reporting"), icon: FileText, path: "/reporting" }
          ]
        },
        {
          title: "Animal Health & Response",
          items: [
            { id: "animal-health", label: t("nav.animalHealth"), icon: HeartPulse, path: "/animal-health" },
            { id: "vet-response", label: t("nav.vetResponse"), icon: Stethoscope, path: "/vet-response" },
            { id: "lab", label: t("nav.lab"), icon: TestTube2, path: "/lab" },
            { id: "vaccination", label: t("nav.vaccination"), icon: Syringe, path: "/vaccination" }
          ]
        },
        {
          title: "Intelligence & Admin",
          items: [
            { id: "alerts", label: t("nav.alerts"), icon: BellRing, path: "/alerts" },
            { id: "analytics", label: t("nav.analytics"), icon: BarChart3, path: "/analytics" },
            { id: "disease-info", label: t("nav.diseaseInfo"), icon: Info, path: "/disease-info" },
            { id: "multilingual", label: t("nav.multilingual"), icon: Languages, path: "/multilingual" },
            { id: "offline", label: t("nav.offline"), icon: WifiOff, path: "/offline" },
            { id: "admin", label: t("nav.admin"), icon: Settings, path: "/admin" }
          ]
        }
      ];
    }

    // Append Portals & Authentication section for all roles
    groups.push({
      title: "Portals & Access",
      items: [
        { id: "role-portals", label: "Separate Role Portals", icon: Key, path: "/login" },
        { id: "account-signup", label: "Register New Account", icon: UserPlus, path: "/signup" }
      ]
    });

    return groups;
  };

  const navGroups = getNavGroups();

  return (
    <div
      className={`w-64 h-full bg-sidebar text-white flex flex-col overflow-hidden shadow-xl ${className}`}
    >
      {/* Brand Header */}
      <div className="p-4 flex items-center justify-between border-b border-gray-700/80 shrink-0 bg-gray-900/40">
        <div className="flex items-center gap-3 overflow-hidden">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center shrink-0 shadow-md">
            <Shield size={20} className="text-white" />
          </div>
          <div className="overflow-hidden">
            <p className="text-sm font-black tracking-tight text-white">Pashu-Shield</p>
            <p className="text-xs text-gray-400 font-medium truncate">
              {role.replace("_", " ")}
            </p>
          </div>
        </div>

        {/* Close button on mobile/tablet drawer */}
        {isMobile && (
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-white/10 transition-colors"
            aria-label="Close navigation"
          >
            <X size={20} />
          </button>
        )}
      </div>

      {/* Nav List */}
      <nav className="flex-1 overflow-y-auto py-3 custom-scrollbar">
        {navGroups.map((group, gIdx) => (
          <div key={gIdx} className="mb-4">
            <div className="px-5 mb-2">
              <span className="text-xs font-bold text-gray-400 tracking-wide">
                {group.title}
              </span>
            </div>
            <ul className="space-y-0.5">
              {group.items.map((item) => {
                const Icon = item.icon;
                return (
                  <li key={item.id} className="px-2">
                    <NavLink
                      to={item.path}
                      end={item.path === "/" || item.path === "/farmer"}
                      onClick={() => {
                        if (isMobile && onClose) onClose();
                      }}
                      className={({ isActive }) =>
                        `flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-semibold transition-all duration-150 min-h-[40px] touch-manipulation ${
                          isActive
                            ? "bg-brandBlue text-white shadow-md font-bold"
                            : "text-gray-400 hover:bg-white/10 hover:text-white"
                        }`
                      }
                    >
                      <Icon size={17} className="shrink-0" />
                      <span className="truncate">{item.label}</span>
                    </NavLink>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>

      {/* Bottom Emergency Help Box */}
      <div className="p-3 bg-gray-900/60 border-t border-gray-800 text-xs text-gray-400 shrink-0">
        <p className="font-bold text-white">24x7 Help: 1962</p>
        <p className="text-gray-400">Govt. of Maharashtra</p>
      </div>
    </div>
  );
}
