import React from "react";
import { useAlerts } from "../../context/AlertsContext";
import type { SystemAlert } from "../../context/AlertsContext";
import { X, MapPin, Activity, ShieldAlert, Cpu, CheckCircle, Clock, UserCheck, PlayCircle } from "lucide-react";
import { MapContainer, TileLayer, Marker, Popup, Circle } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

// Fix for default marker icons in Leaflet with React
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png",
  iconUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png",
  shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png",
});

interface Props {
  alert: SystemAlert;
  onClose: () => void;
}

export default function AlertDetailModal({ alert, onClose }: Props) {
  const { updateAlertStatus, assignOfficer } = useAlerts();

  const handleStatusChange = async (status: SystemAlert["status"]) => {
    await updateAlertStatus(alert.id, status);
  };

  const handleAssign = async () => {
    const officer = prompt("Enter officer name to assign:");
    if (officer) {
      await assignOfficer(alert.id, officer);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="bg-white w-full max-w-4xl rounded-2xl shadow-xl flex flex-col max-h-[90vh] overflow-hidden">
        
        {/* Header */}
        <div className={`p-4 border-b flex justify-between items-start ${
          alert.priority === "CRITICAL" ? "bg-red-50 border-red-200" :
          alert.priority === "HIGH" ? "bg-orange-50 border-orange-200" :
          alert.priority === "MEDIUM" ? "bg-yellow-50 border-yellow-200" :
          "bg-blue-50 border-blue-200"
        }`}>
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className={`px-2.5 py-0.5 text-xs font-bold rounded-full ${
                alert.priority === "CRITICAL" ? "bg-red-600 text-white" :
                alert.priority === "HIGH" ? "bg-orange-500 text-white" :
                alert.priority === "MEDIUM" ? "bg-yellow-500 text-white" :
                "bg-blue-500 text-white"
              }`}>{alert.priority} ALERT</span>
              <span className="text-gray-500 text-sm">{alert.id}</span>
            </div>
            <h2 className="text-xl font-bold text-gray-900">{alert.disease} - {alert.type}</h2>
            <p className="text-gray-600 text-sm flex items-center gap-1 mt-1">
              <MapPin size={14} /> {alert.village}, {alert.taluka}, {alert.district}
            </p>
          </div>
          <button onClick={onClose} className="p-2 text-gray-500 hover:bg-white rounded-full transition-colors">
            <X size={20} />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 flex flex-col md:flex-row gap-6">
          
          <div className="flex-1 space-y-6">
            <div className="bg-gray-50 p-4 rounded-xl border border-gray-200">
              <h3 className="text-sm font-bold text-gray-500 uppercase mb-3 tracking-wider">Impact & Metrics</h3>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs text-gray-500">Affected Animals</p>
                  <p className="text-lg font-bold text-gray-900">{alert.affectedAnimals}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Suspected Cases</p>
                  <p className="text-lg font-bold text-orange-600">{alert.suspectedCases}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Confirmed Deaths</p>
                  <p className="text-lg font-bold text-red-600">{alert.deaths}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Vaccination Coverage</p>
                  <p className="text-lg font-bold text-gray-900">{alert.vaccinationCoverage}%</p>
                </div>
              </div>
            </div>

            <div className="bg-purple-50 p-4 rounded-xl border border-purple-200">
              <h3 className="text-sm font-bold text-purple-800 flex items-center gap-2 mb-3">
                <Cpu size={16} /> AI Early Warning Analysis
              </h3>
              <div className="flex justify-between items-center mb-3">
                <div>
                  <p className="text-xs text-purple-600 font-medium">Disease Risk Score</p>
                  <p className="text-2xl font-black text-purple-900">{alert.riskScore}/100</p>
                </div>
                <div className="text-right">
                  <p className="text-xs text-purple-600 font-medium">Confidence</p>
                  <p className="text-lg font-bold text-purple-800">{alert.confidence}%</p>
                </div>
              </div>
              <div className="space-y-1">
                <p className="text-xs font-medium text-purple-800 mb-2">Key Risk Factors Detected:</p>
                <p className="text-xs text-purple-700 flex items-center gap-1">? Rapid increase in suspected cases locally</p>
                <p className="text-xs text-purple-700 flex items-center gap-1">? Vaccination coverage is below protective threshold</p>
                {alert.riskScore > 80 && <p className="text-xs text-purple-700 flex items-center gap-1">? Favorable environmental conditions for vector spread</p>}
              </div>
              <div className="mt-4 pt-3 border-t border-purple-200">
                 <p className="text-sm text-purple-900 font-bold italic">Prediction: High probability of localized transmission over the next 7 days without intervention.</p>
              </div>
            </div>

            <div className="space-y-2">
              <p className="text-sm"><span className="text-gray-500">Detected At:</span> {new Date(alert.detectedAt).toLocaleString()}</p>
              <p className="text-sm"><span className="text-gray-500">Source:</span> {alert.source}</p>
              <p className="text-sm"><span className="text-gray-500">Escalation Level:</span> {alert.escalationLevel}</p>
              <p className="text-sm"><span className="text-gray-500">Assigned To:</span> {alert.assignedOfficer || "Unassigned"}</p>
            </div>
          </div>

          <div className="flex-1 flex flex-col min-h-[300px]">
            <h3 className="text-sm font-bold text-gray-500 uppercase mb-3 tracking-wider">Geospatial Context</h3>
            <div className="flex-1 rounded-xl overflow-hidden border border-gray-200 shadow-sm relative">
              <MapContainer center={[alert.latitude, alert.longitude]} zoom={12} className="w-full h-full absolute inset-0">
                <TileLayer
                  attribution="&copy; OpenStreetMap contributors"
                  url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
                />
                <Marker position={[alert.latitude, alert.longitude]}>
                  <Popup>
                    <strong>{alert.village}</strong><br/>
                    {alert.disease} outbreak area.
                  </Popup>
                </Marker>
                <Circle 
                  center={[alert.latitude, alert.longitude]} 
                  radius={3000} 
                  pathOptions={{ 
                    fillColor: alert.priority === "CRITICAL" ? "#ef4444" : "#f97316", 
                    color: "transparent", 
                    fillOpacity: 0.3 
                  }} 
                />
              </MapContainer>
            </div>
          </div>

        </div>

        {/* Footer / Workflow Actions */}
        <div className="p-4 border-t bg-gray-50 flex items-center justify-between">
           <div className="flex items-center gap-2">
             <span className="text-sm font-medium text-gray-500">Current Status:</span>
             <span className="font-bold text-gray-900">{alert.status}</span>
           </div>
           
           <div className="flex items-center gap-2">
             {alert.status === "NEW" && (
               <button onClick={() => handleStatusChange("ACKNOWLEDGED")} className="px-4 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 text-sm font-medium flex items-center gap-2">
                 <Clock size={16} /> Acknowledge Alert
               </button>
             )}
             
             {["ACKNOWLEDGED", "NEW"].includes(alert.status) && (
               <button onClick={handleAssign} className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 text-sm font-medium flex items-center gap-2">
                 <UserCheck size={16} /> Assign Officer
               </button>
             )}

             {["ACKNOWLEDGED", "ASSIGNED"].includes(alert.status) && (
               <button onClick={() => handleStatusChange("IN_PROGRESS")} className="px-4 py-2 bg-brandBlue text-white rounded-lg hover:bg-blue-700 text-sm font-medium flex items-center gap-2">
                 <PlayCircle size={16} /> Start Response
               </button>
             )}

             {alert.status === "IN_PROGRESS" && (
               <button onClick={() => handleStatusChange("RESOLVED")} className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 text-sm font-medium flex items-center gap-2">
                 <CheckCircle size={16} /> Resolve Incident
               </button>
             )}
           </div>
        </div>
      </div>
    </div>
  );
}

