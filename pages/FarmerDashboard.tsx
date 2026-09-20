import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { 
  Mic, HeartPulse, AlertTriangle, Stethoscope, Syringe, 
  TestTube2, BellRing, MapPin, BookOpen, PhoneCall, 
  Clock, ShieldCheck, ArrowRight
} from "lucide-react";
import { useMultilingual } from "../context/MultilingualContext";
import { useAuth } from "../context/AuthContext";
import PashuMap from "../components/PashuMap";

export default function FarmerDashboard() {
  const { t, language } = useMultilingual();
  const { user } = useAuth();
  const navigate = useNavigate();

  const [recentReports, setRecentReports] = useState<any[]>([]);

  useEffect(() => {
    fetch("/api/v1/reports")
      .then((res) => res.json())
      .then((data) => {
        if (Array.isArray(data)) setRecentReports(data.slice(0, 3));
      })
      .catch(() => {});
  }, []);

  const actionCards = [
    {
      id: "voice",
      title: t("farmer.talk"),
      subtitle: language === "mr" ? "आवाजाने तक्रार करा किंवा माहिती विचारा" : "Voice reporting & instant guidance",
      icon: Mic,
      color: "from-blue-600 to-indigo-600",
      textColor: "text-white",
      badge: "AI Powered",
      onClick: () => {
        const voiceBtn = document.querySelector('button[aria-label="' + t("card.voiceInput") + '"]') as HTMLElement;
        if (voiceBtn) voiceBtn.click();
      }
    },
    {
      id: "report",
      title: t("farmer.reportSick"),
      subtitle: language === "mr" ? "आजारी जनावराची त्वरित नोंदणी" : "Quick syndromic field report",
      icon: AlertTriangle,
      color: "from-red-600 to-rose-700",
      textColor: "text-white",
      badge: "Emergency",
      onClick: () => navigate("/reporting")
    },
    {
      id: "vet",
      title: t("farmer.requestVet"),
      subtitle: language === "mr" ? "शासकीय पशुवैद्यक व मोबाइल युनिट" : "Dispatch Veterinary Officer (1962)",
      icon: Stethoscope,
      color: "from-teal-600 to-emerald-700",
      textColor: "text-white",
      badge: "Toll-Free 1962",
      onClick: () => navigate("/vet-response")
    },
    {
      id: "animals",
      title: t("farmer.myAnimals"),
      subtitle: language === "mr" ? "नोंदणीकृत जनावरे आणि कळप" : "Registered Cattle & Herds",
      icon: HeartPulse,
      color: "from-amber-600 to-orange-700",
      textColor: "text-white",
      onClick: () => navigate("/animal-health")
    },
    {
      id: "vaccine",
      title: t("farmer.vaccination"),
      subtitle: language === "mr" ? "एफएमडी आणि लंपी लसीकरण तारीख" : "NADCP Schedules & Due Dates",
      icon: Syringe,
      color: "from-purple-600 to-indigo-800",
      textColor: "text-white",
      onClick: () => navigate("/vaccination")
    },
    {
      id: "lab",
      title: t("farmer.labResults"),
      subtitle: language === "mr" ? "तपासणी निकाल आणि अहवाल" : "RT-PCR & Diagnostic Reports",
      icon: TestTube2,
      color: "from-cyan-600 to-blue-800",
      textColor: "text-white",
      onClick: () => navigate("/lab")
    },
    {
      id: "alerts",
      title: t("farmer.alerts"),
      subtitle: language === "mr" ? "गावातील रोग सूचना व सावधानता" : "Outbreak Warnings in Taluka",
      icon: BellRing,
      color: "from-orange-500 to-amber-600",
      textColor: "text-white",
      onClick: () => navigate("/alerts")
    },
    {
      id: "info",
      title: t("di.title"),
      subtitle: language === "mr" ? "रोग लक्षणे आणि घरगुती प्रथमोपचार" : "Disease Symptoms & Biosecurity",
      icon: BookOpen,
      color: "from-emerald-600 to-green-700",
      textColor: "text-white",
      onClick: () => navigate("/disease-info")
    }
  ];

  return (
    <div className="space-y-6 pb-12 max-w-7xl mx-auto">
      {/* Farmer Welcome Banner with Emergency 1962 Helpline */}
      <div className="bg-gradient-to-r from-emerald-800 via-teal-800 to-blue-900 rounded-3xl p-6 lg:p-8 text-white shadow-lg relative overflow-hidden">
        <div className="absolute right-0 top-0 bottom-0 w-1/3 bg-white/5 transform skew-x-12 pointer-events-none" />
        
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 relative z-10">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="px-3 py-1 bg-white/20 backdrop-blur rounded-full text-xs font-bold tracking-wide uppercase">
                {t("nav.farmerHome")}
              </span>
              <span className="text-emerald-200 text-xs font-semibold">
                📍 {user?.village || "Walwur"}, {user?.district || "Pune"}
              </span>
            </div>
            <h1 className="text-2xl md:text-3xl font-black tracking-tight">
              {language === "mr" ? `नमस्कार, ${user?.full_name || "शेतकरी मित्र"}` : `Welcome, ${user?.full_name || "Livestock Keeper"}`}
            </h1>
            <p className="text-emerald-100 text-sm mt-1 max-w-xl">
              {language === "mr"
                ? "पशु-शील्ड: महाराष्ट्र शासनाची २४x७ पशुआरोग्य सुरक्षा प्रणाली. कोणत्याही समस्येसाठी खालील बटणे दाबा."
                : "24x7 livestock surveillance & veterinary emergency assistance platform for Maharashtra."}
            </p>
          </div>

          <div className="flex flex-col sm:flex-row items-center gap-3">
            <a
              href="tel:1962"
              className="w-full sm:w-auto px-6 py-3.5 bg-red-600 hover:bg-red-700 text-white rounded-2xl font-bold flex items-center justify-center gap-2 shadow-lg transition-transform hover:scale-105 active:scale-95"
            >
              <PhoneCall size={20} className="animate-bounce" />
              <span>{t("farmer.emergencyCall")}</span>
            </a>
          </div>
        </div>
      </div>

      {/* Main Touch-Friendly Large Action Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {actionCards.map((card) => {
          const Icon = card.icon;
          return (
            <button
              key={card.id}
              onClick={card.onClick}
              className={`p-6 rounded-3xl bg-gradient-to-br ${card.color} ${card.textColor} shadow-md hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1 text-left flex flex-col justify-between min-h-[160px] relative overflow-hidden group focus:outline-none focus:ring-4 focus:ring-blue-300`}
            >
              <div className="flex justify-between items-start">
                <div className="p-3 bg-white/20 backdrop-blur rounded-2xl">
                  <Icon size={28} />
                </div>
                {card.badge && (
                  <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-white/30 tracking-wider uppercase">
                    {card.badge}
                  </span>
                )}
              </div>

              <div className="mt-4">
                <h3 className="text-lg font-bold leading-tight group-hover:underline">
                  {card.title}
                </h3>
                <p className="text-xs text-white/80 mt-1 line-clamp-1">{card.subtitle}</p>
              </div>
            </button>
          );
        })}
      </div>

      {/* Two Column Section: Recent Cases & Local Facilities Map */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Reports Tracking */}
        <div className="bg-white rounded-3xl p-6 border border-gray-100 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-gray-900 text-lg flex items-center gap-2">
              <Clock className="text-blue-600" size={20} />
              <span>{language === "mr" ? "माझे अलीकडील अहवाल" : "My Reported Cases"}</span>
            </h3>
            <button
              onClick={() => navigate("/reporting")}
              className="text-xs text-blue-600 font-bold hover:underline flex items-center gap-1"
            >
              <span>{language === "mr" ? "सर्व पहा" : "View All"}</span>
              <ArrowRight size={14} />
            </button>
          </div>

          <div className="space-y-3">
            {recentReports.length === 0 ? (
              <div className="text-center py-8 text-gray-400">
                <ShieldCheck size={40} className="mx-auto text-emerald-500 mb-2" />
                <p className="text-sm font-semibold text-gray-700">
                  {language === "mr" ? "कोणतीही सक्रिय रोग तक्रार नाही" : "No active disease reports recorded."}
                </p>
                <p className="text-xs text-gray-400 mt-1">
                  {language === "mr" ? "सर्व जनावरे निरोगी आहेत." : "All livestock currently marked healthy."}
                </p>
              </div>
            ) : (
              recentReports.map((r) => (
                <div
                  key={r.id}
                  className="p-4 rounded-2xl bg-gray-50 border border-gray-200/60 flex items-center justify-between hover:bg-blue-50/40 transition-colors"
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-gray-900 text-sm">{r.species}</span>
                      <span className="text-xs text-gray-500 font-mono">({r.reportNumber || r.id})</span>
                    </div>
                    <p className="text-xs text-gray-600 mt-0.5">
                      {r.disease || "Suspected Signs"} • {r.village}, {r.district}
                    </p>
                    <span className="inline-block mt-1 px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800">
                      Triage: {r.triageRiskLevel || "MODERATE"}
                    </span>
                  </div>

                  <span className="px-3 py-1 rounded-full text-xs font-bold bg-blue-100 text-blue-800">
                    {r.status}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Nearby Facilities & GIS Map */}
        <div className="bg-white rounded-3xl p-6 border border-gray-100 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-gray-900 text-lg flex items-center gap-2">
              <MapPin className="text-red-500" size={20} />
              <span>{t("farmer.nearbyHelp")}</span>
            </h3>
            <span className="text-xs font-semibold text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-full">
              MVU Active (1962)
            </span>
          </div>

          <PashuMap
            height="260px"
            center={[18.8288, 74.3789]}
            zoom={10}
            points={[
              { id: "FAC-1", name: "Shirur Veterinary Polyclinic", lat: 18.8260, lng: 74.3750, type: "facility" },
              { id: "CL-1", name: "Shirur Containment Zone", lat: 18.8288, lng: 74.3789, type: "cluster", riskLevel: "High Risk" }
            ]}
          />
        </div>
      </div>
    </div>
  );
}
