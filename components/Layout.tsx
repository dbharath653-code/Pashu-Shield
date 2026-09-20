import { useState, useEffect } from "react";
import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import Topbar from "./Topbar";
import PersistentVoiceAssistant from "./PersistentVoiceAssistant";
import SyncModal from "./SyncModal";

export default function Layout() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Close mobile drawer on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setMobileMenuOpen(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  // Prevent background scroll when mobile drawer is open
  useEffect(() => {
    if (mobileMenuOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [mobileMenuOpen]);

  return (
    <div className="flex min-h-screen bg-bgLight antialiased font-sans text-gray-900">
      {/* Desktop Persistent Sidebar */}
      <aside className="hidden lg:block fixed left-0 top-0 h-screen w-64 z-30">
        <Sidebar />
      </aside>

      {/* Mobile Drawer Navigation with Slide-in and Backdrop Overlay */}
      {mobileMenuOpen && (
        <div className="lg:hidden fixed inset-0 z-50 flex">
          {/* Backdrop overlay */}
          <div
            className="fixed inset-0 bg-black/60 backdrop-blur-xs transition-opacity animate-in fade-in duration-200"
            onClick={() => setMobileMenuOpen(false)}
            aria-hidden="true"
          />

          {/* Slide-in drawer */}
          <div className="relative flex-1 flex flex-col max-w-xs w-full bg-sidebar z-10 shadow-2xl animate-in slide-in-from-left duration-200">
            <Sidebar isMobile onClose={() => setMobileMenuOpen(false)} />
          </div>
        </div>
      )}

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 h-screen overflow-hidden lg:pl-64">
        <Topbar onOpenMobileMenu={() => setMobileMenuOpen(true)} />
        <main className="flex-1 overflow-y-auto overflow-x-hidden p-3 sm:p-4 lg:p-6 relative">
          <Outlet />
        </main>
      </div>

      {/* Shared Modals and Assistants */}
      <SyncModal />
      <PersistentVoiceAssistant />
    </div>
  );
}
