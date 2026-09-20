import React from "react";
import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom";
import { AppProvider } from "./context/AppContext";
import { AlertsProvider } from "./context/AlertsContext";
import { MultilingualProvider } from "./context/MultilingualContext";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { SyncProvider } from "./services/SyncService";

import Layout from "./components/Layout";
import ErrorBoundary from "./components/ErrorBoundary";

// Core Pages
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

// Dedicated Separate Auth Portals & Pages
import LoginPortal from "./pages/Auth/LoginPortal";
import FarmerLogin from "./pages/Auth/FarmerLogin";
import FarmerSignup from "./pages/Auth/FarmerSignup";
import VetLogin from "./pages/Auth/VetLogin";
import VetSignup from "./pages/Auth/VetSignup";
import LabLogin from "./pages/Auth/LabLogin";
import LabSignup from "./pages/Auth/LabSignup";
import GovernmentLogin from "./pages/Auth/GovernmentLogin";
import GovernmentSignup from "./pages/Auth/GovernmentSignup";
import SignupPortal from "./pages/Auth/SignupPortal";

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
            <SyncProvider>
              <BrowserRouter>
                <Routes>
                  {/* Dedicated Separate Login & Sign-up Pages */}
                  <Route path="/login" element={<RouteErrorBoundary><LoginPortal /></RouteErrorBoundary>} />
                  <Route path="/login/farmer" element={<RouteErrorBoundary><FarmerLogin /></RouteErrorBoundary>} />
                  <Route path="/login/veterinary" element={<RouteErrorBoundary><VetLogin /></RouteErrorBoundary>} />
                  <Route path="/login/vet" element={<RouteErrorBoundary><VetLogin /></RouteErrorBoundary>} />
                  <Route path="/login/laboratory" element={<RouteErrorBoundary><LabLogin /></RouteErrorBoundary>} />
                  <Route path="/login/lab" element={<RouteErrorBoundary><LabLogin /></RouteErrorBoundary>} />
                  <Route path="/login/government" element={<RouteErrorBoundary><GovernmentLogin /></RouteErrorBoundary>} />
                  <Route path="/login/admin" element={<RouteErrorBoundary><GovernmentLogin /></RouteErrorBoundary>} />

                  <Route path="/signup" element={<RouteErrorBoundary><SignupPortal /></RouteErrorBoundary>} />
                  <Route path="/signup/farmer" element={<RouteErrorBoundary><FarmerSignup /></RouteErrorBoundary>} />
                  <Route path="/signup/veterinary" element={<RouteErrorBoundary><VetSignup /></RouteErrorBoundary>} />
                  <Route path="/signup/vet" element={<RouteErrorBoundary><VetSignup /></RouteErrorBoundary>} />
                  <Route path="/signup/laboratory" element={<RouteErrorBoundary><LabSignup /></RouteErrorBoundary>} />
                  <Route path="/signup/lab" element={<RouteErrorBoundary><LabSignup /></RouteErrorBoundary>} />
                  <Route path="/signup/government" element={<RouteErrorBoundary><GovernmentSignup /></RouteErrorBoundary>} />
                  <Route path="/signup/admin" element={<RouteErrorBoundary><GovernmentSignup /></RouteErrorBoundary>} />

                  {/* Main Authenticated Application Layout */}
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
            </SyncProvider>
          </AlertsProvider>
        </AppProvider>
      </AuthProvider>
    </MultilingualProvider>
  );
}

export default App;
