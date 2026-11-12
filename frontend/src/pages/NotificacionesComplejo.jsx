import Alerta from '../components/Alerta.jsx';
import AvisosUrgentes from '../components/AvisosUrgentes.jsx';
import EncabezadoPantalla from '../components/EncabezadoPantalla.jsx';
import FiltrosNotificaciones from '../components/FiltrosNotificaciones.jsx';
import ListaNotificaciones from '../components/ListaNotificaciones.jsx';
import PestanasCategorias from '../components/PestanasCategorias.jsx';
import useBandejaNotificaciones from '../hooks/useBandejaNotificaciones.js';
import useContextoPanel from '../hooks/useContextoPanel.js';
import useFiltrosNotificaciones from '../hooks/useFiltrosNotificaciones.js';
import useMarcarLeida from '../hooks/useMarcarLeida.js';
import { t } from '../i18n/index.js';
import { listarNotificacionesDelComplejo } from '../services/notificacionService.js';
import { clavesDeVacio, FILTROS_URGENTES } from '../utils/notificaciones.js';

const CAMPOS_DE_FILTRO = ['estado'];

/**
 * Bandeja operativa del complejo activo (dueño, operador y superadmin): arriba los avisos urgentes pendientes y
 * debajo todos los avisos, separados por categoría y por estado. Marcar un aviso como leído lo actualiza en las
 * dos listas.
 */
export default function NotificacionesComplejo() {
  const { complejo } = useContextoPanel();
  const { filtros, cambiar, limpiar, hayFiltros } = useFiltrosNotificaciones();

  const pedir = (filtrosDeLista, pagina, signal) => (
    listarNotificacionesDelComplejo(complejo.id, filtrosDeLista, pagina, signal)
  );
  const urgentes = useBandejaNotificaciones(pedir, FILTROS_URGENTES, [complejo.id]);
  const bandeja = useBandejaNotificaciones(pedir, filtros, [complejo.id]);
  const marcado = useMarcarLeida({
    alMarcar: (notificacion) => {
      urgentes.registrarLeida(notificacion.id);
      bandeja.registrarLeida(notificacion.id);
    },
  });
  const claves = clavesDeVacio(filtros, 'notificaciones.complejoVacioDescripcion');

  return (
    <div>
      <EncabezadoPantalla
        titulo={t('notificaciones.complejoTitulo')}
        descripcion={t('notificaciones.complejoDescripcion', { complejo: complejo.nombre })}
      />
      {marcado.error && (
        <Alerta onCerrar={marcado.descartarError}>
          {t('notificaciones.errorMarcar')} {marcado.error.mensaje}
        </Alerta>
      )}
      <AvisosUrgentes lista={urgentes} onMarcarLeida={marcado.marcar} />
      <PestanasCategorias activa={filtros.categoria} onCambiar={(categoria) => cambiar('categoria', categoria)} />
      <FiltrosNotificaciones
        filtros={filtros}
        campos={CAMPOS_DE_FILTRO}
        hayFiltros={hayFiltros}
        onCambiar={cambiar}
        onLimpiar={limpiar}
      />
      <ListaNotificaciones
        lista={bandeja}
        etiqueta={t('notificaciones.complejoTitulo')}
        vacio={{ titulo: t(claves.titulo), descripcion: t(claves.descripcion) }}
        onMarcarLeida={marcado.marcar}
      />
    </div>
  );
}
