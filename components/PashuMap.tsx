import { useEffect, useRef, useState } from "react";
import { MapContainer, TileLayer, CircleMarker, Popup, Polyline } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import { Key, Search, Flame, Crosshair, AlertCircle } from "lucide-react";

export interface MapPoint {
  id: string;
  name: string;
  lat: number;
  lng: number;
  type: "cluster" | "facility" | "lab" | "report" | "vet";
  riskLevel?: "High Risk" | "Moderate Risk" | "Low Risk" | "Critical";
  details?: string;
  affected?: number;
  deaths?: number;
}

interface PashuMapProps {
  center?: [number, number];
  zoom?: number;
  points?: MapPoint[];
  routeWaypoints?: { lat: number; lng: number }[];
  height?: string;
  showSearch?: boolean;
  showHeatmapToggle?: boolean;
  onPointSelect?: (point: MapPoint) => void;
}

export default function PashuMap({
  center = [19.25, 75.5], // Maharashtra center
  zoom = 7,
  points = [],
  routeWaypoints = [],
  height = "480px",
  showSearch = true,
  showHeatmapToggle = true,
  onPointSelect
}: PashuMapProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);
  
  const [apiKey, setApiKey] = useState<string>(() => {
    return (
      (import.meta.env?.VITE_GOOGLE_MAPS_API_KEY as string) ||
      localStorage.getItem("pashu_google_maps_api_key") ||
      ""
    );
  });

  const [showKeyModal, setShowKeyModal] = useState(false);
  const [tempKeyInput, setTempKeyInput] = useState("");
  const [isGoogleReady, setIsGoogleReady] = useState(false);
  const [googleLoadError, setGoogleLoadError] = useState<string | null>(null);
  const [showHeatmap, setShowHeatmap] = useState(false);
  const [userGpsLocation, setUserGpsLocation] = useState<{ lat: number; lng: number } | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  const googleMapInstance = useRef<any>(null);
  const markersRef = useRef<any[]>([]);
  const heatmapLayerRef = useRef<any>(null);
  const directionsRendererRef = useRef<any>(null);

  // Load Google Maps JavaScript API
  useEffect(() => {
    if (!apiKey || apiKey.trim() === "") {
      setIsGoogleReady(false);
      setGoogleLoadError(null);
      return;
    }

    // Check if google maps script already loaded with this key
    if ((window as any).google && (window as any).google.maps) {
      setIsGoogleReady(true);
      setGoogleLoadError(null);
      return;
    }

    // Remove any previously inserted failing google scripts
    const existing = document.getElementById("google-maps-sdk-script");
    if (existing) existing.remove();

    const script = document.createElement("script");
    script.id = "google-maps-sdk-script";
    script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}&libraries=places,geometry,visualization`;
    script.async = true;
    script.defer = true;

    script.onload = () => {
      setIsGoogleReady(true);
      setGoogleLoadError(null);
    };

    script.onerror = () => {
      setIsGoogleReady(false);
      setGoogleLoadError("Failed loading Google Maps SDK. Please check your API key, domain restrictions, and billing status.");
    };

    document.head.appendChild(script);

    // Global Google Auth Failure Handler
    (window as any).gm_authFailure = () => {
      setIsGoogleReady(false);
      setGoogleLoadError("Google Maps authentication failed (gm_authFailure). The API key is invalid or unauthorized.");
    };
  }, [apiKey]);

  // Initialize and update Google Map instance
  useEffect(() => {
    if (!isGoogleReady || !mapContainerRef.current || !(window as any).google?.maps) {
      return;
    }

    try {
      const g = (window as any).google.maps;
      
      if (!googleMapInstance.current) {
        const map = new g.Map(mapContainerRef.current, {
          center: { lat: center[0], lng: center[1] },
          zoom: zoom,
          mapTypeId: "roadmap",
          mapTypeControl: true,
          mapTypeControlOptions: {
            style: g.MapTypeControlStyle.DROPDOWN_MENU,
            position: g.ControlPosition.TOP_LEFT
          },
          streetViewControl: false,
          fullscreenControl: true,
          zoomControl: true
        });
        googleMapInstance.current = map;
      }

      const map = googleMapInstance.current;

      // Clear old markers
      markersRef.current.forEach((m) => m.setMap(null));
      markersRef.current = [];

      // Render custom Google Maps markers
      points.forEach((p) => {
        const color =
          p.riskLevel === "Critical" || p.riskLevel === "High Risk"
            ? "#dc2626"
            : p.type === "facility"
            ? "#2563eb"
            : p.type === "lab"
            ? "#7c3aed"
            : "#16a34a";

        // SVG Pin Icon
        const svgIcon = {
          path: "M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z",
          fillColor: color,
          fillOpacity: 0.95,
          strokeWeight: 1.5,
          strokeColor: "#ffffff",
          scale: 1.6,
          anchor: new g.Point(12, 22)
        };

        const marker = new g.Marker({
          position: { lat: p.lat, lng: p.lng },
          map: map,
          title: p.name,
          icon: svgIcon
        });

        const infoWindow = new g.InfoWindow({
          content: `
            <div style="padding: 10px; font-family: system-ui, sans-serif; max-width: 240px;">
              <h4 style="margin: 0 0 4px 0; font-size: 14px; font-weight: 700; color: #111827;">${p.name}</h4>
              <p style="margin: 0; font-size: 12px; color: #4b5563; text-transform: capitalize;">Role/Type: <b>${p.type}</b></p>
              ${
                p.riskLevel
                  ? `<div style="margin: 6px 0; display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 700; background: ${color}22; color: ${color};">
                      ${p.riskLevel}
                     </div>`
                  : ""
              }
              ${p.details ? `<p style="margin: 4px 0 0 0; font-size: 12px; color: #374151;">${p.details}</p>` : ""}
              ${
                p.affected
                  ? `<p style="margin: 2px 0 0 0; font-size: 11px; color: #6b7280;">Affected Livestock: <b>${p.affected}</b></p>`
                  : ""
              }
            </div>
          `
        });

        marker.addListener("click", () => {
          infoWindow.open(map, marker);
          if (onPointSelect) onPointSelect(p);
        });

        markersRef.current.push(marker);
      });

      // Heatmap Layer (Google Maps visualization library)
      if (showHeatmap && g.visualization?.HeatmapLayer) {
        if (!heatmapLayerRef.current) {
          const heatData = points.map((pt) => ({
            location: new g.LatLng(pt.lat, pt.lng),
            weight: pt.riskLevel === "Critical" ? 5 : pt.riskLevel === "High Risk" ? 3 : 1
          }));

          heatmapLayerRef.current = new g.visualization.HeatmapLayer({
            data: heatData,
            radius: 40,
            opacity: 0.7,
            map: map
          });
        } else {
          heatmapLayerRef.current.setMap(map);
        }
      } else if (heatmapLayerRef.current) {
        heatmapLayerRef.current.setMap(null);
      }

      // Directions Route Line
      if (routeWaypoints && routeWaypoints.length > 1) {
        if (!directionsRendererRef.current) {
          directionsRendererRef.current = new g.DirectionsRenderer({
            suppressMarkers: false,
            polylineOptions: { strokeColor: "#2563eb", strokeWeight: 5 }
          });
          directionsRendererRef.current.setMap(map);
        }

        const origin = routeWaypoints[0];
        const destination = routeWaypoints[routeWaypoints.length - 1];

        const directionsService = new g.DirectionsService();
        directionsService.route(
          {
            origin: { lat: origin.lat, lng: origin.lng },
            destination: { lat: destination.lat, lng: destination.lng },
            travelMode: g.TravelMode.DRIVING
          },
          (res: any, status: any) => {
            if (status === g.DirectionsStatus.OK) {
              directionsRendererRef.current.setDirections(res);
            }
          }
        );
      } else if (directionsRendererRef.current) {
        directionsRendererRef.current.setDirections({ routes: [] });
      }
    } catch (e) {
      console.warn("Google Maps render error:", e);
    }
  }, [isGoogleReady, points, center, zoom, showHeatmap, routeWaypoints]);

  const handleSaveApiKey = () => {
    const trimmed = tempKeyInput.trim();
    if (trimmed) {
      setApiKey(trimmed);
      localStorage.setItem("pashu_google_maps_api_key", trimmed);
      setShowKeyModal(false);
    }
  };

  const handleRemoveKey = () => {
    setApiKey("");
    localStorage.removeItem("pashu_google_maps_api_key");
    setIsGoogleReady(false);
    setGoogleLoadError(null);
    setShowKeyModal(false);
  };

  const handleLocateMe = () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          const lat = pos.coords.latitude;
          const lng = pos.coords.longitude;
          setUserGpsLocation({ lat, lng });

          if (googleMapInstance.current && (window as any).google?.maps) {
            googleMapInstance.current.setCenter({ lat, lng });
            googleMapInstance.current.setZoom(12);

            // Add pulsing current position marker
            new (window as any).google.maps.Marker({
              position: { lat, lng },
              map: googleMapInstance.current,
              title: "Your Location",
              icon: {
                path: (window as any).google.maps.SymbolPath.CIRCLE,
                scale: 8,
                fillColor: "#0284c7",
                fillOpacity: 1,
                strokeWeight: 2,
                strokeColor: "#ffffff"
              }
            });
          }
        },
        () => alert("Unable to access GPS location.")
      );
    }
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;

    if (isGoogleReady && (window as any).google?.maps) {
      const geocoder = new (window as any).google.maps.Geocoder();
      geocoder.geocode({ address: `${searchQuery}, Maharashtra, India` }, (results: any, status: any) => {
        if (status === "OK" && results && results[0]) {
          const loc = results[0].geometry.location;
          googleMapInstance.current.setCenter(loc);
          googleMapInstance.current.setZoom(11);
        } else {
          alert(`Location "${searchQuery}" not found on Google Maps.`);
        }
      });
    }
  };

  const activeProviderIsGoogle = isGoogleReady && !googleLoadError;

  return (
    <div className="relative rounded-2xl overflow-hidden border border-gray-200 shadow-sm flex flex-col bg-white" style={{ height }}>
      {/* Top Controls Toolbar */}
      <div className="p-3 bg-white/95 backdrop-blur-md border-b border-gray-200 flex flex-wrap items-center justify-between gap-2 z-20 shrink-0">
        <div className="flex items-center gap-2">
          {/* Provider Badge */}
          <div
            className={`px-2.5 py-1 rounded-full text-xs font-bold flex items-center gap-1.5 border shadow-2xs ${
              activeProviderIsGoogle
                ? "bg-emerald-50 text-emerald-800 border-emerald-300"
                : "bg-blue-50 text-blue-800 border-blue-200"
            }`}
          >
            <span
              className={`w-2 h-2 rounded-full ${
                activeProviderIsGoogle ? "bg-emerald-500 animate-pulse" : "bg-blue-500"
              }`}
            />
            <span>{activeProviderIsGoogle ? "Google Maps API (Live)" : "Leaflet GIS (Active Fallback)"}</span>
          </div>

          {/* Key Config Button */}
          <button
            onClick={() => {
              setTempKeyInput(apiKey);
              setShowKeyModal(true);
            }}
            className="flex items-center gap-1 text-xs text-gray-700 hover:text-blue-600 bg-gray-100 hover:bg-gray-200 px-2.5 py-1 rounded-lg font-medium transition-colors border border-gray-200"
            title="Configure Google Maps API Key"
          >
            <Key size={13} className="text-amber-600" />
            <span>{apiKey ? "Key Configured" : "Enter Google API Key"}</span>
          </button>
        </div>

        {/* Search & Map Action Toggles */}
        <div className="flex items-center gap-2">
          {showSearch && activeProviderIsGoogle && (
            <form onSubmit={handleSearchSubmit} className="flex items-center">
              <div className="relative">
                <input
                  ref={searchInputRef}
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search village/district..."
                  className="w-44 sm:w-56 text-xs pl-7 pr-2 py-1.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
                <Search size={13} className="absolute left-2 top-2 text-gray-400" />
              </div>
            </form>
          )}

          {showHeatmapToggle && activeProviderIsGoogle && (
            <button
              onClick={() => setShowHeatmap(!showHeatmap)}
              className={`px-2.5 py-1 rounded-lg text-xs font-semibold flex items-center gap-1 transition-colors ${
                showHeatmap ? "bg-red-600 text-white" : "bg-gray-100 text-gray-700 hover:bg-gray-200"
              }`}
              title="Toggle Outbreak Density Heatmap"
            >
              <Flame size={13} />
              <span className="hidden sm:inline">Heatmap</span>
            </button>
          )}

          <button
            onClick={handleLocateMe}
            className="p-1.5 bg-gray-100 hover:bg-gray-200 rounded-lg text-gray-700 transition-colors"
            title="Recenter to My GPS Location"
          >
            <Crosshair size={15} />
          </button>
        </div>
      </div>

      {/* Error notification if key is invalid */}
      {googleLoadError && (
        <div className="px-4 py-2 bg-amber-50 text-amber-900 border-b border-amber-200 text-xs flex items-center justify-between gap-2 z-20">
          <div className="flex items-center gap-2">
            <AlertCircle size={15} className="text-amber-600 shrink-0" />
            <span>{googleLoadError}</span>
          </div>
          <button
            onClick={() => setShowKeyModal(true)}
            className="text-xs font-bold underline text-amber-800 hover:text-amber-900"
          >
            Update Key
          </button>
        </div>
      )}

      {/* Map View Canvas */}
      <div className="flex-1 relative w-full h-full">
        {activeProviderIsGoogle ? (
          <div ref={mapContainerRef} className="w-full h-full" />
        ) : (
          <MapContainer
            center={userGpsLocation ? [userGpsLocation.lat, userGpsLocation.lng] : center}
            zoom={zoom}
            style={{ height: "100%", width: "100%" }}
            scrollWheelZoom={false}
          >
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            {points.map((p) => {
              const color =
                p.riskLevel === "Critical" || p.riskLevel === "High Risk"
                  ? "#dc2626"
                  : p.type === "facility"
                  ? "#2563eb"
                  : p.type === "lab"
                  ? "#7c3aed"
                  : "#16a34a";

              return (
                <CircleMarker
                  key={p.id}
                  center={[p.lat, p.lng]}
                  radius={p.type === "cluster" ? 14 : 9}
                  pathOptions={{
                    fillColor: color,
                    fillOpacity: 0.75,
                    color: "#ffffff",
                    weight: 2
                  }}
                  eventHandlers={{
                    click: () => onPointSelect && onPointSelect(p)
                  }}
                >
                  <Popup>
                    <div className="p-1 max-w-[200px]">
                      <h4 className="font-bold text-sm text-gray-900">{p.name}</h4>
                      <p className="text-xs text-gray-500 capitalize">Type: {p.type}</p>
                      {p.riskLevel && (
                        <span className="inline-block mt-1 px-2 py-0.5 text-[10px] font-bold rounded bg-red-100 text-red-800">
                          {p.riskLevel}
                        </span>
                      )}
                      {p.details && <p className="text-xs text-gray-600 mt-1">{p.details}</p>}
                    </div>
                  </Popup>
                </CircleMarker>
              );
            })}

            {routeWaypoints && routeWaypoints.length > 1 && (
              <Polyline
                positions={routeWaypoints.map((w) => [w.lat, w.lng])}
                pathOptions={{ color: "#2563eb", weight: 4, dashArray: "6, 8" }}
              />
            )}
          </MapContainer>
        )}
      </div>

      {/* Google Maps API Key Modal */}
      {showKeyModal && (
        <div className="absolute inset-0 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl shadow-2xl p-6 max-w-md w-full border border-gray-200 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2.5 rounded-xl bg-blue-100 text-blue-700">
                <Key size={22} />
              </div>
              <div>
                <h3 className="font-bold text-gray-900 text-base">Google Maps API Integration</h3>
                <p className="text-xs text-gray-500">Real-time Maps JavaScript SDK + Places + Geocoding</p>
              </div>
            </div>

            <p className="text-xs text-gray-600 mb-4 leading-relaxed">
              Enter a valid <b>Google Maps API Key</b> with Maps JavaScript API enabled. The key will be stored securely in your browser's local session and activate satellite views, marker clustering, places search, and routing.
            </p>

            <div className="space-y-3 mb-5">
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">
                  Google Maps API Key
                </label>
                <input
                  type="text"
                  value={tempKeyInput}
                  onChange={(e) => setTempKeyInput(e.target.value)}
                  placeholder="AIzaSy..."
                  className="w-full text-xs font-mono p-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
                />
              </div>

              <div className="text-[11px] text-gray-500 bg-gray-50 p-2.5 rounded-lg border border-gray-200">
                <b>Environment Variable:</b> You can also permanently set <code>VITE_GOOGLE_MAPS_API_KEY</code> in your <code>.env</code> file.
              </div>
            </div>

            <div className="flex items-center justify-end gap-2">
              {apiKey && (
                <button
                  onClick={handleRemoveKey}
                  className="text-xs text-red-600 hover:text-red-700 px-3 py-2 font-semibold"
                >
                  Clear Key
                </button>
              )}
              <button
                onClick={() => setShowKeyModal(false)}
                className="text-xs text-gray-600 hover:bg-gray-100 px-4 py-2 rounded-lg font-medium"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveApiKey}
                className="text-xs bg-blue-600 hover:bg-blue-700 text-white px-5 py-2 rounded-lg font-bold shadow-sm"
              >
                Apply & Connect
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
