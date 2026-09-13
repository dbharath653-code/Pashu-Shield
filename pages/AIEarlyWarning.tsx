import React, { useState, useEffect } from "react";
import { TrendingUp, Activity, CheckCircle, ShieldAlert, BarChart2, MapPin, Loader2, Info } from "lucide-react";
import { PieChart, Pie, Cell, ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from "recharts";
import { MapContainer, TileLayer, CircleMarker, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";

export default function AIEarlyWarning() {
  const [activeTab, setActiveTab] = useState("Risk Score");
  const [loading, setLoading] = useState(false);
  const [prediction, setPrediction] = useState<any>(null);
  const [metrics, setMetrics] = useState<any>(null);
  const [outbreak, setOutbreak] = useState<any>(null);
  const [forecast, setForecast] = useState<any>(null);
  const [clusters, setClusters] = useState<any>(null);
  const [error, setError] = useState("");

  const [formData, setFormData] = useState({
    disease: "LSD",
    district: "Pune",
    time_range: "14",
    animal_population: 15000,
    affected_animals: 120,
    new_cases: 45,
    deaths: 5,
    vaccination_coverage: 0.45,
    temperature: 32.5,
    rainfall: 12.0,
    humidity: 65.0,
    animal_density: 120.5,
    previous_cases: 300,
    cases_growth_rate: 0.15
  });

  useEffect(() => {
    fetch("http://localhost:8000/api/model-performance")
      .then(res => res.json())
      .then(data => setMetrics(data))
      .catch(err => console.error("Model metrics unavailable", err));
  }, []);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: ["disease", "district", "time_range"].includes(name) ? value : parseFloat(value) || 0
    }));
  };

  const analyze = async () => {
    setLoading(true);
    setError("");
    try {
      // Predict Risk
      const pRes = await fetch("http://localhost:8000/api/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData)
      });
      if (!pRes.ok) throw new Error("AI Prediction failed");
      const pData = await pRes.json();
      setPrediction(pData);

      // Outbreak Detection
      const oRes = await fetch("http://localhost:8000/api/outbreak-detection", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
           new_cases: formData.new_cases,
           cases_growth_rate: formData.cases_growth_rate,
           deaths: formData.deaths,
           district: formData.district
        })
      });
      if (oRes.ok) setOutbreak(await oRes.json());

      // Forecast
      const fRes = await fetch("http://localhost:8000/api/forecast", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
           historical_cases: [10, 15, 22, 35, formData.new_cases],
           horizon: parseInt(formData.time_range)
        })
      });
      if (fRes.ok) setForecast(await fRes.json());

      // Clusters
      const cRes = await fetch("http://localhost:8000/api/cluster", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ districts: [formData.district] })
      });
      if (cRes.ok) setClusters(await cRes.json());

    } catch (err: any) {
      setError(err.message || "Failed to connect to ML backend.");
    } finally {
      setLoading(false);
    }
  };

  const renderTab = () => {
    if (activeTab === "Risk Score" && prediction) {
      const riskValue = prediction.risk_score;
      const pieData = [
        { name: "Risk", value: riskValue },
        { name: "Safe", value: 100 - riskValue }
      ];
      const COLORS = ["#ef4444", "#f3f4f6"];
      
      return (
        <div className="flex-1 grid grid-cols-1 md:grid-cols-3 gap-6 overflow-y-auto">
          {/* Risk Score */}
          <div className="bg-white border border-gray-200 rounded-xl p-6 flex flex-col items-center shadow-sm">
            <h3 className="text-sm font-semibold text-gray-800 mb-4 w-full">Risk Score</h3>
            <div className="relative w-48 h-48">
               <ResponsiveContainer width="100%" height="100%">
                 <PieChart>
                   <Pie data={pieData} startAngle={180} endAngle={0} innerRadius={60} outerRadius={80} dataKey="value" stroke="none">
                     {pieData.map((entry, index) => (
                       <Cell key={`cell-${index}`} fill={index === 0 ? (prediction.risk_level === "High Risk" ? "#ef4444" : prediction.risk_level === "Moderate Risk" ? "#f59e0b" : "#10b981") : COLORS[1]} />
                     ))}
                   </Pie>
                 </PieChart>
               </ResponsiveContainer>
               <div className="absolute inset-0 flex flex-col items-center justify-center top-[-20px]">
                  <span className="text-4xl font-bold text-gray-800">{riskValue}%</span>
                  <span className={`text-sm font-medium px-2 py-1 rounded-full mt-1 ${prediction.risk_level === "High Risk" ? "text-red-600 bg-red-100" : prediction.risk_level === "Moderate Risk" ? "text-orange-600 bg-orange-100" : "text-green-600 bg-green-100"}`}>{prediction.risk_level}</span>
               </div>
            </div>
            
            <div className="w-full mt-6 space-y-3 bg-gray-50 p-3 rounded-lg border border-gray-100">
               <div className="flex justify-between items-center border-b border-gray-200 pb-2">
                 <span className="text-xs text-gray-500">ML Model Probability</span>
                 <span className="text-xs font-semibold text-gray-900">{prediction.probability}</span>
               </div>
               <div className="flex justify-between items-center">
                 <span className="text-xs text-gray-500">Model Confidence</span>
                 <span className="text-xs font-semibold text-gray-900">{(prediction.confidence * 100).toFixed(1)}%</span>
               </div>
            </div>
          </div>

          {/* Explainable AI */}
          <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm">
             <h3 className="text-sm font-semibold text-gray-800 mb-1">Why this prediction?</h3>
             <p className="text-xs text-gray-500 mb-4">Top factors influencing the ML model</p>
             <div className="space-y-4">
                {prediction.top_risk_factors.map((factor: any, idx: number) => (
                   <div key={idx}>
                      <div className="flex justify-between items-center mb-1">
                         <span className="text-xs font-medium text-gray-700">{factor.factor}</span>
                         <span className="text-xs font-bold text-brandBlue">{(factor.impact * 100).toFixed(1)}% impact</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-1.5">
                         <div className="bg-brandBlue h-1.5 rounded-full" style={{ width: `${Math.min(factor.impact * 300, 100)}%` }}></div>
                      </div>
                   </div>
                ))}
             </div>
             
             <div className="mt-6 pt-4 border-t border-gray-100">
               <h3 className="text-sm font-semibold text-brandBlue mb-3">AI Recommended Actions</h3>
               <ul className="space-y-2 text-sm text-gray-700">
                 {prediction.recommended_actions.map((action: string, idx: number) => (
                   <li key={idx} className="flex items-start gap-2">
                     <CheckCircle size={16} className="mt-0.5 text-brandBlue flex-shrink-0" /> {action}
                   </li>
                 ))}
               </ul>
             </div>
          </div>

          {/* Prediction Summary */}
          <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm flex flex-col">
            <h3 className="text-sm font-semibold text-gray-800 mb-4">Prediction Summary</h3>
            <div className="space-y-4 flex-1">
              <div className="flex justify-between items-center border-b border-gray-100 pb-2">
                <span className="text-sm text-gray-500">Disease:</span>
                <span className="text-sm font-semibold text-gray-900">{prediction.disease}</span>
              </div>
              <div className="flex justify-between items-center border-b border-gray-100 pb-2">
                <span className="text-sm text-gray-500">Affected Area:</span>
                <span className="text-sm font-semibold text-gray-900">{prediction.district} District</span>
              </div>
              <div className="flex justify-between items-center border-b border-gray-100 pb-2">
                <span className="text-sm text-gray-500">Horizon:</span>
                <span className="text-sm font-semibold text-gray-900">{prediction.prediction_horizon_days} Days</span>
              </div>
              <div className="flex justify-between items-center pb-2">
                <span className="text-sm text-gray-500">Trend:</span>
                <span className={`text-sm font-semibold flex items-center gap-1 ${prediction.trend === "Increasing" ? "text-red-600" : "text-green-600"}`}>
                  <TrendingUp size={16} /> {prediction.trend}
                </span>
              </div>
            </div>
            
            {outbreak && (
              <div className={`mt-4 p-3 rounded-lg border ${outbreak.outbreak_detected ? "bg-red-50 border-red-200" : "bg-green-50 border-green-200"}`}>
                 <div className="flex items-center gap-2 mb-1">
                    <ShieldAlert size={16} className={outbreak.outbreak_detected ? "text-red-600" : "text-green-600"} />
                    <span className={`text-sm font-bold ${outbreak.outbreak_detected ? "text-red-700" : "text-green-700"}`}>
                       {outbreak.outbreak_detected ? "Outbreak Detected" : "No Outbreak Detected"}
                    </span>
                 </div>
                 <p className={`text-xs ${outbreak.outbreak_detected ? "text-red-600" : "text-green-600"}`}>
                    Anomaly Score: {outbreak.anomaly_score}
                 </p>
              </div>
            )}
          </div>
        </div>
      );
    }
    
    if (activeTab === "Forecast" && forecast) {
       return (
         <div className="flex-1 bg-white border border-gray-200 rounded-xl p-6 m-6 shadow-sm min-h-[400px]">
           <h3 className="text-sm font-semibold text-gray-800 mb-6">Predicted Cases ({formData.time_range} Days)</h3>
           <ResponsiveContainer width="100%" height={300}>
              <LineChart data={forecast.forecast}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="date" tick={{fontSize: 12}} />
                <YAxis tick={{fontSize: 12}} />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="predicted_cases" name="Forecasted Cases" stroke="#3b82f6" strokeWidth={3} dot={{r:4}} activeDot={{r: 6}} />
              </LineChart>
           </ResponsiveContainer>
         </div>
       );
    }
    
    if (activeTab === "Spatiotemporal Clustering" && clusters) {
       return (
          <div className="flex-1 bg-white border border-gray-200 rounded-xl p-6 m-6 shadow-sm min-h-[400px] flex flex-col">
             <h3 className="text-sm font-semibold text-gray-800 mb-4">DBSCAN Detected Clusters</h3>
             <div className="flex-1 rounded-lg border border-gray-200 relative">
               <MapContainer center={[19.7515, 75.7139]} zoom={6} style={{ height: "100%", width: "100%", zIndex: 1 }}>
                  <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" attribution="&copy; OpenStreetMap" />
                  {clusters.clusters.map((c: any, i: number) => (
                     <CircleMarker key={i} center={[c.lat, c.lng]} radius={c.cases / 5} color={c.risk_level === "High Risk" ? "red" : "orange"} fillOpacity={0.4}>
                        <Popup>
                           <div className="font-bold">{c.cluster_id}</div>
                           <div className="text-xs">Cases: {c.cases}</div>
                           <div className="text-xs text-red-600">{c.risk_level}</div>
                        </Popup>
                     </CircleMarker>
                  ))}
               </MapContainer>
             </div>
          </div>
       );
    }

    return (
      <div className="flex-1 flex items-center justify-center text-gray-500">
        <p>Click Analyze to generate real AI predictions based on the input factors.</p>
      </div>
    );
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 flex flex-col h-full overflow-hidden">
      {/* Top Navigation */}
      <div className="flex border-b border-gray-200 p-2 overflow-x-auto gap-2">
        <button onClick={() => setActiveTab("Risk Score")} className={`px-4 py-2 text-sm font-medium rounded-md ${activeTab === "Risk Score" ? "bg-brandBlue text-white" : "text-gray-600 hover:bg-gray-50"}`}>Risk Score</button>
        <button onClick={() => setActiveTab("Forecast")} className={`px-4 py-2 text-sm font-medium rounded-md ${activeTab === "Forecast" ? "bg-brandBlue text-white" : "text-gray-600 hover:bg-gray-50"}`}>Forecast</button>
        <button onClick={() => setActiveTab("Spatiotemporal Clustering")} className={`px-4 py-2 text-sm font-medium rounded-md ${activeTab === "Spatiotemporal Clustering" ? "bg-brandBlue text-white" : "text-gray-600 hover:bg-gray-50"}`}>Spatiotemporal Clustering</button>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Left Sidebar Form */}
        <div className="w-80 border-r border-gray-200 bg-gray-50 flex flex-col h-full">
           <div className="p-4 border-b border-gray-200 bg-white">
              <h2 className="font-bold text-gray-800 flex items-center gap-2"><BarChart2 size={18} className="text-brandBlue"/> Surveillance Inputs</h2>
              <p className="text-xs text-gray-500 mt-1">Configure parameters for ML prediction</p>
           </div>
           
           <div className="flex-1 overflow-y-auto p-4 space-y-4">
              <div className="space-y-1">
                <label className="text-xs font-semibold text-gray-700">Disease</label>
                <select name="disease" value={formData.disease} onChange={handleChange} className="block w-full rounded-md border-gray-300 shadow-sm focus:border-brandBlue focus:ring-brandBlue sm:text-sm p-2 border bg-white">
                  <option value="LSD">LSD</option>
                  <option value="FMD">FMD</option>
                </select>
              </div>
              <div className="space-y-1">
                <label className="text-xs font-semibold text-gray-700">District</label>
                <select name="district" value={formData.district} onChange={handleChange} className="block w-full rounded-md border-gray-300 shadow-sm focus:border-brandBlue focus:ring-brandBlue sm:text-sm p-2 border bg-white">
                  <option value="Pune">Pune</option>
                  <option value="Satara">Satara</option>
                  <option value="Nashik">Nashik</option>
                  <option value="Nagpur">Nagpur</option>
                </select>
              </div>
              <div className="space-y-1">
                <label className="text-xs font-semibold text-gray-700">Time Horizon</label>
                <select name="time_range" value={formData.time_range} onChange={handleChange} className="block w-full rounded-md border-gray-300 shadow-sm focus:border-brandBlue focus:ring-brandBlue sm:text-sm p-2 border bg-white">
                  <option value="7">7 Days</option>
                  <option value="14">14 Days</option>
                  <option value="30">30 Days</option>
                </select>
              </div>
              
              <hr className="border-gray-200"/>
              
              <div className="grid grid-cols-2 gap-3">
                 <div className="space-y-1">
                   <label className="text-xs font-medium text-gray-600">Total Animals</label>
                   <input type="number" name="animal_population" value={formData.animal_population} onChange={handleChange} className="w-full text-sm p-1.5 border border-gray-300 rounded" />
                 </div>
                 <div className="space-y-1">
                   <label className="text-xs font-medium text-gray-600">Affected</label>
                   <input type="number" name="affected_animals" value={formData.affected_animals} onChange={handleChange} className="w-full text-sm p-1.5 border border-gray-300 rounded" />
                 </div>
                 <div className="space-y-1">
                   <label className="text-xs font-medium text-gray-600">New Cases</label>
                   <input type="number" name="new_cases" value={formData.new_cases} onChange={handleChange} className="w-full text-sm p-1.5 border border-gray-300 rounded" />
                 </div>
                 <div className="space-y-1">
                   <label className="text-xs font-medium text-gray-600">Deaths</label>
                   <input type="number" name="deaths" value={formData.deaths} onChange={handleChange} className="w-full text-sm p-1.5 border border-gray-300 rounded" />
                 </div>
                 <div className="space-y-1">
                   <label className="text-xs font-medium text-gray-600">Vax Coverage</label>
                   <input type="number" step="0.1" name="vaccination_coverage" value={formData.vaccination_coverage} onChange={handleChange} className="w-full text-sm p-1.5 border border-gray-300 rounded" />
                 </div>
                 <div className="space-y-1">
                   <label className="text-xs font-medium text-gray-600">Growth Rate</label>
                   <input type="number" step="0.1" name="cases_growth_rate" value={formData.cases_growth_rate} onChange={handleChange} className="w-full text-sm p-1.5 border border-gray-300 rounded" />
                 </div>
                 <div className="space-y-1">
                   <label className="text-xs font-medium text-gray-600">Temp (°C)</label>
                   <input type="number" step="0.1" name="temperature" value={formData.temperature} onChange={handleChange} className="w-full text-sm p-1.5 border border-gray-300 rounded" />
                 </div>
                 <div className="space-y-1">
                   <label className="text-xs font-medium text-gray-600">Humidity (%)</label>
                   <input type="number" step="0.1" name="humidity" value={formData.humidity} onChange={handleChange} className="w-full text-sm p-1.5 border border-gray-300 rounded" />
                 </div>
              </div>
           </div>
           
           <div className="p-4 border-t border-gray-200 bg-white">
              <button onClick={analyze} disabled={loading} className="w-full bg-brandBlue text-white px-4 py-2.5 rounded-lg text-sm font-bold hover:bg-blue-600 transition-colors flex items-center justify-center gap-2 disabled:bg-blue-300">
                {loading ? <Loader2 size={18} className="animate-spin" /> : <Activity size={18} />}
                {loading ? "Analyzing..." : "Analyze Risk"}
              </button>
           </div>
        </div>

        {/* Right Content Area */}
        <div className="flex-1 bg-gray-50 flex flex-col h-full overflow-hidden">
           {/* Model Status Header */}
           <div className="bg-yellow-50 border-b border-yellow-200 p-3 flex justify-between items-center text-xs">
              <div className="flex items-center gap-2">
                 <Info size={14} className="text-yellow-700" />
                 <span className="font-semibold text-yellow-800">AI Prediction</span>
                 <span className="text-yellow-700">— Generated using trained models from available surveillance data.</span>
              </div>
              {metrics ? (
                 <div className="flex gap-4 text-yellow-800">
                    <span><strong className="font-bold">Model:</strong> {metrics.model}</span>
                    <span><strong className="font-bold">Accuracy:</strong> {(metrics.accuracy * 100).toFixed(1)}%</span>
                    <span><strong className="font-bold">Samples:</strong> {metrics.training_samples}</span>
                    <span className="italic text-yellow-600 border-l border-yellow-300 pl-4">Development model — trained on demo data</span>
                 </div>
              ) : (
                 <div className="text-red-600 font-bold">AI Model Backend Offline — Ensure FastAPI is running.</div>
              )}
           </div>
           
           {error && (
              <div className="m-4 p-4 bg-red-50 text-red-700 border border-red-200 rounded-lg text-sm">
                 <strong className="font-bold">Error:</strong> {error}
              </div>
           )}

           <div className="flex-1 overflow-y-auto p-4 flex flex-col">
              {loading ? (
                 <div className="flex-1 flex flex-col items-center justify-center text-gray-500 gap-4">
                    <Loader2 size={40} className="animate-spin text-brandBlue" />
                    <p className="font-medium">AI model analyzing surveillance data...</p>
                 </div>
              ) : (
                 renderTab()
              )}
           </div>
        </div>
      </div>
    </div>
  );
}
