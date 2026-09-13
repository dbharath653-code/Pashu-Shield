import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import "./index.css"
import App from "./App.tsx"

// Register the PWA service worker for offline support
import { registerSW } from "virtual:pwa-register"
const updateSW = registerSW({
  onNeedRefresh() {
    // optional: show a prompt to user to refresh
  },
  onOfflineReady() {
    console.log("App is ready to work offline");
  },
})

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
