import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { ArrowRight, AlertCircle, UserPlus } from "lucide-react";
import { useAuth } from "../../context/AuthContext";

export default function FarmerSignup() {
  const navigate = useNavigate();
  const { signup } = useAuth();

  const [fullName, setFullName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [district, setDistrict] = useState("Pune");
  const [taluka, setTaluka] = useState("Shirur");
  const [village, setVillage] = useState("Walwur");
  const [password, setPassword] = useState("");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!fullName.trim() || !phone.trim() || !village.trim() || !password) {
      setErrorMsg("Please fill in all mandatory fields (Name, Phone, Village, Password).");
      return;
    }

    setLoading(true);
    setErrorMsg(null);

    const payload = {
      full_name: fullName.trim(),
      phone: phone.trim(),
      email: email.trim() || undefined,
      district,
      taluka,
      village: village.trim(),
      password
    };

    const res = await signup("farmer", payload);
    setLoading(false);

    if (res.success) {
      navigate("/farmer");
    } else {
      setErrorMsg(res.error || "Farmer registration failed. Please verify your details.");
    }
  };

  const handlePreFillSample = () => {
    setFullName("Tukaram Baburao Shinde");
    setPhone("9823154890");
    setEmail("tukaram.shinde@pashushield.gov.in");
    setDistrict("Pune");
    setTaluka("Haveli");
    setVillage("Manjari");
    setErrorMsg(null);
  };

  return (
    <div className="min-h-screen bg-slate-900 flex flex-col justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <div className="w-14 h-14 bg-gradient-to-tr from-emerald-600 to-teal-700 rounded-2xl mx-auto flex items-center justify-center text-white shadow-xl mb-3">
          <UserPlus size={30} />
        </div>
        <span className="px-3 py-1 bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-xs font-bold rounded-full uppercase tracking-wider">
          🌾 Farmer Registration • शेतकरी नोंदणी
        </span>
        <h2 className="mt-3 text-2xl sm:text-3xl font-extrabold text-white">
          Create Farmer Account
        </h2>
        <p className="mt-1 text-xs text-slate-300">
          पशुपालक खाते तयार करा व २४x७ मोफत पशुवैद्यकीय मदत मिळवा
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-lg">
        <div className="bg-slate-800 py-8 px-6 sm:px-8 shadow-2xl rounded-3xl border border-slate-700 space-y-6">
          {errorMsg && (
            <div className="p-3 bg-red-950/70 border border-red-700/80 rounded-xl text-xs text-red-200 flex items-center gap-2">
              <AlertCircle size={16} className="text-red-400 shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          <div className="flex justify-between items-center bg-slate-900/80 p-3 rounded-xl border border-slate-700 text-xs">
            <span className="text-slate-300">Quick Testing Assistance:</span>
            <button
              type="button"
              onClick={handlePreFillSample}
              className="text-emerald-400 hover:text-emerald-300 font-bold underline"
            >
              Fill Sample Farmer Info
            </button>
          </div>

          <form onSubmit={handleRegister} className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-slate-200 uppercase tracking-wider mb-1">
                Full Name / संपूर्ण नाव *
              </label>
              <input
                type="text"
                required
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="e.g. Ramesh Tukaram Patil"
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-bold text-slate-200 uppercase tracking-wider mb-1">
                  Mobile Number / मोबाईल *
                </label>
                <input
                  type="tel"
                  required
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="10-digit Mobile"
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-200 uppercase tracking-wider mb-1">
                  Email (Optional) / ईमेल
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@example.com"
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>
            </div>

            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="block text-xs font-bold text-slate-200 uppercase tracking-wider mb-1">
                  District / जिल्हा *
                </label>
                <select
                  value={district}
                  onChange={(e) => setDistrict(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
                >
                  <option value="Pune">Pune</option>
                  <option value="Satara">Satara</option>
                  <option value="Ahmednagar">Ahmednagar</option>
                  <option value="Solapur">Solapur</option>
                  <option value="Kolhapur">Kolhapur</option>
                  <option value="Nashik">Nashik</option>
                  <option value="Sangli">Sangli</option>
                  <option value="Nagpur">Nagpur</option>
                  <option value="Aurangabad">Chh. Sambhajinagar</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-200 uppercase tracking-wider mb-1">
                  Taluka / तालुका
                </label>
                <input
                  type="text"
                  value={taluka}
                  onChange={(e) => setTaluka(e.target.value)}
                  placeholder="Taluka"
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-200 uppercase tracking-wider mb-1">
                  Village / गाव *
                </label>
                <input
                  type="text"
                  required
                  value={village}
                  onChange={(e) => setVillage(e.target.value)}
                  placeholder="Village"
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-200 uppercase tracking-wider mb-1">
                Create Password / पासवर्ड तयार करा *
              </label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="At least 6 characters"
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 px-4 rounded-xl text-sm font-bold bg-emerald-600 hover:bg-emerald-700 text-white shadow-lg flex items-center justify-center gap-2 transition-transform active:scale-95 disabled:opacity-60"
            >
              <span>{loading ? "Registering..." : "Complete Farmer Registration"}</span>
              <ArrowRight size={16} />
            </button>
          </form>

          <div className="pt-2 border-t border-slate-700 text-center text-xs text-slate-400">
            <span>Already registered? </span>
            <Link to="/login/farmer" className="text-emerald-400 hover:text-emerald-300 font-bold underline">
              Sign In to Farmer Portal
            </Link>
          </div>
        </div>

        <div className="mt-6 text-center text-xs text-slate-400">
          <Link to="/login" className="hover:text-slate-200 underline">
            ← Back to Unified Role Portals
          </Link>
        </div>
      </div>
    </div>
  );
}
