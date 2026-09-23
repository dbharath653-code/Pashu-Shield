import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import "./index.css"
import App from "./App.tsx"
import { installApiAuth } from "./services/apiAuth"

// Attach Bearer tokens / refresh on 401 for every /api request
installApiAuth()

// Register the PWA service worker for offline support
import { registerSW } from "virtual:pwa-register"
registerSW({
  onNeedRefresh() {
    // registerType is "autoUpdate" in vite.config.ts, so the new worker
    // activates on its own; just log for diagnostics.
    console.log("A new version is available and will be applied automatically");
  },
  onOfflineReady() {
    console.log("App is ready to work offline");
  },
  onRegisterError(error) {
    console.error("Service worker registration failed", error);
  },
})

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
