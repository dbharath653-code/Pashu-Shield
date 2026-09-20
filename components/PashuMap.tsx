import { useEffect, useRef, useState } from "react";
import { MapContainer, TileLayer, CircleMarker, Popup, Polyline } from "react-leaflet";
import "leaflet/dist/leaflet.css";

export interface MapPoint {
  id: string;
  name: string;
  lat: number;
  lng: number;
  type: "cluster" | "facility" | "lab" | "report" | "vet";
  riskLevel?: "High Risk" | "Moderate Risk" | "Low Risk" | "Critical";
  details?: string;
}

interface PashuMapProps {
  center?: [number, number];
  zoom?: number;
  points?: MapPoint[];
  routeWaypoints?: { lat: number; lng: number }[];
  height?: string;
  onPointSelect?: (point: MapPoint) => void;
}

export default function PashuMap({
  center = [18.8288, 74.3789], // Default Maharashtra / Pune Shirur cluster
  zoom = 10,
  points = [],
  routeWaypoints = [],
  height = "450px",
  onPointSelect
}: PashuMapProps) {
  const googleMapRef = useRef<HTMLDivElement>(null);
  const [googleMapLoaded, setGoogleMapLoaded] = useState(false);
  const [googleMapError, setGoogleMapError] = useState(false);
  const googleMapInstance = useRef<any>(null);

  const googleApiKey = import.meta.env?.VITE_GOOGLE_MAPS_API_KEY as string | undefined;

  useEffect(() => {
    if (!googleApiKey || googleApiKey.trim() === "") {
      setGoogleMapError(true);
      return;
    }

    // Load Google Maps script if not already present
    if ((window as any).google && (window as any).google.maps) {
      setGoogleMapLoaded(true);
      return;
    }

    const script = document.createElement("script");
    script.src = `https://maps.googleapis.com/maps/api/js?key=${googleApiKey}&libraries=geometry`;
    script.async = true;
    script.defer = true;
    script.onload = () => setGoogleMapLoaded(true);
    script.onerror = () => setGoogleMapError(true);
    document.head.appendChild(script);
  }, [googleApiKey]);

  // Initialize Google Maps instance
  useEffect(() => {
    if (googleMapLoaded && googleMapRef.current && (window as any).google) {
      try {
        const g = (window as any).google.maps;
        const map = new g.Map(googleMapRef.current, {
          center: { lat: center[0], lng: center[1] },
          zoom: zoom,
          mapTypeId: "roadmap",
          mapTypeControl: false,
          streetViewControl: false
        });
        googleMapInstance.current = map;

        // Render markers
        points.forEach((p) => {
          const markerColor =
            p.riskLevel === "Critical" || p.riskLevel === "High Risk"
              ? "#dc2626"
              : p.type === "facility"
              ? "#2563eb"
              : p.type === "lab"
              ? "#7c3aed"
              : "#16a34a";

          const marker = new g.Marker({
            position: { lat: p.lat, lng: p.lng },
            map: map,
            title: p.name
          });

          const infoWindow = new g.InfoWindow({
            content: `
              <div style="padding: 8px; font-family: sans-serif;">
                <h4 style="font-weight: bold; margin: 0 0 4px 0; font-size: 14px;">${p.name}</h4>
                <p style="margin: 0; font-size: 12px; color: #4b5563;">Type: ${p.type}</p>
                ${p.riskLevel ? `<p style="margin: 4px 0 0 0; font-size: 12px; font-weight: bold; color: ${markerColor}">Risk: ${p.riskLevel}</p>` : ""}
                ${p.details ? `<p style="margin: 4px 0 0 0; font-size: 11px; color: #6b7280;">${p.details}</p>` : ""}
              </div>
            `
          });

          marker.addListener("click", () => {
            infoWindow.open(map, marker);
            if (onPointSelect) onPointSelect(p);
          });
        });

        // Render route line if provided
        if (routeWaypoints && routeWaypoints.length > 1) {
          const path = routeWaypoints.map((w) => ({ lat: w.lat, lng: w.lng }));
          new g.Polyline({
            path: path,
            geodesic: true,
            strokeColor: "#2563eb",
            strokeOpacity: 0.8,
            strokeWeight: 4,
            map: map
          });
        }
      } catch (err) {
        console.warn("Failed initializing Google Maps:", err);
        setGoogleMapError(true);
      }
    }
  }, [googleMapLoaded, points, center, zoom, routeWaypoints]);

  // Leaflet Fallback if Google Maps is not configured or failed
  const showGoogle = googleMapLoaded && !googleMapError;

  return (
    <div className="relative rounded-xl overflow-hidden border border-gray-200 shadow-sm" style={{ height }}>
      {/* Map Header Status Badge */}
      <div className="absolute top-3 right-3 z-[1000] bg-white/90 backdrop-blur px-3 py-1.5 rounded-lg border border-gray-200 shadow text-xs font-semibold flex items-center gap-2">
        <span className={`w-2 h-2 rounded-full ${showGoogle ? "bg-emerald-500 animate-pulse" : "bg-blue-500"}`}></span>
        <span>{showGoogle ? "Google Maps (Active)" : "Standard GIS Map (Leaflet)"}</span>
      </div>

      {showGoogle ? (
        <div ref={googleMapRef} className="w-full h-full" />
      ) : (
        <MapContainer center={center} zoom={zoom} style={{ height: "100%", width: "100%" }} scrollWheelZoom={false}>
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
                  fillOpacity: 0.7,
                  color: "#ffffff",
                  weight: 2
                }}
                eventHandlers={{
                  click: () => onPointSelect && onPointSelect(p)
                }}
              >
                <Popup>
                  <div className="p-1">
                    <h4 className="font-bold text-sm text-gray-900">{p.name}</h4>
                    <p className="text-xs text-gray-500 capitalize">Type: {p.type}</p>
                    {p.riskLevel && (
                      <span className="inline-block mt-1 px-2 py-0.5 text-[11px] font-bold rounded bg-red-100 text-red-800">
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
  );
}
