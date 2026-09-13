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

      if (loadedAlerts.length === 0) {
        const mockAlerts: SystemAlert[] = [
          {
            id: "ALT-2026-001",
            type: "OUTBREAK",
            priority: "CRITICAL",
            disease: "Foot-and-Mouth Disease",
            district: "Pune",
            taluka: "Shirur",
            village: "Example Village",
            affectedAnimals: 47,
            suspectedCases: 18,
            deaths: 2,
            recovered: 0,
            vaccinationCoverage: 42,
            riskScore: 94,
            confidence: 91,
            source: "AI Early Warning + Field Reports",
            detectedAt: new Date(Date.now() - 3600000 * 2).toISOString(),
            status: "NEW",
            escalationLevel: "Taluka Officer",
            latitude: 18.826,
            longitude: 74.376,
            read: false,
          },
          {
            id: "ALT-2026-002",
            type: "CLUSTER",
            priority: "HIGH",
            disease: "Lumpy Skin Disease",
            district: "Nashik",
            taluka: "Sinnar",
            village: "Pimplad",
            affectedAnimals: 31,
            suspectedCases: 12,
            deaths: 0,
            recovered: 4,
            vaccinationCoverage: 68,
            riskScore: 82,
            confidence: 85,
            source: "Routine Surveillance",
            detectedAt: new Date(Date.now() - 3600000 * 12).toISOString(),
            status: "ACKNOWLEDGED",
            escalationLevel: "None",
            latitude: 19.845,
            longitude: 73.998,
            read: true,
          },
          {
            id: "ALT-2026-003",
            type: "VACCINATION_GAP",
            priority: "MEDIUM",
            disease: "PPR",
            district: "Nagpur",
            taluka: "Katol",
            village: "Dorli",
            affectedAnimals: 200,
            suspectedCases: 0,
            deaths: 0,
            recovered: 0,
            vaccinationCoverage: 31,
            riskScore: 57,
            confidence: 75,
            source: "Analytics Engine",
            detectedAt: new Date(Date.now() - 86400000).toISOString(),
            status: "NEW",
            escalationLevel: "None",
            latitude: 21.272,
            longitude: 78.586,
            read: false,
          }
        ];
        for (const a of mockAlerts) {
          await dbService.save("alerts", a);
        }
        setAlerts(mockAlerts);
      } else {
        setAlerts(loadedAlerts.sort((a, b) => new Date(b.detectedAt).getTime() - new Date(a.detectedAt).getTime()));
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

