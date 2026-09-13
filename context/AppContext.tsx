import React, { createContext, useContext, useState, useMemo } from 'react';

// Define Types
export interface Report {
  id: string;
  date: string;
  species: string;
  numberAffected: number;
  numberDead: number;
  district: string;
  village: string;
  symptoms: string[];
  status: 'Suspected' | 'Confirmed' | 'Under Review' | 'Resolved';
  disease: string;
}

export interface Alert {
  id: string;
  time: string;
  title: string;
  type: 'high' | 'warning' | 'success';
}

interface AppContextType {
  reports: Report[];
  alerts: Alert[];
  addReport: (report: Omit<Report, 'id'>) => void;
  totalPopulation: number;
  vaccinationCoverage: number;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export function AppProvider({ children }: { children: React.ReactNode }) {
  // Initial Mock Data to seed the "database"
  const [reports, setReports] = useState<Report[]>([
    { id: '1', date: '2025-04-15', species: 'Cattle', numberAffected: 12, numberDead: 1, district: 'Pune', village: 'Walwur', symptoms: ['Fever', 'Skin lesions'], status: 'Suspected', disease: 'LSD' },
    { id: '2', date: '2025-04-14', species: 'Buffalo', numberAffected: 8, numberDead: 0, district: 'Pune', village: 'Shirur', symptoms: ['Fever'], status: 'Suspected', disease: 'FMD' },
    { id: '3', date: '2025-04-14', species: 'Cattle', numberAffected: 5, numberDead: 0, district: 'Satara', village: 'Khed', symptoms: ['Reduced appetite'], status: 'Under Review', disease: 'Brucellosis' },
    { id: '4', date: '2025-04-13', species: 'Goat', numberAffected: 7, numberDead: 2, district: 'Satara', village: 'Mhaswad', symptoms: ['Fever'], status: 'Suspected', disease: 'PPR' },
    { id: '5', date: '2025-04-11', species: 'Cattle', numberAffected: 10, numberDead: 0, district: 'Nanded', village: 'Nandur', symptoms: ['Fever'], status: 'Confirmed', disease: 'BND' },
  ]);

  const [alerts, setAlerts] = useState<Alert[]>([
    { id: '1', time: '15 Apr 2025 - 10:14 AM', title: 'High Risk - Pune - FMD', type: 'high' },
    { id: '2', time: '14 Apr 2025 - 08:15 PM', title: 'FMD Suspected - Satara', type: 'warning' },
    { id: '3', time: '13 Apr 2025 - 11:32 AM', title: 'Brucellosis - Nagpur', type: 'warning' },
    { id: '4', time: '12 Apr 2025 - 04:20 PM', title: 'Foot and Mouth Disease - Aurangabad', type: 'success' },
  ]);

  const totalPopulation = 1248320; // Base population
  const vaccinationCoverage = 24; // Base coverage %

  const addReport = (reportData: Omit<Report, 'id'>) => {
    const newReport = {
      ...reportData,
      id: Math.random().toString(36).substring(2, 9),
    };
    setReports(prev => [newReport, ...prev]);
    
    // Automatically generate an alert if it's high severity
    if (reportData.numberDead > 0 || reportData.numberAffected > 10) {
      setAlerts(prev => [
        {
          id: Math.random().toString(36).substring(2, 9),
          time: new Date().toLocaleString(),
          title: `High Risk - ${reportData.district} - ${reportData.disease || 'Unknown'}`,
          type: 'high'
        },
        ...prev
      ]);
    }
  };

  return (
    <AppContext.Provider value={{
      reports,
      alerts,
      addReport,
      totalPopulation,
      vaccinationCoverage
    }}>
      {children}
    </AppContext.Provider>
  );
}

export function useAppContext() {
  const context = useContext(AppContext);
  if (context === undefined) {
    throw new Error('useAppContext must be used within an AppProvider');
  }
  return context;
}
