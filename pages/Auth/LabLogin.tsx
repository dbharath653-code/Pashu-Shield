import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { 
  TestTube2, ArrowRight, AlertCircle, 
  Sparkles, FlaskConical
} from "lucide-react";
import { useAuth } from "../../context/AuthContext";

export default function LabLogin() {
  const navigate = useNavigate();
  const { login, demoLogin } = useAuth();

  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleLabLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!identifier.trim() || !password) {
      setErrorMsg("Please enter your laboratory email or technician phone, and password.");
      return;
    }

    setLoading(true);
    setErrorMsg(null);

    const res = await login(identifier.trim(), password);
    setLoading(false);

    if (res.success) {
      navigate("/lab");
    } else {
      setErrorMsg(res.error || "Login failed. Please verify your laboratory credentials.");
    }
  };

  const handlePreFillDemo = () => {
    setIdentifier("lab@pashushield.gov.in");
    setPassword("Lab@123");
    setErrorMsg(null);
  };

  const handleInstantLabDemo = async () => {
    setLoading(true);
    await demoLogin("LAB_TECHNICIAN");
    setLoading(false);
    navigate("/lab");
  };

  return (
    <div className="min-h-screen bg-slate-900 flex flex-col justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <div className="w-14 h-14 bg-gradient-to-tr from-purple-600 to-indigo-800 rounded-2xl mx-auto flex items-center justify-center text-white shadow-xl mb-3">
          <TestTube2 size={32} />
        </div>
        <span className="px-3 py-1 bg-purple-500/20 text-purple-300 border border-purple-500/30 text-xs font-bold rounded-full uppercase tracking-wider">
          🧪 Laboratory Portal • रोग निदान प्रयोगशाळा
        </span>
        <h2 className="mt-3 text-2xl sm:text-3xl font-extrabold text-white">
          Diagnostic Lab Sign In
        </h2>
        <p className="mt-1 text-xs sm:text-sm text-slate-300">
          RT-PCR, ELISA Serology & Sample Barcode Verification System
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
          <div className="bg-purple-950/50 border border-purple-700/50 rounded-2xl p-3.5 text-xs text-purple-200 flex items-start justify-between gap-2">
            <div>
              <p className="font-bold flex items-center gap-1 text-purple-300">
                <FlaskConical size={13} />
                <span>Authorized Laboratory Credentials</span>
              </p>
              <p className="text-[11px] text-purple-300/90 mt-1 font-mono">
                Email/Mobile: <b>lab@pashushield.gov.in</b> (or 9823077777)
              </p>
              <p className="text-[11px] text-purple-300/90 font-mono">
                Password: <b>Lab@123</b>
              </p>
              <p className="text-[10px] text-purple-400 mt-1">
                Pooja Shinde (DIS Pune, ISO/IEC 17025 Accredited)
              </p>
            </div>
            <button
              onClick={handlePreFillDemo}
              className="text-[11px] font-bold bg-purple-700 hover:bg-purple-600 text-white px-2.5 py-1.5 rounded-lg shrink-0 transition-colors shadow-2xs"
            >
              Fill Details
            </button>
          </div>

          <form onSubmit={handleLabLogin} className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-slate-200 uppercase tracking-wider mb-1">
                Laboratory Email or Mobile
              </label>
              <input
                type="text"
                required
                value={identifier}
                onChange={(e) => setIdentifier(e.target.value)}
                placeholder="lab@pashushield.gov.in or 9823077777"
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-purple-500"
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
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 px-4 rounded-xl text-sm font-bold bg-purple-600 hover:bg-purple-700 text-white shadow-lg flex items-center justify-center gap-2 transition-transform active:scale-95 disabled:opacity-60"
            >
              <span>{loading ? "Authenticating..." : "Sign In to Laboratory System"}</span>
              <ArrowRight size={16} />
            </button>
          </form>

          {/* 1-Tap Instant Demo */}
          <div className="pt-2 border-t border-slate-700/80 space-y-3">
            <button
              onClick={handleInstantLabDemo}
              disabled={loading}
              className="w-full py-2.5 px-3 rounded-xl text-xs font-bold bg-slate-700 hover:bg-slate-600 text-slate-200 border border-slate-600 flex items-center justify-center gap-2 transition-colors"
            >
              <Sparkles size={14} className="text-amber-400" />
              <span>1-Tap Instant Demo Login (Pooja Shinde)</span>
            </button>

            <div className="flex items-center justify-between text-xs text-slate-400">
              <span>New Diagnostic Facility?</span>
              <Link to="/signup/laboratory" className="text-purple-400 hover:text-purple-300 font-bold underline">
                Register New Lab
              </Link>
            </div>
          </div>
        </div>

        <div className="mt-6 text-center text-xs text-slate-400">
          <Link to="/login" className="hover:text-slate-200 underline">
            ← Switch to Other Roles (Farmer, Vet, Govt)
          </Link>
        </div>
      </div>
    </div>
  );
}
