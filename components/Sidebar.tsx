import { NavLink } from "react-router-dom";
import { useMultilingual } from "../context/MultilingualContext";
import { 
  LayoutDashboard, Activity, Map as MapIcon, BrainCircuit, FileText, 
  HeartPulse, Stethoscope, TestTube2, Syringe, BellRing, Languages, 
  WifiOff, Info, BarChart3, Settings 
} from "lucide-react";

export default function Sidebar() {
  const { t } = useMultilingual();

  const navGroups = [
    {
      title: "GENERAL",
      items: [
        { id: "dashboard", label: t("nav.dashboard"), icon: LayoutDashboard, path: "/" }
      ]
    },
    {
      title: "SURVEILLANCE",
      items: [
        { id: "surveillance", label: t("nav.surveillance"), icon: Activity, path: "/surveillance" },
        { id: "gis", label: t("nav.gis"), icon: MapIcon, path: "/gis" },
        { id: "ai", label: t("nav.ai"), icon: BrainCircuit, path: "/ai" },
        { id: "reporting", label: t("nav.reporting"), icon: FileText, path: "/reporting" }
      ]
    },
    {
      title: "ANIMAL HEALTH",
      items: [
        { id: "animal-health", label: t("nav.animalHealth"), icon: HeartPulse, path: "/animal-health" },
        { id: "vet-response", label: t("nav.vetResponse"), icon: Stethoscope, path: "/vet-response" },
        { id: "lab", label: t("nav.lab"), icon: TestTube2, path: "/lab" },
        { id: "vaccination", label: t("nav.vaccination"), icon: Syringe, path: "/vaccination" }
      ]
    },
    {
      title: "INSIGHTS",
      items: [
        { id: "alerts", label: t("nav.alerts"), icon: BellRing, path: "/alerts" },
        { id: "analytics", label: t("nav.analytics"), icon: BarChart3, path: "/analytics" }
      ]
    },
    {
      title: "RESOURCES",
      items: [
        { id: "disease-info", label: t("nav.diseaseInfo"), icon: Info, path: "/disease-info" }
      ]
    },
    {
      title: "SYSTEM",
      items: [
        { id: "multilingual", label: t("nav.multilingual"), icon: Languages, path: "/multilingual" },
        { id: "offline", label: t("nav.offline"), icon: WifiOff, path: "/offline" },
        { id: "admin", label: t("nav.admin"), icon: Settings, path: "/admin" }
      ]
    }
  ];

  return (
    <div className="w-64 h-screen bg-sidebar text-white flex flex-col fixed left-0 top-0 overflow-hidden">
      <div className="p-4 flex flex-col gap-2 border-b border-gray-700 shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center shrink-0">
            <span className="font-bold text-white text-sm">MH</span>
          </div>
          <div className="overflow-hidden">
            <h2 className="text-sm font-bold truncate">Maha Vet Health</h2>
            <p className="text-xs text-gray-400 truncate">Govt. Officer</p>
          </div>
        </div>
      </div>
      
      <nav className="flex-1 overflow-y-auto py-2 custom-scrollbar">
        {navGroups.map((group, gIdx) => (
          <div key={gIdx} className="mb-4">
             <div className="px-5 mb-2">
                <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">{group.title}</span>
             </div>
             <ul className="space-y-0.5">
                {group.items.map((item) => {
                  const Icon = item.icon;
                  return (
                    <li key={item.id} className="px-2">
                      <NavLink 
                        to={item.path}
                        className={({ isActive }) => 
                          `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                            isActive 
                              ? "bg-brandBlue text-white font-medium" 
                              : "text-gray-300 hover:bg-white/10 hover:text-white"
                          }`
                        }
                      >
                        <Icon size={18} className="shrink-0" />
                        <span className="truncate">{item.label}</span>
                      </NavLink>
                    </li>
                  );
                })}
             </ul>
          </div>
        ))}
      </nav>
    </div>
  );
}
