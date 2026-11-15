import Alerta from '../components/Alerta.jsx';
import AvisosUrgentes from '../components/AvisosUrgentes.jsx';
import EncabezadoPantalla from '../components/EncabezadoPantalla.jsx';
import FiltrosNotificaciones from '../components/FiltrosNotificaciones.jsx';
import ListaNotificaciones from '../components/ListaNotificaciones.jsx';
import useBandejaNotificaciones from '../hooks/useBandejaNotificaciones.js';
import useComplejosDeNotificaciones from '../hooks/useComplejosDeNotificaciones.js';
import useFiltrosNotificaciones from '../hooks/useFiltrosNotificaciones.js';
import useMarcarLeida from '../hooks/useMarcarLeida.js';
import { t } from '../i18n/index.js';
import { listarMisNotificaciones } from '../services/notificacionService.js';
import { anunciarLeida } from '../utils/avisosNotificaciones.js';
import { clavesDeVacio, filtrosUrgentesDe } from '../utils/notificaciones.js';

const CAMPOS_BASE = ['estado', 'prioridad', 'categoria'];
const CAMPOS_CON_COMPLEJO = [...CAMPOS_BASE, 'complejo'];

/**
 * Bandeja personal de notificaciones, para cualquier rol: cada integrante recibe acá lo que le corresponde por su rol,
 * su complejo y sus permisos. Arriba, los avisos urgentes pendientes; debajo, la lista con sus filtros en la URL y
 * "Mostrar más". Quien recibe avisos de más de un complejo los distingue y puede filtrar por uno. Al marcar una como
 * leída se descuenta en el acto el contador de la campana.
 */
export default function Notificaciones() {
  const { filtros, cambiar, limpiar, hayFiltros } = useFiltrosNotificaciones();
  const { complejos, nombres, variosComplejos } = useComplejosDeNotificaciones();
  const urgentes = useBandejaNotificaciones(listarMisNotificaciones, filtrosUrgentesDe(filtros));
  const bandeja = useBandejaNotificaciones(listarMisNotificaciones, filtros);
  const marcado = useMarcarLeida({
    alMarcar: (notificacion) => {
      urgentes.registrarLeida(notificacion.id);
      bandeja.registrarLeida(notificacion.id);
      anunciarLeida();
    },
  });
  const claves = clavesDeVacio(filtros, 'notificaciones.vacioDescripcion');

  return (
    <div>
      <EncabezadoPantalla titulo={t('notificaciones.titulo')} descripcion={t('notificaciones.descripcion')} />
      {marcado.error && (
        <Alerta onCerrar={marcado.descartarError}>
          {t('notificaciones.errorMarcar')} {marcado.error.mensaje}
        </Alerta>
      )}
      <AvisosUrgentes lista={urgentes} nombresDeComplejos={nombres} ocultarSiVacio onMarcarLeida={marcado.marcar} />
      <FiltrosNotificaciones
        filtros={filtros}
        campos={variosComplejos ? CAMPOS_CON_COMPLEJO : CAMPOS_BASE}
        complejos={complejos}
        hayFiltros={hayFiltros}
        onCambiar={cambiar}
        onLimpiar={limpiar}
      />
      <ListaNotificaciones
        lista={bandeja}
        etiqueta={t('notificaciones.titulo')}
        nombresDeComplejos={nombres}
        vacio={{ titulo: t(claves.titulo), descripcion: t(claves.descripcion) }}
        onMarcarLeida={marcado.marcar}
      />
    </div>
  );
}
