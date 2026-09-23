import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { ArrowRight, AlertCircle, ShieldCheck } from "lucide-react";
import { useAuth } from "../../context/AuthContext";

export default function GovernmentSignup() {
  const navigate = useNavigate();
  const { signup } = useAuth();

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [department, setDepartment] = useState("Department of Animal Husbandry, Govt. of Maharashtra");
  const [designation, setDesignation] = useState("Epidemiology & Surveillance Officer");
  const [jurisdiction, setJurisdiction] = useState("Maharashtra State");
  const [district, setDistrict] = useState("Pune");
  const [role, setRole] = useState("STATE_OFFICER");
  const [password, setPassword] = useState("");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!fullName.trim() || !email.trim() || !phone.trim() || !password) {
      setErrorMsg("Please fill in all mandatory fields (Name, Email, Phone, Password).");
      return;
    }

    setLoading(true);
    setErrorMsg(null);

    const payload = {
      full_name: fullName.trim(),
      email: email.trim(),
      phone: phone.trim(),
      department,
      designation,
      jurisdiction,
      district,
      role,
      password
    };

    const res = await signup("government", payload);
    setLoading(false);

    if (res.success) {
      navigate("/surveillance");
    } else {
      setErrorMsg(res.error || "Government registration failed. Please verify your official details.");
    }
  };

  const handlePreFillSample = () => {
    setFullName("Dr. Meenakshi S. Kulkarni");
    setEmail("dr.meenakshi.kulkarni@pashushield.gov.in");
    setPhone("9823091122");
    setDepartment("Commissionerate of Animal Husbandry, Maharashtra");
    setDesignation("Deputy Director (Zoonotic Disease Surveillance)");
    setJurisdiction("Maharashtra State");
    setDistrict("Pune");
    setRole("STATE_OFFICER");
    setErrorMsg(null);
  };

  return (
    <div className="min-h-screen bg-slate-900 flex flex-col justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <div className="w-14 h-14 bg-gradient-to-tr from-amber-600 via-orange-600 to-red-700 rounded-2xl mx-auto flex items-center justify-center text-white shadow-xl mb-3">
          <ShieldCheck size={30} />
        </div>
        <span className="px-3 py-1 bg-amber-500/20 text-amber-300 border border-amber-500/30 text-xs font-bold rounded-full uppercase tracking-wider">
          🏛️ Official Registration • शासकीय नोंदणी
        </span>
        <h2 className="mt-3 text-2xl sm:text-3xl font-extrabold text-white">
          Government Official Registration
        </h2>
        <p className="mt-1 text-xs text-slate-300">
          State Surveillance Coordination & Administrative Oversight
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-xl">
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
              className="text-amber-400 hover:text-amber-300 font-bold underline"
            >
              Fill Sample Official Info
            </button>
          </div>

          <form onSubmit={handleRegister} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-bold text-slate-200 uppercase tracking-wider mb-1">
                  Full Name & Designation *
                </label>
                <input
                  type="text"
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="e.g. Dr. Rajesh Joshi"
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-amber-500"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-200 uppercase tracking-wider mb-1">
                  Official Email *
                </label>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="officer@pashushield.gov.in"
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-amber-500"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-bold text-slate-200 uppercase tracking-wider mb-1">
                  Contact Phone *
                </label>
                <input
                  type="tel"
                  required
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="10-digit mobile"
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-amber-500"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-200 uppercase tracking-wider mb-1">
                  Administrative Level
                </label>
                <select
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-amber-500"
                >
                  <option value="STATE_OFFICER">State Surveillance Coordinator</option>
                  <option value="DISTRICT_OFFICER">District Officer (DAHO)</option>
                  <option value="SYSTEM_ADMIN">System Administrator</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-bold text-slate-200 uppercase tracking-wider mb-1">
                  Designation Title
                </label>
                <input
                  type="text"
                  value={designation}
                  onChange={(e) => setDesignation(e.target.value)}
                  placeholder="Surveillance Officer / Joint Director"
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-amber-500"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-200 uppercase tracking-wider mb-1">
                  Headquarter District
                </label>
                <select
                  value={district}
                  onChange={(e) => setDistrict(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-amber-500"
                >
                  <option value="Pune">Pune</option>
                  <option value="Satara">Satara</option>
                  <option value="Ahmednagar">Ahmednagar</option>
                  <option value="Nashik">Nashik</option>
                  <option value="Nagpur">Nagpur</option>
                  <option value="Kolhapur">Kolhapur</option>
                  <option value="Aurangabad">Chh. Sambhajinagar</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-200 uppercase tracking-wider mb-1">
                Password *
              </label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="At least 6 characters"
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-amber-500"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 px-4 rounded-xl text-sm font-bold bg-amber-600 hover:bg-amber-700 text-white shadow-lg flex items-center justify-center gap-2 transition-transform active:scale-95 disabled:opacity-60"
            >
              <span>{loading ? "Registering..." : "Complete Official Registration"}</span>
              <ArrowRight size={16} />
            </button>
          </form>

          <div className="pt-2 border-t border-slate-700 text-center text-xs text-slate-400">
            <span>Already registered? </span>
            <Link to="/login/government" className="text-amber-400 hover:text-amber-300 font-bold underline">
              Sign In to Government Portal
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
