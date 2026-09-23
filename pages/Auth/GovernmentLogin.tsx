import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { 
  Building2, ArrowRight, AlertCircle, 
  Sparkles, ShieldCheck
} from "lucide-react";
import { useAuth } from "../../context/AuthContext";

export default function GovernmentLogin() {
  const navigate = useNavigate();
  const { login, demoLogin } = useAuth();

  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleGovtLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!identifier.trim() || !password) {
      setErrorMsg("Please enter your official government email or phone, and password.");
      return;
    }

    setLoading(true);
    setErrorMsg(null);

    const res = await login(identifier.trim(), password);
    setLoading(false);

    if (res.success) {
      navigate("/surveillance");
    } else {
      setErrorMsg(res.error || "Login failed. Please verify your government official credentials.");
    }
  };

  const handlePreFillStateOfficer = () => {
    setIdentifier("state.demo@pashushield.local");
    setErrorMsg(null);
  };

  const handlePreFillAdmin = () => {
    setIdentifier("admin.demo@pashushield.local");
    setErrorMsg(null);
  };

  const handleInstantStateDemo = async () => {
    setLoading(true);
    await demoLogin("STATE_OFFICER");
    setLoading(false);
    navigate("/surveillance");
  };

  return (
    <div className="min-h-screen bg-slate-900 flex flex-col justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <div className="w-14 h-14 bg-gradient-to-tr from-amber-600 via-orange-600 to-red-700 rounded-2xl mx-auto flex items-center justify-center text-white shadow-xl mb-3">
          <Building2 size={32} />
        </div>
        <span className="px-3 py-1 bg-amber-500/20 text-amber-300 border border-amber-500/30 text-xs font-bold rounded-full uppercase tracking-wider">
          🏛️ Government Surveillance & Admin Authority
        </span>
        <h2 className="mt-3 text-2xl sm:text-3xl font-extrabold text-white">
          Government Official Sign In
        </h2>
        <p className="mt-1 text-xs sm:text-sm text-slate-300">
          State Surveillance Coordination, Hotspot Containment & System Administration
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-slate-800 py-8 px-6 sm:px-8 shadow-2xl rounded-3xl border border-slate-700 space-y-6">
          {errorMsg && (
            <div className="p-3 bg-red-950/70 border border-red-700/80 rounded-xl text-xs text-red-200 flex items-center gap-2">
              <AlertCircle size={16} className="text-red-400 shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          {/* Authorized Demo Credentials Notice Card */}
          <div className="bg-amber-950/50 border border-amber-700/50 rounded-2xl p-4 text-xs text-amber-200 space-y-2.5">
            <div className="flex items-center justify-between">
              <p className="font-bold flex items-center gap-1.5 text-amber-300">
                <ShieldCheck size={15} />
                <span>Government Admin & Surveillance Credentials</span>
              </p>
            </div>

            <div className="bg-slate-900/90 p-2.5 rounded-xl border border-slate-700 space-y-1">
              <div className="flex items-center justify-between">
                <span className="font-bold text-slate-200">State Surveillance Officer (Admin)</span>
                <button
                  type="button"
                  onClick={handlePreFillStateOfficer}
                  className="text-[10px] font-bold bg-amber-600 hover:bg-amber-500 text-white px-2 py-0.5 rounded shadow-2xs"
                >
                  Fill State
                </button>
              </div>
              <p className="text-[11px] font-mono text-amber-300">
                Email: <b>state.demo@pashushield.local</b> | Password: <i>demo password configured by the server administrator (DEMO_USER_PASSWORD)</i>
              </p>
              <p className="text-[10px] text-slate-400">
                Dr. V. K. Chavan (Joint Director, Animal Husbandry)
              </p>
            </div>

            <div className="bg-slate-900/90 p-2.5 rounded-xl border border-slate-700 space-y-1">
              <div className="flex items-center justify-between">
                <span className="font-bold text-slate-200">System Administrator (IT Directorate)</span>
                <button
                  type="button"
                  onClick={handlePreFillAdmin}
                  className="text-[10px] font-bold bg-slate-700 hover:bg-slate-600 text-white px-2 py-0.5 rounded shadow-2xs"
                >
                  Fill Admin
                </button>
              </div>
              <p className="text-[11px] font-mono text-amber-300">
                Email: <b>admin.demo@pashushield.local</b> | Password: <i>demo password configured by the server administrator (DEMO_USER_PASSWORD)</i>
              </p>
            </div>
          </div>

          <form onSubmit={handleGovtLogin} className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-slate-200 uppercase tracking-wider mb-1">
                Official Government Email or Phone
              </label>
              <input
                type="text"
                required
                value={identifier}
                onChange={(e) => setIdentifier(e.target.value)}
                placeholder="state.demo@pashushield.local or admin.demo@pashushield.local"
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-amber-500"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-200 uppercase tracking-wider mb-1">
                Password
              </label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-amber-500"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 px-4 rounded-xl text-sm font-bold bg-amber-600 hover:bg-amber-700 text-white shadow-lg flex items-center justify-center gap-2 transition-transform active:scale-95 disabled:opacity-60"
            >
              <span>{loading ? "Authenticating..." : "Sign In to Government Surveillance"}</span>
              <ArrowRight size={16} />
            </button>
          </form>

          {/* 1-Tap Instant Demo */}
          <div className="pt-2 border-t border-slate-700/80 space-y-3">
            <button
              onClick={handleInstantStateDemo}
              disabled={loading}
              className="w-full py-2.5 px-3 rounded-xl text-xs font-bold bg-slate-700 hover:bg-slate-600 text-slate-200 border border-slate-600 flex items-center justify-center gap-2 transition-colors"
            >
              <Sparkles size={14} className="text-amber-400" />
              <span>1-Tap Demo: State Surveillance Coordinator (Dr. Chavan)</span>
            </button>

            <div className="flex items-center justify-between text-xs text-slate-400">
              <span>New Surveillance Officer?</span>
              <Link to="/signup/government" className="text-amber-400 hover:text-amber-300 font-bold underline">
                Register Official Account
              </Link>
            </div>
          </div>
        </div>

        <div className="mt-6 text-center text-xs text-slate-400">
          <Link to="/login" className="hover:text-slate-200 underline">
            ← Switch to Other Roles (Farmer, Vet, Lab)
          </Link>
        </div>
      </div>
    </div>
  );
}
