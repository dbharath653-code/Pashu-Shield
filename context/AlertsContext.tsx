import React, { createContext, useContext, useState, useEffect } from "react";
import { dbService } from "../services/db/IndexedDBService";

export interface SystemAlert {
  id: string;
  type: string;
  priority: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  disease: string;
  district: string;
  taluka: string;
  village: string;
  affectedAnimals: number;
  suspectedCases: number;
  deaths: number;
  recovered: number;
  vaccinationCoverage: number;
  riskScore: number;
  confidence: number;
  source: string;
  detectedAt: string;
  status: "NEW" | "ACKNOWLEDGED" | "ASSIGNED" | "IN_PROGRESS" | "RESOLVED";
  assignedOfficer?: string;
  escalationLevel: string;
  latitude: number;
  longitude: number;
  read: boolean;
}

interface AlertsContextType {
  alerts: SystemAlert[];
  unreadCount: number;
  markAsRead: (id: string) => Promise<void>;
  markAllAsRead: () => Promise<void>;
  updateAlertStatus: (id: string, status: SystemAlert["status"]) => Promise<void>;
  assignOfficer: (id: string, officerName: string) => Promise<void>;
  refreshAlerts: () => void;
}

const AlertsContext = createContext<AlertsContextType | undefined>(undefined);

export function AlertsProvider({ children }: { children: React.ReactNode }) {
  const [alerts, setAlerts] = useState<SystemAlert[]>([]);
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  useEffect(() => {
    const loadData = async () => {
      await dbService.init();
      const loadedAlerts = await dbService.getAll("alerts");

      // Load server-generated alerts (rule/alert engine). No fabricated alerts are seeded;
      // an empty list is shown as empty. Cached alerts remain available offline.
      try {
        const res = await fetch("/api/v1/alerts?limit=100");
        if (res.ok) {
          const serverAlerts: any[] = await res.json();
          const sevToPriority: Record<string, SystemAlert["priority"]> = { critical: "CRITICAL", high: "HIGH", warning: "MEDIUM", medium: "MEDIUM", info: "LOW", low: "LOW" };
          for (const a of serverAlerts) {
            const mapped: SystemAlert = {
              id: a.id, type: a.alertType || a.type || "ALERT",
              priority: sevToPriority[String(a.severity || "").toLowerCase()] || "MEDIUM",
              disease: a.disease || "", district: a.district || "", taluka: "", village: "",
              affectedAnimals: 0, suspectedCases: a.occurrences || 0, deaths: 0, recovered: 0,
              vaccinationCoverage: 0, riskScore: 0, confidence: 0,
              source: `${a.isDemo ? "DEMO · " : ""}Server alert engine (${a.evidenceLevel || "UNVERIFIED"})`,
              detectedAt: a.createdAt, status: "NEW", escalationLevel: "None",
              latitude: NaN, longitude: NaN, read: !!a.read,
            };
            const existing = loadedAlerts.find((l: SystemAlert) => l.id === mapped.id);
            await dbService.save("alerts", existing ? { ...mapped, status: existing.status, assignedOfficer: existing.assignedOfficer, read: existing.read || mapped.read } : mapped);
          }
        }
      } catch {
        // offline: fall through to the cached alerts
      }
      const cached = (await dbService.getAll("alerts")) as SystemAlert[];
      // Drop legacy fabricated sample alerts from older app versions.
      const legacy = cached.filter((a) => /^ALT-2026-00\d$/.test(a.id));
      for (const a of legacy) await dbService.delete("alerts", a.id);
      const real = cached.filter((a) => !/^ALT-2026-00\d$/.test(a.id));
      if (real.length === 0) {
        setAlerts([]);
      } else {
        setAlerts(real.sort((a, b) => new Date(b.detectedAt).getTime() - new Date(a.detectedAt).getTime()));
      }
    };
    loadData();
  }, [refreshTrigger]);

  const markAsRead = async (id: string) => {
    const target = alerts.find(a => a.id === id);
    if (target && !target.read) {
      target.read = true;
      await dbService.save("alerts", target);
      setAlerts(alerts.map(a => a.id === id ? target : a));
    }
  };

  const markAllAsRead = async () => {
    const updated = alerts.map(a => ({ ...a, read: true }));
    for (const a of updated) {
      await dbService.save("alerts", a);
    }
    setAlerts(updated);
  };

  const updateAlertStatus = async (id: string, status: SystemAlert["status"]) => {
    const target = alerts.find(a => a.id === id);
    if (target) {
      target.status = status;
      await dbService.save("alerts", target);
      setAlerts(alerts.map(a => a.id === id ? target : a));
    }
  };

  const assignOfficer = async (id: string, officerName: string) => {
    const target = alerts.find(a => a.id === id);
    if (target) {
      target.assignedOfficer = officerName;
      target.status = "ASSIGNED";
      await dbService.save("alerts", target);
      setAlerts(alerts.map(a => a.id === id ? target : a));
    }
  };

  const refreshAlerts = () => {
    setRefreshTrigger(prev => prev + 1);
  };

  const unreadCount = alerts.filter(a => !a.read).length;

  return (
    <AlertsContext.Provider value={{ alerts, unreadCount, markAsRead, markAllAsRead, updateAlertStatus, assignOfficer, refreshAlerts }}>
      {children}
    </AlertsContext.Provider>
  );
}

export function useAlerts() {
  const context = useContext(AlertsContext);
  if (context === undefined) throw new Error("useAlerts must be used within Provider");
  return context;
}

