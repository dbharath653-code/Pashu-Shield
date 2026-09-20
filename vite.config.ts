import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"
import tailwindcss from "@tailwindcss/vite"
import { VitePWA } from "vite-plugin-pwa"
import fs from "fs"
import path from "path"

// Where the optional FastAPI service (ml-backend/) listens during development.
const ML_BACKEND = process.env.ML_BACKEND_URL || "http://127.0.0.1:8000"

// Set VITE_BASE_PATH when the app is hosted under a sub-path (e.g. GitHub Pages:
// VITE_BASE_PATH=/Pashu-Shield/ npm run build).
const base = process.env.VITE_BASE_PATH || "/"

export default defineConfig({
  base,
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: "autoUpdate",
      workbox: {
        globPatterns: ["**/*.{js,css,html,ico,png,svg,webmanifest}"],
        maximumFileSizeToCacheInBytes: 10 * 1024 * 1024, // 10MB limit to handle some ML/WASM assets if needed
        // Large ML assets are not precached (beyond the 10MB cap); they are cached
        // on first use so the offline features keep working after the initial load.
        runtimeCaching: [
          {
            // Path suffixes keep the patterns valid when the app is served from a
            // sub-path (VITE_BASE_PATH), where URLs are prefixed (e.g. /Pashu-Shield/models/…).
            urlPattern: ({ url }) =>
              ["/model_weights.json", "/symptomDictionary.json", "/maharashtra_locations.json", "/maharashtra_state.geojson"].some((name) => url.pathname.endsWith(name)) ||
              url.pathname.includes("/models/") ||
              url.pathname.includes("/wasm/"),
            handler: "CacheFirst",
            options: {
              cacheName: "ml-assets",
              expiration: { maxEntries: 40, maxAgeSeconds: 60 * 60 * 24 * 30 },
              cacheableResponse: { statuses: [0, 200] },
            },
          },
          {
            // Reference/district data used by the GIS screens.
            urlPattern: ({ url }) => url.pathname.endsWith(".geojson"),
            handler: "StaleWhileRevalidate",
            options: {
              cacheName: "reference-data",
              expiration: { maxEntries: 30, maxAgeSeconds: 60 * 60 * 24 * 7 },
              cacheableResponse: { statuses: [0, 200] },
            },
          },
          {
            // Base map tiles, so the maps keep rendering offline.
            urlPattern: /^https:\/\/[abc]?\.?tile\.openstreetmap\.org\/.*/i,
            handler: "CacheFirst",
            options: {
              cacheName: "osm-tiles",
              expiration: { maxEntries: 500, maxAgeSeconds: 60 * 60 * 24 * 14 },
              cacheableResponse: { statuses: [0, 200] },
            },
          },
          {
            // Optional FastAPI ML service: serve the last good response when offline.
            urlPattern: ({ url }) => url.pathname.includes("/api/"),
            handler: "NetworkFirst",
            options: {
              cacheName: "ml-api",
              networkTimeoutSeconds: 5,
              expiration: { maxEntries: 50, maxAgeSeconds: 60 * 60 * 24 },
              cacheableResponse: { statuses: [0, 200] },
            },
          },
        ],
      },
      manifest: {
        name: "Livestock Health Surveillance",
        short_name: "LivestockHealth",
        description: "Offline-first application for Maharashtra Livestock Health Surveillance",
        theme_color: "#ffffff",
        background_color: "#ffffff",
        display: "standalone",
        start_url: ".",
        scope: ".",
        icons: [
          {
            src: "icons/icon-192.png",
            sizes: "192x192",
            type: "image/png",
            purpose: "any"
          },
          {
            src: "icons/icon-512.png",
            sizes: "512x512",
            type: "image/png",
            purpose: "any"
          },
          {
            src: "icons/icon-512.png",
            sizes: "512x512",
            type: "image/png",
            purpose: "maskable"
          },
          {
            src: "favicon.svg",
            sizes: "any",
            type: "image/svg+xml",
            purpose: "any"
          }
        ]
      }
    }),
    {
      name: "dev-missing-asset-404",
      configureServer(server) {
        server.middlewares.use((req, res, next) => {
          if (req.url && (req.url.startsWith("/models/") || req.url.startsWith("/wasm/"))) {
             const filePath = path.join(import.meta.dirname, "public", req.url.split("?")[0]);
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
  server: {
    host: true,
    // Preview environments proxy the dev server through their own hostname.
    allowedHosts: true,
    proxy: {
      // Front-end calls "/api/..." – forward to the FastAPI service when it is running.
      "/api": {
        target: ML_BACKEND,
        changeOrigin: true,
        ws: true,
      },
      "/ws": {
        target: ML_BACKEND,
        changeOrigin: true,
        ws: true,
      },
    },
  },
  preview: {
    host: true,
    allowedHosts: true,
    proxy: {
      "/api": {
        target: ML_BACKEND,
        changeOrigin: true,
      },
    },
  },
})
