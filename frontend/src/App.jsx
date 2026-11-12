import { lazy, Suspense } from 'react';
import { Outlet, Route, Routes } from 'react-router-dom';
import AceptarPolitica from './components/AceptarPolitica.jsx';
import Cargando from './components/Cargando.jsx';
import Layout from './components/Layout.jsx';
import PantallaEstado from './components/PantallaEstado.jsx';
import ProtectedRoute from './components/ProtectedRoute.jsx';
import ScrollAlInicio from './components/ScrollAlInicio.jsx';
import { t } from './i18n/index.js';
import Catalogo from './pages/Catalogo.jsx';
import Login from './pages/Login.jsx';
import Privacidad from './pages/Privacidad.jsx';
import Registro from './pages/Registro.jsx';

const ComplejoDetalle = lazy(() => import('./pages/ComplejoDetalle.jsx'));
const LayoutPanel = lazy(() => import('./components/LayoutPanel.jsx'));
const PanelComplejo = lazy(() => import('./pages/PanelComplejo.jsx'));
const GestionCanchas = lazy(() => import('./pages/GestionCanchas.jsx'));
const GestionExcepciones = lazy(() => import('./pages/GestionExcepciones.jsx'));
const Agenda = lazy(() => import('./pages/Agenda.jsx'));
const Reportes = lazy(() => import('./pages/Reportes.jsx'));
const LayoutSistema = lazy(() => import('./components/LayoutSistema.jsx'));
const PanelSistema = lazy(() => import('./pages/PanelSistema.jsx'));
const Contratos = lazy(() => import('./pages/Contratos.jsx'));
const Auditoria = lazy(() => import('./pages/Auditoria.jsx'));
const MisReservas = lazy(() => import('./pages/MisReservas.jsx'));
const Perfil = lazy(() => import('./pages/Perfil.jsx'));
const Provisoria = lazy(() => import('./pages/Provisoria.jsx'));

// La guía visual es una herramienta de desarrollo: en el build de producción esta constante es `null` y el
// bloque de la guía no se incluye. No figura en la navegación: en desarrollo se abre escribiendo `/guia`.
const GuiaVisual = import.meta.env.DEV ? lazy(() => import('./pages/GuiaVisual.jsx')) : null;

function NoEncontrada() {
  return (
    <PantallaEstado
      icono="buscar"
      titulo={t('paginaNoEncontrada.titulo')}
      descripcion={t('paginaNoEncontrada.descripcion')}
    />
  );
}

function PlantillaPublica() {
  return (
    <Layout>
      <Outlet />
    </Layout>
  );
}

function PlantillaPanel() {
  return (
    <Layout ancho="panel" claveCarga="panel">
      <Outlet />
    </Layout>
  );
}

// Pantallas privadas todavía provisorias: cada una se reemplaza por su página definitiva en su subfase.
const PRIVADAS = [
  { ruta: '/notificaciones', seccion: 'notificaciones', titulo: t('navegacion.notificaciones') },
];

export default function App() {
  return (
    <Suspense fallback={<Cargando variante="pantalla" texto={t('comun.cargandoPantalla')} />}>
      <AceptarPolitica />
      <ScrollAlInicio />
      <Routes>
        <Route element={<PlantillaPublica />}>
          <Route path="/" element={<Catalogo />} />
          <Route path="/complejos/:id" element={<ComplejoDetalle />} />
          <Route path="/login" element={<Login />} />
          <Route path="/registro" element={<Registro />} />
          <Route path="/privacidad" element={<Privacidad />} />
          <Route
            path="/mis-reservas"
            element={<ProtectedRoute seccion="misReservas"><MisReservas /></ProtectedRoute>}
          />
          <Route path="/perfil" element={<ProtectedRoute seccion="perfil"><Perfil /></ProtectedRoute>} />
          {GuiaVisual && <Route path="/guia" element={<GuiaVisual />} />}
          {PRIVADAS.map(({ ruta, seccion, titulo }) => (
            <Route
              key={ruta}
              path={ruta}
              element={<ProtectedRoute seccion={seccion}><Provisoria titulo={titulo} /></ProtectedRoute>}
            />
          ))}
          <Route path="*" element={<NoEncontrada />} />
        </Route>
        <Route element={<PlantillaPanel />}>
          <Route path="/panel" element={<ProtectedRoute seccion="panel"><LayoutPanel /></ProtectedRoute>}>
            <Route index element={<PanelComplejo />} />
            <Route path="canchas" element={<GestionCanchas />} />
            <Route path="excepciones" element={<GestionExcepciones />} />
            <Route path="agenda" element={<ProtectedRoute seccion="agenda"><Agenda /></ProtectedRoute>} />
            <Route path="reportes" element={<ProtectedRoute seccion="reportes"><Reportes /></ProtectedRoute>} />
          </Route>
          <Route path="/sistema" element={<ProtectedRoute seccion="sistema"><LayoutSistema /></ProtectedRoute>}>
            <Route index element={<PanelSistema />} />
            <Route path="contratos" element={<Contratos />} />
            <Route path="auditoria" element={<Auditoria />} />
          </Route>
        </Route>
      </Routes>
    </Suspense>
  );
}
