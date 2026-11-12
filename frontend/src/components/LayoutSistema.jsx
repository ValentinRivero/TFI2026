import { Suspense } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { t } from '../i18n/index.js';
import Cargando from './Cargando.jsx';
import SubnavegacionPanel from './SubnavegacionPanel.jsx';

const SECCIONES = [
  { a: '/sistema', texto: 'sistema.usuarios' },
  { a: '/sistema/contratos', texto: 'sistema.contratos' },
  { a: '/sistema/auditoria', texto: 'sistema.auditoria' },
];

/** Estructura de `/sistema/*` (superadmin): subnavegación entre cuentas, contratos y auditoría, y la subvista activa. */
export default function LayoutSistema() {
  const { pathname } = useLocation();

  return (
    <div>
      <SubnavegacionPanel secciones={SECCIONES.map(({ a, texto }) => ({ a, texto: t(texto) }))} />
      <Suspense key={pathname} fallback={<Cargando variante="seccion" />}>
        <Outlet />
      </Suspense>
    </div>
  );
}
