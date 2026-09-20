import { Link } from "react-router-dom";
import { 
  Shield, Stethoscope, TestTube2, Building2, 
  ArrowRight, UserPlus
} from "lucide-react";

export default function SignupPortal() {
  const roles = [
    {
      id: "farmer",
      title: "Farmer / Livestock Keeper",
      marathi: "शेतकरी व पशुपालक",
      badge: "🌾 FREE ENROLLMENT",
      description: "Register your herd, report sick livestock, access 24x7 1962 emergency mobile veterinary units, and view vaccination cards.",
      path: "/signup/farmer",
      loginPath: "/login/farmer",
      accent: "from-emerald-700 to-teal-800",
      btnColor: "bg-emerald-600 hover:bg-emerald-700",
      icon: Shield
    },
    {
      id: "veterinary",
      title: "Veterinary Officer",
      marathi: "पशुवैद्यकीय अधिकारी",
      badge: "👨‍⚕️ MSVC VERIFIED",
      description: "Enroll as an accredited veterinary officer for clinical field triage, telemedicine dispatch, e-prescriptions, and sample collection.",
      path: "/signup/veterinary",
      loginPath: "/login/veterinary",
      accent: "from-blue-700 to-indigo-800",
      btnColor: "bg-blue-600 hover:bg-blue-700",
      icon: Stethoscope
    },
    {
      id: "laboratory",
      title: "Diagnostic Laboratory",
      marathi: "रोग निदान प्रयोगशाळा",
      badge: "🧪 NABL ACCREDITED",
      description: "Register animal disease investigation section (DIS/RDDL), manage incoming sample barcodes, test batches, and sign off lab results.",
      path: "/signup/laboratory",
      loginPath: "/login/laboratory",
      accent: "from-purple-700 to-indigo-900",
      btnColor: "bg-purple-600 hover:bg-purple-700",
      icon: TestTube2
    },
    {
      id: "government",
      title: "Government Official / Admin",
      marathi: "शासकीय सनियंत्रण अधिकारी",
      badge: "🏛️ SURVEILLANCE & ADMIN",
      description: "Access state-wide epidemiological GIS risk maps, configure outbreak quarantine rings, issue district alerts, and system administration.",
      path: "/signup/government",
      loginPath: "/login/government",
      accent: "from-amber-700 to-red-900",
      btnColor: "bg-amber-600 hover:bg-amber-700",
      icon: Building2
    }
  ];

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-900 via-slate-800 to-slate-950 text-white py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-5xl mx-auto text-center mb-10">
        <div className="w-14 h-14 bg-gradient-to-tr from-blue-600 to-indigo-700 rounded-2xl mx-auto flex items-center justify-center text-white shadow-xl mb-3">
          <UserPlus size={30} />
        </div>
        <span className="px-3 py-1 bg-blue-500/20 text-blue-300 border border-blue-500/30 text-xs font-bold rounded-full uppercase tracking-wider">
          Account Registration Hub • नवीन नोंदणी
        </span>
        <h1 className="text-3xl sm:text-4xl font-extrabold text-white mt-3">
          Select Your Operational Role
        </h1>
        <p className="mt-2 text-sm text-slate-300 max-w-xl mx-auto">
          Choose the appropriate registration portal to enroll in Maharashtra's livestock disease surveillance and response network.
        </p>
      </div>

      <div className="max-w-5xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-6 mb-12">
        {roles.map((r) => {
          const Icon = r.icon;
          return (
            <div
              key={r.id}
              className="bg-slate-800/80 backdrop-blur-md rounded-2xl border border-slate-700 p-6 flex flex-col justify-between hover:border-slate-500 transition-all shadow-xl"
            >
              <div>
                <div className="flex items-center justify-between gap-3 mb-4">
                  <div className={`p-3 rounded-xl bg-gradient-to-br ${r.accent} text-white shadow-md`}>
                    <Icon size={24} />
                  </div>
                  <span className="px-3 py-1 rounded-full text-[11px] font-black tracking-wider bg-slate-700 text-slate-200 border border-slate-600">
                    {r.badge}
                  </span>
                </div>

                <h2 className="text-xl font-bold text-white">{r.title}</h2>
                <p className="text-xs text-emerald-400 font-medium mt-0.5">{r.marathi}</p>
                <p className="text-xs text-slate-300 mt-2.5 leading-relaxed">
                  {r.description}
                </p>
              </div>

              <div className="mt-6 pt-4 border-t border-slate-700/80 flex items-center justify-between gap-3">
                <Link
                  to={r.path}
                  className={`py-2.5 px-4 rounded-xl text-xs font-bold text-white ${r.btnColor} shadow-md flex items-center gap-1.5 transition-transform active:scale-95`}
                >
                  <span>Register {r.id === "farmer" ? "Farmer" : r.id === "veterinary" ? "Vet" : r.id === "laboratory" ? "Lab" : "Official"}</span>
                  <ArrowRight size={14} />
                </Link>

                <Link
                  to={r.loginPath}
                  className="text-xs text-slate-400 hover:text-white underline font-medium"
                >
                  Already registered? Sign In
                </Link>
              </div>
            </div>
          );
        })}
      </div>

      <div className="max-w-md mx-auto text-center">
        <Link
          to="/login"
          className="text-xs text-slate-400 hover:text-slate-200 underline font-medium"
        >
          ← Return to Login Hub
        </Link>
      </div>
    </div>
  );
}
