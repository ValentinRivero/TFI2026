import { lazy, Suspense } from 'react';
import { Route, Routes } from 'react-router-dom';
import Cargando from './components/Cargando.jsx';
import Layout from './components/Layout.jsx';
import { t } from './i18n/index.js';

// La guía visual es una herramienta de desarrollo: en el build de producción esta constante es `null` y el
// bloque de la guía no se incluye.
const GuiaVisual = import.meta.env.DEV ? lazy(() => import('./pages/GuiaVisual.jsx')) : null;

const ENLACES = [
  { a: '/', texto: t('navegacion.inicio') },
  ...(GuiaVisual ? [{ a: '/guia', texto: t('navegacion.guia') }] : []),
];

function Portada() {
  return (
    <section>
      <h1 className="display-5">{t('marca.nombre')}</h1>
      <p className="lead text-secondary">{t('marca.eslogan')}</p>
    </section>
  );
}

export default function App() {
  return (
    <Suspense fallback={<Cargando variante="pantalla" texto={t('comun.cargandoPantalla')} />}>
      <Routes>
        <Route path="/" element={<Layout enlaces={ENLACES}><Portada /></Layout>} />
        {GuiaVisual && <Route path="/guia" element={<Layout enlaces={ENLACES}><GuiaVisual /></Layout>} />}
      </Routes>
    </Suspense>
  );
}
