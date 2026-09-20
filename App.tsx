import React from "react";
import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom";
import { AppProvider } from "./context/AppContext";
import { AlertsProvider } from "./context/AlertsContext";
import { MultilingualProvider } from "./context/MultilingualContext";
import { AuthProvider, useAuth } from "./context/AuthContext";

import Layout from "./components/Layout";
import ErrorBoundary from "./components/ErrorBoundary";

// Pages
import Dashboard from "./pages/Dashboard";
import FarmerDashboard from "./pages/FarmerDashboard";
import DiseaseSurveillance from "./pages/DiseaseSurveillance";
import GisRiskMap from "./pages/GisRiskMap";
import AIEarlyWarning from "./pages/AIEarlyWarning";
import CaseReporting from "./pages/CaseReporting";
import AnimalHealth from "./pages/AnimalHealth/AnimalHealth";
import VetResponse from "./pages/VetResponse/VetResponse";
import LabManagement from "./pages/LabManagement/LabManagement";
import VaccinationManagement from "./pages/VaccinationManagement/VaccinationManagement";
import AlertsManagement from "./pages/AlertsNotifications/AlertsManagement";
import MultilingualManagement from "./pages/Multilingual/MultilingualManagement";
import OfflineSync from "./pages/OfflineSync/OfflineSync";
import DiseaseInfo from "./pages/DiseaseInfo/DiseaseInfo";
import AnalyticsManagement from "./pages/Analytics/AnalyticsManagement";
import AdminManagement from "./pages/Administration/AdminManagement";

function RouteErrorBoundary({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  return <ErrorBoundary key={location.pathname}>{children}</ErrorBoundary>;
}

function RoleBasedHome() {
  const { role } = useAuth();
  if (role === "FARMER") {
    return <FarmerDashboard />;
  }
  return <Dashboard />;
}

function App() {
  return (
    <MultilingualProvider>
      <AuthProvider>
        <AppProvider>
          <AlertsProvider>
            <BrowserRouter>
              <Routes>
                <Route path="/" element={<Layout />}>
                  <Route index element={<RouteErrorBoundary><RoleBasedHome /></RouteErrorBoundary>} />
                  <Route path="farmer" element={<RouteErrorBoundary><FarmerDashboard /></RouteErrorBoundary>} />
                  <Route path="surveillance" element={<RouteErrorBoundary><DiseaseSurveillance /></RouteErrorBoundary>} />
                  <Route path="gis" element={<RouteErrorBoundary><GisRiskMap /></RouteErrorBoundary>} />
                  <Route path="ai" element={<RouteErrorBoundary><AIEarlyWarning /></RouteErrorBoundary>} />
                  <Route path="reporting" element={<RouteErrorBoundary><CaseReporting /></RouteErrorBoundary>} />
                  <Route path="animal-health" element={<RouteErrorBoundary><AnimalHealth /></RouteErrorBoundary>} />
                  <Route path="vet-response" element={<RouteErrorBoundary><VetResponse /></RouteErrorBoundary>} />
                  <Route path="lab" element={<RouteErrorBoundary><LabManagement /></RouteErrorBoundary>} />
                  <Route path="vaccination" element={<RouteErrorBoundary><VaccinationManagement /></RouteErrorBoundary>} />
                  <Route path="alerts" element={<RouteErrorBoundary><AlertsManagement /></RouteErrorBoundary>} />
                  <Route path="multilingual" element={<RouteErrorBoundary><MultilingualManagement /></RouteErrorBoundary>} />
                  <Route path="offline" element={<RouteErrorBoundary><OfflineSync /></RouteErrorBoundary>} />
                  <Route path="disease-info" element={<RouteErrorBoundary><DiseaseInfo /></RouteErrorBoundary>} />
                  <Route path="analytics" element={<RouteErrorBoundary><AnalyticsManagement /></RouteErrorBoundary>} />
                  <Route path="admin" element={<RouteErrorBoundary><AdminManagement /></RouteErrorBoundary>} />
                  <Route path="*" element={<RouteErrorBoundary><RoleBasedHome /></RouteErrorBoundary>} />
                </Route>
              </Routes>
            </BrowserRouter>
          </AlertsProvider>
        </AppProvider>
      </AuthProvider>
    </MultilingualProvider>
  );
}

export default App;
