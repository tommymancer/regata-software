import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";
import path from "path";

export default defineConfig({
  plugins: [svelte()],
  server: {
    port: 5173,
    proxy: {
      "/ws": {
        target: "ws://localhost:8080",
        ws: true,
      },
      "/api": {
        target: "http://localhost:8080",
      },
    },
  },
  build: {
    outDir: path.resolve(__dirname, "../aquarela/static"),
    emptyOutDir: true,
  },
});
