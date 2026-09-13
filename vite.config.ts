import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"
import tailwindcss from "@tailwindcss/vite"
import { VitePWA } from "vite-plugin-pwa"
import fs from "fs"
import path from "path"

export default defineConfig({
  plugins: [
    react(), 
    tailwindcss(),
    VitePWA({
      registerType: "autoUpdate",
      workbox: {
        globPatterns: ["**/*.{js,css,html,ico,png,svg}"],
        maximumFileSizeToCacheInBytes: 10 * 1024 * 1024 // 10MB limit to handle some ML/WASM assets if needed
      },
      manifest: {
        name: "Livestock Health Surveillance",
        short_name: "LivestockHealth",
        description: "Offline-first application for Maharashtra Livestock Health Surveillance",
        theme_color: "#ffffff",
        icons: [
          {
            src: "/favicon.svg",
            sizes: "192x192",
            type: "image/svg+xml"
          }
        ]
      }
    }),
    {
      name: "404-for-models",
      configureServer(server) {
        server.middlewares.use((req, res, next) => {
          if (req.url && (req.url.startsWith("/models/") || req.url.startsWith("/wasm/"))) {
             const filePath = path.join(__dirname, "public", req.url.split("?")[0]);
             if (!fs.existsSync(filePath)) {
               res.statusCode = 404;
               res.end("Not Found");
               return;
             }
          }
          next();
        });
      }
    }
  ],
})
