import { Suspense, useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { puedeVer } from '../config/catalogos.js';
import useComplejoActivo from '../hooks/useComplejoActivo.js';
import useConsulta from '../hooks/useConsulta.js';
import useSesion from '../hooks/useSesion.js';
import { t } from '../i18n/index.js';
import { listarAdministrados } from '../services/complejoAdminService.js';
import { resolverComplejoActivo } from '../utils/complejo.js';
import AlertaReintento from './AlertaReintento.jsx';
import Cargando from './Cargando.jsx';
import EstadoVacio from './EstadoVacio.jsx';
import SelectorComplejo from './SelectorComplejo.jsx';
import SubnavegacionPanel from './SubnavegacionPanel.jsx';

const SECCIONES = [
  { a: '/panel', texto: 'navegacion.panelConfiguracion', seccion: 'panel' },
  { a: '/panel/canchas', texto: 'navegacion.panelCanchas', seccion: 'panel' },
  { a: '/panel/excepciones', texto: 'navegacion.panelExcepciones', seccion: 'excepciones' },
  { a: '/panel/agenda', texto: 'navegacion.panelAgenda', seccion: 'agenda' },
  { a: '/panel/reportes', texto: 'navegacion.panelReportes', seccion: 'reportes' },
  { a: '/panel/notificaciones', texto: 'navegacion.panelNotificaciones', seccion: 'notificacionesComplejo' },
];

/**
 * Estructura de `/panel/*`: carga los complejos que el usuario administra, mantiene el complejo activo en memoria
 * (se elige desde el selector superior; con uno solo se toma automáticamente), muestra la subnavegación según el rol
 * y entrega a cada subvista el complejo activo por el contexto de la ruta (ver `useContextoPanel`). Cada complejo
 * y cada subvista tienen su propio límite de carga, así que cambiar de uno u otra reinicia el estado local.
 */
export default function LayoutPanel() {
  const { rol } = useSesion();
  const { pathname } = useLocation();
  const { elegido, elegir } = useComplejoActivo();
  const consulta = useConsulta((signal) => listarAdministrados(signal), []);
  const [reemplazos, setReemplazos] = useState({ base: null, porId: {} });

  const datos = consulta.datos;
  const porId = reemplazos.base === datos ? reemplazos.porId : {};
  const complejos = (datos ?? []).map((complejo) => porId[complejo.id] ?? complejo);
  const complejo = resolverComplejoActivo(complejos, elegido);

  // El backend devuelve el complejo completo al guardar: se refleja sin volver a pedir la lista.
  const actualizarComplejo = (nuevo) => setReemplazos({ base: datos, porId: { ...porId, [nuevo.id]: nuevo } });

  if (!datos) {
    if (consulta.error) {
      return <AlertaReintento titulo={t('panel.errorTitulo')} mensaje={consulta.error.mensaje} onReintentar={consulta.recargar} />;
    }
    return <Cargando variante="seccion" />;
  }

  if (!complejo) {
    return <EstadoVacio titulo={t('panel.sinComplejosTitulo')} descripcion={t('panel.sinComplejosDescripcion')} />;
  }

  const secciones = SECCIONES.filter(({ seccion }) => puedeVer(seccion, rol)).map(({ a, texto }) => ({ a, texto: t(texto) }));

  return (
    <div>
      <div className="mb-3">
        <SelectorComplejo complejos={complejos} activo={complejo} onElegir={elegir} />
      </div>
      <SubnavegacionPanel secciones={secciones} />
      <Suspense key={`${complejo.id}:${pathname}`} fallback={<Cargando variante="seccion" />}>
        <Outlet context={{ complejo, actualizarComplejo }} />
      </Suspense>
    </div>
  );
}
