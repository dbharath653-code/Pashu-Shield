import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { 
  Shield, Stethoscope, TestTube2, Building2, 
  ArrowRight, Key, Copy, Check, UserCheck
} from "lucide-react";
import { useAuth, type RoleType } from "../../context/AuthContext";

export default function LoginPortal() {
  const navigate = useNavigate();
  const { demoLogin } = useAuth();
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const copyToClipboard = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const handleInstantDemoLogin = async (targetRole: RoleType, destination: string) => {
    await demoLogin(targetRole);
    navigate(destination);
  };

  const portals = [
    {
      id: "farmer",
      title: "Farmer / Livestock Keeper",
      marathiTitle: "शेतकरी / पशुपालक पोर्टल",
      roleBadge: "🌾 FARMER",
      description: "Voice-guided syndromic reporting, 1962 emergency dispatch requests, herd health registry & vaccination schedules.",
      loginPath: "/login/farmer",
      signupPath: "/signup/farmer",
      dashboardPath: "/farmer",
      role: "FARMER" as RoleType,
      credentials: {
        identifier: "farmer@pashushield.gov.in (or 9823012345)",
        password: "Farmer@123",
        name: "Ramesh Tukaram Patil (Walwur, Pune)"
      },
      accent: "from-emerald-700 to-teal-800",
      btnColor: "bg-emerald-600 hover:bg-emerald-700",
      icon: Shield
    },
    {
      id: "veterinary",
      title: "Veterinary Officer (MVU / Clinic)",
      marathiTitle: "पशुवैद्यकीय अधिकारी पोर्टल",
      roleBadge: "👨‍⚕️ VETERINARIAN",
      description: "Field emergency case queue, GPS routing, clinical examination notes, e-prescriptions, and lab test sample collection.",
      loginPath: "/login/veterinary",
      signupPath: "/signup/veterinary",
      dashboardPath: "/vet-response",
      role: "VETERINARIAN" as RoleType,
      credentials: {
        identifier: "vet@pashushield.gov.in (or 9823054321)",
        password: "Vet@123",
        name: "Dr. Sunita Deshmukh (Shirur Polyclinic)"
      },
      accent: "from-blue-700 to-indigo-800",
      btnColor: "bg-blue-600 hover:bg-blue-700",
      icon: Stethoscope
    },
    {
      id: "laboratory",
      title: "Diagnostic Laboratory Officer",
      marathiTitle: "रोग निदान प्रयोगशाळा पोर्टल",
      roleBadge: "🧪 LAB DIAGNOSTICS",
      description: "Sample QR accessioning, RT-PCR / ELISA / Serology batch workflows, pathogen confirmation, and test verification.",
      loginPath: "/login/laboratory",
      signupPath: "/signup/laboratory",
      dashboardPath: "/lab",
      role: "LAB_TECHNICIAN" as RoleType,
      credentials: {
        identifier: "lab@pashushield.gov.in (or 9823077777)",
        password: "Lab@123",
        name: "Pooja Shinde (DIS Pune, NABL Accredited)"
      },
      accent: "from-purple-700 to-indigo-900",
      btnColor: "bg-purple-600 hover:bg-purple-700",
      icon: TestTube2
    },
    {
      id: "government",
      title: "Government Official / Admin",
      marathiTitle: "शासकीय सनियंत्रण व प्रशासक पोर्टल",
      roleBadge: "🏛️ ADMIN & SURVEILLANCE",
      description: "State-wide GIS disease surveillance, outbreak containment zones, NADRES risk indexes, and system administration.",
      loginPath: "/login/government",
      signupPath: "/signup/government",
      dashboardPath: "/surveillance",
      role: "STATE_OFFICER" as RoleType,
      credentials: {
        identifier: "state@pashushield.gov.in (or admin@pashushield.gov.in)",
        password: "Govt@123 (or Admin@123)",
        name: "Dr. V. K. Chavan (State Surveillance Coordinator)"
      },
      accent: "from-amber-700 to-red-900",
      btnColor: "bg-amber-600 hover:bg-amber-700",
      icon: Building2
    }
  ];

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-900 via-slate-800 to-slate-950 text-white py-12 px-4 sm:px-6 lg:px-8">
      {/* Top Header */}
      <div className="max-w-6xl mx-auto text-center mb-10">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-500/10 border border-blue-400/30 text-blue-300 text-xs font-bold mb-4">
          <Shield size={14} />
          <span>GOVERNMENT OF MAHARASHTRA • ANIMAL HUSBANDRY DEPARTMENT</span>
        </div>
        <h1 className="text-3xl sm:text-5xl font-black tracking-tight text-white mb-3">
          Pashu-Shield Unified Portals
        </h1>
        <p className="text-sm sm:text-base text-slate-300 max-w-2xl mx-auto">
          Dedicated, role-specific authentication portals for Farmers, Veterinarians, Diagnostic Laboratories, and Government Surveillance Administrators.
        </p>
      </div>

      {/* Grid of 4 Dedicated Portals */}
      <div className="max-w-6xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-6 mb-12">
        {portals.map((portal) => {
          const Icon = portal.icon;
          return (
            <div
              key={portal.id}
              className="bg-slate-800/80 backdrop-blur-md rounded-2xl border border-slate-700 p-6 flex flex-col justify-between hover:border-slate-500 transition-all shadow-xl group"
            >
              <div>
                <div className="flex items-center justify-between gap-3 mb-4">
                  <div className={`p-3 rounded-xl bg-gradient-to-br ${portal.accent} text-white shadow-md`}>
                    <Icon size={24} />
                  </div>
                  <span className="px-3 py-1 rounded-full text-[11px] font-black tracking-wider bg-slate-700 text-slate-200 border border-slate-600">
                    {portal.roleBadge}
                  </span>
                </div>

                <h2 className="text-xl font-bold text-white group-hover:text-blue-400 transition-colors">
                  {portal.title}
                </h2>
                <p className="text-xs text-emerald-400 font-medium mt-0.5">{portal.marathiTitle}</p>
                <p className="text-xs text-slate-300 mt-2.5 leading-relaxed">
                  {portal.description}
                </p>

                {/* Pre-configured Demo Credentials Box */}
                <div className="mt-5 p-3.5 bg-slate-900/90 rounded-xl border border-slate-700/80 text-xs space-y-1.5">
                  <div className="flex items-center justify-between text-slate-400 font-semibold text-[11px]">
                    <span className="flex items-center gap-1 text-slate-300">
                      <Key size={12} className="text-amber-400" />
                      <span>Authorized Credentials</span>
                    </span>
                    <span className="text-[10px] text-slate-500">{portal.credentials.name}</span>
                  </div>

                  <div className="flex items-center justify-between bg-slate-950 px-2.5 py-1.5 rounded-lg border border-slate-800 font-mono text-[11px] text-slate-200">
                    <span className="truncate pr-2">{portal.credentials.identifier}</span>
                    <button
                      onClick={() => copyToClipboard(portal.credentials.identifier.split(" ")[0], `${portal.id}-id`)}
                      className="text-slate-400 hover:text-white shrink-0"
                      title="Copy identifier"
                    >
                      {copiedKey === `${portal.id}-id` ? <Check size={13} className="text-emerald-400" /> : <Copy size={13} />}
                    </button>
                  </div>

                  <div className="flex items-center justify-between bg-slate-950 px-2.5 py-1.5 rounded-lg border border-slate-800 font-mono text-[11px] text-slate-200">
                    <span>Password: <b>{portal.credentials.password}</b></span>
                    <button
                      onClick={() => copyToClipboard(portal.credentials.password.split(" ")[0], `${portal.id}-pwd`)}
                      className="text-slate-400 hover:text-white shrink-0"
                      title="Copy password"
                    >
                      {copiedKey === `${portal.id}-pwd` ? <Check size={13} className="text-emerald-400" /> : <Copy size={13} />}
                    </button>
                  </div>
                </div>
              </div>

              {/* Action Buttons: Dedicated Login, Sign Up, 1-Click Demo */}
              <div className="mt-6 pt-4 border-t border-slate-700/80 space-y-2.5">
                <div className="grid grid-cols-2 gap-2">
                  <Link
                    to={portal.loginPath}
                    className={`py-2.5 px-3 rounded-xl text-xs font-bold text-center text-white ${portal.btnColor} shadow-md flex items-center justify-center gap-1.5 transition-transform active:scale-95`}
                  >
                    <span>Sign In</span>
                    <ArrowRight size={14} />
                  </Link>

                  <Link
                    to={portal.signupPath}
                    className="py-2.5 px-3 rounded-xl text-xs font-bold text-center bg-slate-700 hover:bg-slate-600 text-slate-200 transition-colors border border-slate-600"
                  >
                    <span>Sign Up</span>
                  </Link>
                </div>

                <button
                  onClick={() => handleInstantDemoLogin(portal.role, portal.dashboardPath)}
                  className="w-full py-2 px-3 rounded-xl text-xs font-semibold bg-blue-950/60 hover:bg-blue-900/60 text-blue-300 border border-blue-800/70 flex items-center justify-center gap-1.5 transition-colors"
                >
                  <UserCheck size={13} />
                  <span>1-Tap Instant Demo Login</span>
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Footer Return Link */}
      <div className="max-w-md mx-auto text-center">
        <Link
          to="/"
          className="text-xs text-slate-400 hover:text-slate-200 underline font-medium"
        >
          ← Return to Public Dashboard & Overview
        </Link>
      </div>
    </div>
  );
}
