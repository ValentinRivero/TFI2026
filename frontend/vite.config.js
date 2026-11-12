import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

// React y Leaflet van en bloques propios: el mapa se descarga solo al abrirlo y el resto de la app cachea mejor.
const bloqueDe = (id) => {
  if (!id.includes('node_modules')) return undefined;
  if (id.includes('/leaflet/')) return 'leaflet';
  if (/\/(react|react-dom|react-router|react-router-dom|scheduler)\//.test(id)) return 'react';
  return undefined;
};

export default defineConfig({
  plugins: [react()],
  server: { port: 5173, strictPort: true },
  build: {
    rollupOptions: { output: { manualChunks: bloqueDe } },
  },
  test: {
    environment: 'node',
    include: ['src/**/*.test.js'],
  },
});
