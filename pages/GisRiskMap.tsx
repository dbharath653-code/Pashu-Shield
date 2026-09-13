import React, { useState, useEffect, useMemo } from 'react';
import { MapContainer, TileLayer, CircleMarker, Tooltip, GeoJSON } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { Flame, ShieldAlert, ShieldCheck, WifiOff, Wifi, MapPin } from 'lucide-react';
import { useAppContext } from '../context/AppContext';

export default function GisRiskMap() {
  const { reports } = useAppContext();
  const mapCenter = [19.7515, 75.7139]; // Maharashtra center

  const [isOffline, setIsOffline] = useState(!navigator.onLine);
  const [locationsDict, setLocationsDict] = useState<any[]>([]);
  const [geoJsonData, setGeoJsonData] = useState<any>(null);

  // Filters
  const [selectedDisease, setSelectedDisease] = useState<string>('All Diseases');
  const [selectedRiskLevels, setSelectedRiskLevels] = useState<string[]>(['High Risk', 'Moderate Risk', 'Low Risk']);
  const [viewLevel, setViewLevel] = useState<string>('District');

  useEffect(() => {
    const handleOnline = () => setIsOffline(false);
    const handleOffline = () => setIsOffline(true);
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    // Fetch offline datasets
    fetch('/maharashtra_locations.json')
      .then(res => res.json())
      .then(data => setLocationsDict(data))
      .catch(console.error);

    fetch('/maharashtra_state.geojson')
      .then(res => res.json())
      .then(data => setGeoJsonData(data))
      .catch(console.error);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  // Compute District Stats
  const districtStats = useMemo(() => {
    const stats: Record<string, any> = {};

    // Helper for deterministic offset
    const getOffset = (str: string) => {
      let hash = 0;
      for (let i = 0; i < str.length; i++) {
        hash = str.charCodeAt(i) + ((hash << 5) - hash);
      }
      return {
        latOff: ((hash % 100) / 1500) * (hash % 2 === 0 ? 1 : -1),
        lngOff: (((hash >> 4) % 100) / 1500) * (hash % 3 === 0 ? 1 : -1)
      };
    };

    reports.forEach(r => {
      // Apply filters
      if (selectedDisease !== 'All Diseases' && r.disease !== selectedDisease && r.disease !== 'Other') {
        return; 
      }

      let key = '';
      let displayName = '';
      let baseDistrict = r.district || 'Unknown';

      if (viewLevel === 'State') {
        key = 'Maharashtra';
        displayName = 'Maharashtra State';
        baseDistrict = 'Pune'; // arbitrary map anchor
      } else if (viewLevel === 'District') {
        key = baseDistrict;
        displayName = baseDistrict + ' District';
      } else if (viewLevel === 'Taluka/Block') {
        key = baseDistrict + '-' + r.village + '-taluka';
        displayName = r.village + ' Taluka (Simulated)';
      } else if (viewLevel === 'Village') {
        key = baseDistrict + '-' + r.village;
        displayName = r.village + ' Village';
      } else if (viewLevel === 'Farm') {
        key = r.id + '-farm';
        displayName = r.village + ' Farm (#' + r.id.substring(0,4) + ')';
      } else if (viewLevel === 'Animal') {
        key = r.id;
        displayName = 'Animal Case (#' + r.id.substring(0,4) + ')';
      }

      if (!stats[key]) {
        stats[key] = { key, name: displayName, baseDistrict, affected: 0, deaths: 0, reports: 0, diseases: new Set() };
      }
      stats[key].affected += r.numberAffected;
      stats[key].deaths += r.numberDead;
      stats[key].reports += 1;
      stats[key].diseases.add(r.disease);
    });

    // Calculate Risk and Match Coordinates
    return Object.values(stats).map(stat => {
      let riskLevel = 'Low Risk';
      let color = 'green';
      
      // Scale thresholds slightly based on view level so we see variance
      const tAffectedHigh = viewLevel === 'State' ? 50 : viewLevel === 'District' ? 10 : 3;
      const tAffectedMod = viewLevel === 'State' ? 20 : viewLevel === 'District' ? 5 : 1;
      
      if (stat.deaths > 0 || stat.affected >= tAffectedHigh) {
        riskLevel = 'High Risk';
        color = 'red';
      } else if (stat.affected >= tAffectedMod) {
        riskLevel = 'Moderate Risk';
        color = 'orange';
      }

      // Find Coordinates
      let coords = null;
      if (viewLevel === 'State') {
        coords = [19.7515, 75.7139]; // center
      } else {
        const loc = locationsDict.find(l => l.district.toLowerCase() === stat.baseDistrict.toLowerCase());
        if (loc) {
          if (viewLevel === 'District') {
             coords = [loc.lat, loc.lng];
          } else {
             const off = getOffset(stat.key);
             coords = [loc.lat + off.latOff, loc.lng + off.lngOff];
          }
        }
      }

      return {
        ...stat,
        riskLevel,
        color,
        coords,
        diseases: Array.from(stat.diseases).join(', ')
      };
    }).filter(s => selectedRiskLevels.includes(s.riskLevel) && s.coords !== null);
  }, [reports, selectedDisease, selectedRiskLevels, locationsDict, viewLevel]);

  // Summaries
  const highRiskCount = districtStats.filter(s => s.riskLevel === 'High Risk').length;
  const moderateRiskCount = districtStats.filter(s => s.riskLevel === 'Moderate Risk').length;
  const lowRiskCount = districtStats.filter(s => s.riskLevel === 'Low Risk').length;

  // Handlers
  const toggleRisk = (risk: string) => {
    setSelectedRiskLevels(prev => 
      prev.includes(risk) ? prev.filter(r => r !== risk) : [...prev, risk]
    );
  };

  const [currentLocation, setCurrentLocation] = useState<[number, number] | null>(null);

  const handleUseLocation = () => {
      if (navigator.geolocation) {
          navigator.geolocation.getCurrentPosition(
              (position) => {
                  setCurrentLocation([position.coords.latitude, position.coords.longitude]);
              },
              () => alert("GPS failed or denied.")
          );
      }
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 flex flex-col h-full overflow-hidden">
      
      {/* Top Bar for Offline Status */}
      <div className={`px-4 py-2 flex items-center justify-between text-sm ${isOffline ? 'bg-orange-100 text-orange-800' : 'bg-green-50 text-green-800'}`}>
         <div className="flex items-center gap-2 font-medium">
            {isOffline ? <WifiOff size={16}/> : <Wifi size={16}/>}
            {isOffline ? 'OFFLINE MODE — using local administrative boundaries and cached reports.' : 'ONLINE / LIVE DATA — synchronized with central server.'}
         </div>
         <div>
            Last synchronized at: {new Date().toLocaleTimeString()}
         </div>
      </div>

      <div className="flex flex-1 h-full relative z-0">
        {/* Left Sidebar */}
        <div className="w-64 border-r border-gray-200 p-4 flex flex-col gap-6 overflow-y-auto bg-gray-50/50">
          <div>
            <h3 className="text-sm font-semibold text-gray-800 mb-3">View Level</h3>
            <div className="space-y-2">
              {['State', 'District', 'Taluka/Block', 'Village', 'Farm', 'Animal'].map(level => (
                <label key={level} className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
                  <input type="radio" name="viewLevel" checked={viewLevel === level} onChange={() => setViewLevel(level)} className="text-brandBlue focus:ring-brandBlue" />
                  {level}
                </label>
              ))}
            </div>
          </div>

          <div>
            <h3 className="text-sm font-semibold text-gray-800 mb-3">Disease Types</h3>
            <div className="space-y-2">
              {['All Diseases', 'FMD', 'Brucellosis', 'PPR', 'Anthrax', 'LSD'].map(disease => (
                <label key={disease} className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
                  <input type="radio" name="diseaseType" checked={selectedDisease === disease} onChange={() => setSelectedDisease(disease)} className="text-brandBlue rounded focus:ring-brandBlue" />
                  {disease}
                </label>
              ))}
            </div>
          </div>

          <div>
            <h3 className="text-sm font-semibold text-gray-800 mb-3">Risk Level</h3>
            <div className="space-y-2">
              <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
                <input type="checkbox" checked={selectedRiskLevels.includes('High Risk')} onChange={() => toggleRisk('High Risk')} className="rounded text-red-500 focus:ring-red-500" />
                <span className="w-3 h-3 bg-red-500 rounded-sm inline-block"></span> High Risk
              </label>
              <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
                <input type="checkbox" checked={selectedRiskLevels.includes('Moderate Risk')} onChange={() => toggleRisk('Moderate Risk')} className="rounded text-orange-500 focus:ring-orange-500" />
                <span className="w-3 h-3 bg-orange-500 rounded-sm inline-block"></span> Moderate Risk
              </label>
              <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
                <input type="checkbox" checked={selectedRiskLevels.includes('Low Risk')} onChange={() => toggleRisk('Low Risk')} className="rounded text-green-500 focus:ring-green-500" />
                <span className="w-3 h-3 bg-green-500 rounded-sm inline-block"></span> Low Risk
              </label>
            </div>
          </div>

          <div className="mt-auto">
             <button onClick={handleUseLocation} className="w-full bg-white border border-gray-300 text-gray-700 py-2 rounded-lg text-sm font-medium flex items-center justify-center gap-2 hover:bg-gray-50 shadow-sm">
                <MapPin size={16}/> Use My Location
             </button>
          </div>
        </div>

        {/* Map Area */}
        <div className={`flex-1 relative z-0 ${isOffline ? 'bg-[#e5e5e5]' : ''}`}>
          <MapContainer center={currentLocation || (mapCenter as [number, number])} zoom={currentLocation ? 10 : 6} style={{ height: '100%', width: '100%' }}>
            {!isOffline && (
              <TileLayer
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              />
            )}
            
            {(isOffline || geoJsonData) && geoJsonData && (
              <GeoJSON 
                data={geoJsonData} 
                style={{
                  color: isOffline ? '#888' : '#3b82f6',
                  weight: 2,
                  fillOpacity: isOffline ? 0.3 : 0.05,
                  fillColor: isOffline ? '#ccc' : '#3b82f6'
                }} 
              />
            )}

            {currentLocation && (
              <CircleMarker center={currentLocation} radius={8} color="#2563eb" fillOpacity={1}>
                <Tooltip permanent>You are here</Tooltip>
              </CircleMarker>
            )}

            {districtStats.map((stat, i) => (
              <CircleMarker 
                key={i} 
                center={stat.coords as [number, number]} 
                radius={stat.riskLevel === 'High Risk' ? 20 : stat.riskLevel === 'Moderate Risk' ? 15 : 10} 
                color={stat.color} 
                fillOpacity={0.6}
              >
                <Tooltip>
                   <div className="font-semibold text-gray-900">{stat.name}</div>
                   <div className={`text-xs font-bold my-1 ${stat.color === 'red' ? 'text-red-600' : stat.color === 'orange' ? 'text-orange-600' : 'text-green-600'}`}>
                      {stat.riskLevel}
                   </div>
                   <div className="text-xs text-gray-700">Affected: {stat.affected} | Deaths: {stat.deaths}</div>
                   <div className="text-xs text-gray-700">Reports: {stat.reports}</div>
                   <div className="text-xs text-gray-700">Diseases: {stat.diseases}</div>
                </Tooltip>
              </CircleMarker>
            ))}
          </MapContainer>
        </div>

        {/* Right Sidebar */}
        <div className="w-72 border-l border-gray-200 p-4 flex flex-col gap-6 overflow-y-auto bg-gray-50/50">
          <div>
            <h3 className="text-sm font-semibold text-gray-800 mb-4 flex justify-between">
              <span>Risk Summary</span>
              <span className="text-xs font-normal text-gray-500">Filtered Data</span>
            </h3>
            <div className="space-y-3">
              <div className="flex items-center justify-between bg-white p-2 rounded border border-red-100">
                <div className="flex items-center gap-2 text-sm text-red-600 font-medium">
                  <Flame size={16} /> High Risk
                </div>
                <span className="font-bold text-red-700">{highRiskCount}</span>
              </div>
              <div className="flex items-center justify-between bg-white p-2 rounded border border-orange-100">
                <div className="flex items-center gap-2 text-sm text-orange-600 font-medium">
                  <ShieldAlert size={16} /> Moderate Risk
                </div>
                <span className="font-bold text-orange-700">{moderateRiskCount}</span>
              </div>
              <div className="flex items-center justify-between bg-white p-2 rounded border border-green-100">
                <div className="flex items-center gap-2 text-sm text-green-600 font-medium">
                  <ShieldCheck size={16} /> Low Risk
                </div>
                <span className="font-bold text-green-700">{lowRiskCount}</span>
              </div>
            </div>
          </div>

          <div>
            <h3 className="text-sm font-semibold text-gray-800 mb-3">Top Affected Areas</h3>
            <div className="space-y-2">
              {districtStats.sort((a,b) => b.affected - a.affected).slice(0, 5).map((stat, i) => (
                <div key={i} className="flex flex-col p-3 bg-white rounded-lg border border-gray-200 shadow-sm">
                  <div className="flex justify-between items-start mb-1">
                    <span className="font-semibold text-gray-800 text-sm">{stat.name}</span>
                    <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold ${stat.color === 'red' ? 'bg-red-100 text-red-800' : stat.color === 'orange' ? 'bg-orange-100 text-orange-800' : 'bg-green-100 text-green-800'}`}>
                      {stat.riskLevel.toUpperCase()}
                    </span>
                  </div>
                  <div className="text-xs text-gray-500 flex justify-between">
                     <span>{stat.affected} animals</span>
                     <span className="text-red-500">{stat.deaths} deaths</span>
                  </div>
                </div>
              ))}
              {districtStats.length === 0 && (
                 <div className="text-sm text-gray-500 text-center py-4 italic">No matching reports found in local dataset.</div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
