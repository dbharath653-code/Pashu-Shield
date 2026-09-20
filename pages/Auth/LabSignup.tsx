import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { ArrowRight, AlertCircle, FlaskConical } from "lucide-react";
import { useAuth } from "../../context/AuthContext";

export default function LabSignup() {
  const navigate = useNavigate();
  const { signup } = useAuth();

  const [labName, setLabName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [accreditation, setAccreditation] = useState("NABL ISO/IEC 17025:2017");
  const [district, setDistrict] = useState("Pune");
  const [address, setAddress] = useState("");
  const [password, setPassword] = useState("");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!labName.trim() || !email.trim() || !phone.trim() || !password) {
      setErrorMsg("Please fill in all mandatory fields (Lab Name, Email, Phone, Password).");
      return;
    }

    setLoading(true);
    setErrorMsg(null);

    const payload = {
      lab_name: labName.trim(),
      email: email.trim(),
      phone: phone.trim(),
      accreditation,
      district,
      address: address.trim(),
      services: ["RT-PCR", "ELISA Serology", "Culture Sensitivity", "Direct Microscopy"],
      password
    };

    const res = await signup("lab", payload);
    setLoading(false);

    if (res.success) {
      navigate("/lab");
    } else {
      setErrorMsg(res.error || "Laboratory registration failed. Please verify your details.");
    }
  };

  const handlePreFillSample = () => {
    setLabName("Western Maharashtra Regional Disease Diagnostic Laboratory (RDDL)");
    setEmail("rddl.western@pashushield.gov.in");
    setPhone("9823071234");
    setAccreditation("NABL ISO/IEC 17025:2017 & ICAR Recognized");
    setDistrict("Pune");
    setAddress("Ganeshkhind Road, Aundh, Pune 411007");
    setPassword("Lab@123");
    setErrorMsg(null);
  };

  return (
    <div className="min-h-screen bg-slate-900 flex flex-col justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <div className="w-14 h-14 bg-gradient-to-tr from-purple-600 to-indigo-800 rounded-2xl mx-auto flex items-center justify-center text-white shadow-xl mb-3">
          <FlaskConical size={30} />
        </div>
        <span className="px-3 py-1 bg-purple-500/20 text-purple-300 border border-purple-500/30 text-xs font-bold rounded-full uppercase tracking-wider">
          🧪 Lab Registration • प्रयोगशाळा नोंदणी
        </span>
        <h2 className="mt-3 text-2xl sm:text-3xl font-extrabold text-white">
          Laboratory Registration
        </h2>
        <p className="mt-1 text-xs text-slate-300">
          Diagnostic Facility & Testing Center Accreditation System
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
              className="text-purple-400 hover:text-purple-300 font-bold underline"
            >
              Fill Sample Laboratory Info
            </button>
          </div>

          <form onSubmit={handleRegister} className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-slate-200 uppercase tracking-wider mb-1">
                Laboratory Name *
              </label>
              <input
                type="text"
                required
                value={labName}
                onChange={(e) => setLabName(e.target.value)}
                placeholder="e.g. State Disease Investigation Section (DIS)"
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-bold text-slate-200 uppercase tracking-wider mb-1">
                  Official Email *
                </label>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="lab@pashushield.gov.in"
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-200 uppercase tracking-wider mb-1">
                  Contact Phone *
                </label>
                <input
                  type="tel"
                  required
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="Official Contact"
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-bold text-slate-200 uppercase tracking-wider mb-1">
                  Accreditation / Standard
                </label>
                <input
                  type="text"
                  value={accreditation}
                  onChange={(e) => setAccreditation(e.target.value)}
                  placeholder="NABL ISO/IEC 17025"
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-200 uppercase tracking-wider mb-1">
                  District Location *
                </label>
                <select
                  value={district}
                  onChange={(e) => setDistrict(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
                >
                  <option value="Pune">Pune</option>
                  <option value="Satara">Satara</option>
                  <option value="Ahmednagar">Ahmednagar</option>
                  <option value="Kolhapur">Kolhapur</option>
                  <option value="Nashik">Nashik</option>
                  <option value="Nagpur">Nagpur</option>
                  <option value="Aurangabad">Chh. Sambhajinagar</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-200 uppercase tracking-wider mb-1">
                Facility Address
              </label>
              <input
                type="text"
                value={address}
                onChange={(e) => setAddress(e.target.value)}
                placeholder="Full address / building details"
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
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
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 px-4 rounded-xl text-sm font-bold bg-purple-600 hover:bg-purple-700 text-white shadow-lg flex items-center justify-center gap-2 transition-transform active:scale-95 disabled:opacity-60"
            >
              <span>{loading ? "Registering..." : "Complete Laboratory Registration"}</span>
              <ArrowRight size={16} />
            </button>
          </form>

          <div className="pt-2 border-t border-slate-700 text-center text-xs text-slate-400">
            <span>Already registered? </span>
            <Link to="/login/laboratory" className="text-purple-400 hover:text-purple-300 font-bold underline">
              Sign In to Laboratory System
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
