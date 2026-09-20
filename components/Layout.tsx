import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import Topbar from "./Topbar";
import PersistentVoiceAssistant from "./PersistentVoiceAssistant";

export default function Layout() {
  return (
    <div className="flex min-h-screen bg-bgLight antialiased font-sans">
      <Sidebar />
      <div className="flex-1 ml-64 flex flex-col h-screen overflow-hidden">
        <Topbar />
        <main className="flex-1 overflow-auto p-4 lg:p-6 relative">
          <Outlet />
        </main>
      </div>
      <PersistentVoiceAssistant />
    </div>
  );
}
