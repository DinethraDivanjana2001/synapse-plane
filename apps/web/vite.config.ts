import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev server port matches the API's default CORS_ORIGINS entry
// (http://localhost:3000) so the two work together without .env changes.
export default defineConfig({
  plugins: [react()],
  server: { port: 3000 },
});
