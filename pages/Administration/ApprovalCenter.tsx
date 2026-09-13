import { useState, useEffect } from "react";
import { AdminService } from "../../services/AdminService";
import { promptDialog } from "../../services/Dialogs";
import type { ApprovalRequest } from "../../services/AdminService";
import { Check, X, Clock } from "lucide-react";

export default function ApprovalCenter() {
  const [requests, setRequests] = useState<ApprovalRequest[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    AdminService.getApprovals().then(res => { setRequests(res); setLoading(false); });
  }, []);

  const handleApprove = (id: string) => {
     alert("Approved request " + id);
     setRequests(prev => prev.filter(r => r.id !== id));
  };

  const handleReject = async (id: string) => {
     const reason = await promptDialog("Enter rejection reason:", {
        title: "Reject request",
        placeholder: "Reason for rejection",
        confirmLabel: "Reject",
     });
     if (reason) {
        alert("Rejected request " + id + " for: " + reason);
        setRequests(prev => prev.filter(r => r.id !== id));
     }
  };

  return (
    <div className="space-y-4">
       <div className="bg-white p-5 rounded-xl shadow-sm border border-gray-200">
          <h3 className="text-lg font-bold text-gray-900">Pending Approvals</h3>
          <p className="text-sm text-gray-500">Review and authorize administrative requests.</p>
       </div>
       
       {loading ? <div className="text-center p-8 text-gray-500">Loading requests...</div> : requests.length === 0 ? <div className="text-center p-8 text-gray-500 bg-white rounded-xl border border-gray-200">No pending approvals.</div> : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
             {requests.map(req => (
                <div key={req.id} className="bg-white p-5 rounded-xl shadow-sm border border-gray-200 flex flex-col">
                   <div className="flex justify-between items-start mb-3">
                      <span className="px-2 py-1 bg-orange-100 text-orange-800 text-xs font-bold rounded-md">{req.type} Request</span>
                      <span className="text-xs text-gray-400 flex items-center gap-1"><Clock size={12}/> {req.date}</span>
                   </div>
                   <h4 className="font-bold text-gray-900 mb-1">{req.requester}</h4>
                   <p className="text-sm text-gray-600 mb-4 flex-1">{req.details}</p>
                   <div className="flex gap-2 border-t border-gray-100 pt-4">
                      <button onClick={() => handleApprove(req.id)} className="flex-1 py-2 bg-green-50 text-green-700 hover:bg-green-100 font-bold rounded-lg flex items-center justify-center gap-1"><Check size={16}/> Approve</button>
                      <button onClick={() => handleReject(req.id)} className="flex-1 py-2 bg-red-50 text-red-700 hover:bg-red-100 font-bold rounded-lg flex items-center justify-center gap-1"><X size={16}/> Reject</button>
                   </div>
                </div>
             ))}
          </div>
       )}
    </div>
  );
}
