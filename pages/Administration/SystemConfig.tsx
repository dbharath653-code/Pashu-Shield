import { Save } from "lucide-react";

export default function SystemConfig() {
  const handleSave = () => alert("Configuration saved successfully");

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 h-[calc(100vh-10rem)] flex flex-col overflow-hidden">
       <div className="p-5 border-b border-gray-200 bg-gray-50 flex justify-between items-center">
          <div>
             <h3 className="text-lg font-bold text-gray-900">System Configuration</h3>
             <p className="text-sm text-gray-500">Global settings and reporting thresholds.</p>
          </div>
          <button onClick={handleSave} className="px-4 py-2 bg-brandBlue text-white font-medium rounded-lg hover:bg-blue-700 flex items-center gap-2">
             <Save size={18} /> Save Changes
          </button>
       </div>
       <div className="p-6 overflow-y-auto space-y-8">
          
          <section>
             <h4 className="text-base font-bold text-gray-900 mb-4 border-b pb-2">General Settings</h4>
             <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div><label className="block text-sm text-gray-700 mb-1">Application Name</label><input type="text" defaultValue="Livestock Health Surveillance" className="w-full border border-gray-300 rounded p-2"/></div>
                <div><label className="block text-sm text-gray-700 mb-1">State</label><input type="text" defaultValue="Maharashtra" disabled className="w-full border border-gray-300 bg-gray-50 rounded p-2 text-gray-500"/></div>
                <div><label className="block text-sm text-gray-700 mb-1">Default Language</label><select className="w-full border border-gray-300 rounded p-2"><option>English</option><option>Marathi</option></select></div>
                <div><label className="block text-sm text-gray-700 mb-1">Time Zone</label><select className="w-full border border-gray-300 rounded p-2"><option>IST (UTC+05:30)</option></select></div>
             </div>
          </section>

          <section>
             <h4 className="text-base font-bold text-gray-900 mb-4 border-b pb-2">Disease Surveillance Settings</h4>
             <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div><label className="block text-sm text-gray-700 mb-1">Outbreak Alert Threshold (Cases)</label><input type="number" defaultValue={5} className="w-full border border-gray-300 rounded p-2"/></div>
                <div><label className="block text-sm text-gray-700 mb-1">Escalation Timeout (Hours)</label><input type="number" defaultValue={24} className="w-full border border-gray-300 rounded p-2"/></div>
             </div>
          </section>

          <section>
             <h4 className="text-base font-bold text-gray-900 mb-4 border-b pb-2">Data & Offline Settings</h4>
             <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div><label className="block text-sm text-gray-700 mb-1">Data Retention (Days)</label><input type="number" defaultValue={365} className="w-full border border-gray-300 rounded p-2"/></div>
                <div><label className="block text-sm text-gray-700 mb-1">Auto-Sync Interval (Minutes)</label><input type="number" defaultValue={15} className="w-full border border-gray-300 rounded p-2"/></div>
             </div>
          </section>

       </div>
    </div>
  );
}
