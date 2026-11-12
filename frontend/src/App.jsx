import { lazy, Suspense } from 'react';
import { Link, Outlet, Route, Routes } from 'react-router-dom';
import AceptarPolitica from './components/AceptarPolitica.jsx';
import Cargando from './components/Cargando.jsx';
import Layout from './components/Layout.jsx';
import ProtectedRoute from './components/ProtectedRoute.jsx';
import { t } from './i18n/index.js';
import Catalogo from './pages/Catalogo.jsx';
import Login from './pages/Login.jsx';
import Privacidad from './pages/Privacidad.jsx';
import Registro from './pages/Registro.jsx';

const ComplejoDetalle = lazy(() => import('./pages/ComplejoDetalle.jsx'));
const Provisoria = lazy(() => import('./pages/Provisoria.jsx'));

// La guía visual es una herramienta de desarrollo: en el build de producción esta constante es `null` y el
// bloque de la guía no se incluye.
const GuiaVisual = import.meta.env.DEV ? lazy(() => import('./pages/GuiaVisual.jsx')) : null;

const ENLACES = GuiaVisual ? [{ a: '/guia', texto: t('navegacion.guia') }] : [];

function NoEncontrada() {
  return (
    <section>
      <h1 className="h2">{t('paginaNoEncontrada.titulo')}</h1>
      <p className="text-secondary">{t('paginaNoEncontrada.descripcion')}</p>
      <Link to="/">{t('comun.volverAlInicio')}</Link>
    </section>
  );
}

function PlantillaPublica() {
  return (
    <Layout enlaces={ENLACES}>
      <Suspense fallback={<Cargando variante="seccion" />}>
        <Outlet />
      </Suspense>
    </Layout>
  );
}

// Pantallas privadas todavía provisorias: cada una se reemplaza por su página definitiva en su subfase.
const PRIVADAS = [
  { ruta: '/mis-reservas', seccion: 'misReservas', titulo: t('navegacion.misReservas') },
  { ruta: '/perfil', seccion: 'perfil', titulo: t('navegacion.perfil') },
  { ruta: '/notificaciones', seccion: 'notificaciones', titulo: t('navegacion.notificaciones') },
  { ruta: '/panel', seccion: 'panel', titulo: t('navegacion.panel') },
  { ruta: '/panel/reportes', seccion: 'reportes', titulo: t('navegacion.reportes') },
  { ruta: '/sistema', seccion: 'sistema', titulo: t('navegacion.sistema') },
];

export default function App() {
  return (
    <Suspense fallback={<Cargando variante="pantalla" texto={t('comun.cargandoPantalla')} />}>
      <AceptarPolitica />
      <Routes>
        <Route element={<PlantillaPublica />}>
          <Route path="/" element={<Catalogo />} />
          <Route path="/complejos/:id" element={<ComplejoDetalle />} />
          <Route path="/login" element={<Login />} />
          <Route path="/registro" element={<Registro />} />
          <Route path="/privacidad" element={<Privacidad />} />
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
      </Routes>
    </Suspense>
  );
}
