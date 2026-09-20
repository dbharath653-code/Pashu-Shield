import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { 
  Shield, PhoneCall, ArrowRight, 
  AlertCircle, Sparkles, CheckCircle2
} from "lucide-react";
import { useAuth } from "../../context/AuthContext";

export default function FarmerLogin() {
  const navigate = useNavigate();
  const { login, demoLogin } = useAuth();

  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleFarmerLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!identifier.trim() || !password) {
      setErrorMsg("Please enter your registered mobile number or email, and password.");
      return;
    }

    setLoading(true);
    setErrorMsg(null);

    const res = await login(identifier.trim(), password);
    setLoading(false);

    if (res.success) {
      navigate("/farmer");
    } else {
      setErrorMsg(res.error || "Login failed. Please check your mobile number or password.");
    }
  };

  const handlePreFillDemo = () => {
    setIdentifier("farmer@pashushield.gov.in");
    setPassword("Farmer@123");
    setErrorMsg(null);
  };

  const handleInstantFarmerDemo = async () => {
    setLoading(true);
    await demoLogin("FARMER");
    setLoading(false);
    navigate("/farmer");
  };

  return (
    <div className="min-h-screen bg-slate-900 flex flex-col justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <div className="w-14 h-14 bg-gradient-to-tr from-emerald-600 to-teal-700 rounded-2xl mx-auto flex items-center justify-center text-white shadow-xl mb-3">
          <Shield size={32} />
        </div>
        <span className="px-3 py-1 bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-xs font-bold rounded-full uppercase tracking-wider">
          🌾 Farmer Portal • शेतकरी पोर्टल
        </span>
        <h2 className="mt-3 text-2xl sm:text-3xl font-extrabold text-white">
          Farmer Sign In
        </h2>
        <p className="mt-1 text-xs sm:text-sm text-slate-300">
          पशुपालक लॉगिन: जनावरांचे आजार, उपचार व १९६२ आपत्कालीन मदत
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
          <div className="bg-emerald-950/40 border border-emerald-700/40 rounded-2xl p-3.5 text-xs text-emerald-200 flex items-start justify-between gap-2">
            <div>
              <p className="font-bold flex items-center gap-1 text-emerald-300">
                <CheckCircle2 size={13} />
                <span>Authorized Farmer Credentials</span>
              </p>
              <p className="text-[11px] text-emerald-400/90 mt-1 font-mono">
                Mobile/Email: <b>farmer@pashushield.gov.in</b> (or 9823012345)
              </p>
              <p className="text-[11px] text-emerald-400/90 font-mono">
                Password: <b>Farmer@123</b>
              </p>
            </div>
            <button
              onClick={handlePreFillDemo}
              className="text-[11px] font-bold bg-emerald-700 hover:bg-emerald-600 text-white px-2.5 py-1.5 rounded-lg shrink-0 transition-colors shadow-2xs"
            >
              Fill Details
            </button>
          </div>

          <form onSubmit={handleFarmerLogin} className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-slate-200 uppercase tracking-wider mb-1">
                Mobile Number or Email / मोबाईल किंवा ईमेल
              </label>
              <input
                type="text"
                required
                value={identifier}
                onChange={(e) => setIdentifier(e.target.value)}
                placeholder="e.g. 9823012345 or farmer@pashushield.gov.in"
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-200 uppercase tracking-wider mb-1">
                Password / पासवर्ड
              </label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 px-4 rounded-xl text-sm font-bold bg-emerald-600 hover:bg-emerald-700 text-white shadow-lg flex items-center justify-center gap-2 transition-transform active:scale-95 disabled:opacity-60"
            >
              <span>{loading ? "Signing In..." : "Sign In to Farmer Portal"}</span>
              <ArrowRight size={16} />
            </button>
          </form>

          {/* 1-Tap Instant Demo */}
          <div className="pt-2 border-t border-slate-700/80 space-y-3">
            <button
              onClick={handleInstantFarmerDemo}
              disabled={loading}
              className="w-full py-2.5 px-3 rounded-xl text-xs font-bold bg-slate-700 hover:bg-slate-600 text-slate-200 border border-slate-600 flex items-center justify-center gap-2 transition-colors"
            >
              <Sparkles size={14} className="text-amber-400" />
              <span>1-Tap Instant Demo Login (Ramesh Patil)</span>
            </button>

            <div className="flex items-center justify-between text-xs text-slate-400">
              <span>New livestock keeper?</span>
              <Link to="/signup/farmer" className="text-emerald-400 hover:text-emerald-300 font-bold underline">
                Register New Farmer
              </Link>
            </div>
          </div>
        </div>

        <div className="mt-6 flex items-center justify-between text-xs text-slate-400">
          <Link to="/login" className="hover:text-slate-200 underline">
            ← Switch to Other Roles (Vet, Lab, Govt)
          </Link>
          <a href="tel:1962" className="text-red-400 hover:text-red-300 font-bold flex items-center gap-1">
            <PhoneCall size={12} />
            <span>Emergency 1962</span>
          </a>
        </div>
      </div>
    </div>
  );
}
