import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AppProvider } from './context/AppContext';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import DiseaseSurveillance from './pages/DiseaseSurveillance';
import GisRiskMap from './pages/GisRiskMap';
import AIEarlyWarning from './pages/AIEarlyWarning';
import CaseReporting from './pages/CaseReporting';
import AnimalHealth from './pages/AnimalHealth/AnimalHealth';
import VetResponse from './pages/VetResponse/VetResponse';
import LabManagement from './pages/LabManagement/LabManagement';
import VaccinationManagement from './pages/VaccinationManagement/VaccinationManagement';
import AlertsManagement from './pages/AlertsNotifications/AlertsManagement';
import MultilingualManagement from './pages/Multilingual/MultilingualManagement';
import OfflineSync from './pages/OfflineSync/OfflineSync';
import DiseaseInfo from './pages/DiseaseInfo/DiseaseInfo';
import AnalyticsManagement from './pages/Analytics/AnalyticsManagement';
import AdminManagement from './pages/Administration/AdminManagement';

function Placeholder({ title }: { title: string }) {
  return (
    <div className="flex items-center justify-center h-full bg-white rounded-xl shadow-sm border border-gray-100">
      <h2 className="text-2xl font-semibold text-gray-400">{title} Component (Coming Soon)</h2>
    </div>
  );
}

import { AlertsProvider } from './context/AlertsContext';
import { MultilingualProvider } from './context/MultilingualContext';

function App() {
  return (
    <MultilingualProvider>
    <AppProvider>
      <AlertsProvider>
        <BrowserRouter>
          <Routes>
          <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="surveillance" element={<DiseaseSurveillance />} />
          <Route path="gis" element={<GisRiskMap />} />
          <Route path="ai" element={<AIEarlyWarning />} />
          <Route path="reporting" element={<CaseReporting />} />
          <Route path="animal-health" element={<AnimalHealth />} />
          <Route path="vet-response" element={<VetResponse />} />
          <Route path="lab" element={<LabManagement />} />
          <Route path="vaccination" element={<VaccinationManagement />} />
          <Route path="alerts" element={<AlertsManagement />} />
          <Route path="multilingual" element={<MultilingualManagement />} />
          <Route path="offline" element={<OfflineSync />} />
          <Route path="disease-info" element={<DiseaseInfo />} />
          <Route path="analytics" element={<AnalyticsManagement />} />
          <Route path="admin" element={<AdminManagement />} />
        </Route>
        </Routes>
      </BrowserRouter>
      </AlertsProvider>
    </AppProvider>
    </MultilingualProvider>
  );
}

export default App;
