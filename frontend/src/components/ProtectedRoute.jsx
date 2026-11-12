import { useState } from 'react';
import { Link, Navigate, useLocation } from 'react-router-dom';
import { ETIQUETA_ROL, puedeVer } from '../config/catalogos.js';
import useSesion from '../hooks/useSesion.js';
import { t } from '../i18n/index.js';
import Alerta from './Alerta.jsx';
import Cargando from './Cargando.jsx';

/**
 * Protege una ruta privada. Espera a que se resuelva la sesión inicial, lleva a `/login` guardando la ruta de origen
 * si no hay sesión y, con `seccion`, valida el rol contra la matriz de `catalogos.js`. Si la sesión termina estando en
 * la pantalla por una salida deliberada (cerrar sesión, baja de la cuenta), va directo a la portada con el aviso: no
 * pasa por el login ni deja esa entrada en el historial. Solo decide la navegación: el control real lo hacen los
 * backends (403).
 */
export default function ProtectedRoute({ seccion, children }) {
  const { autenticado, cargandoSesion, rol, cierre } = useSesion();
  const ubicacion = useLocation();
  // Una salida deliberada solo cuenta si esta pantalla estaba abierta con sesión: entrar sin sesión va al login.
  const [estuvoAutenticado, setEstuvoAutenticado] = useState(autenticado);
  if (autenticado && !estuvoAutenticado) setEstuvoAutenticado(true);

  if (cargandoSesion) return <Cargando variante="pantalla" />;
  if (!autenticado) {
    if (estuvoAutenticado && cierre) {
      return <Navigate to="/" replace state={cierre.aviso ? { aviso: cierre.aviso } : null} />;
    }
    return <Navigate to="/login" replace state={{ desde: ubicacion }} />;
  }

  if (seccion && !puedeVer(seccion, rol)) {
    return (
      <Alerta variante="warning" titulo={t('acceso.sinAcceso')}>
        <p className="mb-2">{t('acceso.sinAccesoDetalle', { rol: ETIQUETA_ROL[rol] ?? rol ?? '' })}</p>
        <Link to="/">{t('comun.volverAlInicio')}</Link>
      </Alerta>
    );
  }
  return children;
}
