import Alerta from '../components/Alerta.jsx';
import EncabezadoPantalla from '../components/EncabezadoPantalla.jsx';
import FiltrosNotificaciones from '../components/FiltrosNotificaciones.jsx';
import ListaNotificaciones from '../components/ListaNotificaciones.jsx';
import useBandejaNotificaciones from '../hooks/useBandejaNotificaciones.js';
import useFiltrosNotificaciones from '../hooks/useFiltrosNotificaciones.js';
import useMarcarLeida from '../hooks/useMarcarLeida.js';
import { t } from '../i18n/index.js';
import { listarMisNotificaciones } from '../services/notificacionService.js';
import { anunciarLeida } from '../utils/avisosNotificaciones.js';
import { clavesDeVacio } from '../utils/notificaciones.js';

/**
 * Bandeja personal de notificaciones, para cualquier rol. Los filtros viven en la URL y la lista crece con "Mostrar
 * más". Al marcar una como leída se descuenta en el acto el contador de la campana.
 */
export default function Notificaciones() {
  const { filtros, cambiar, limpiar, hayFiltros } = useFiltrosNotificaciones();
  const bandeja = useBandejaNotificaciones(listarMisNotificaciones, filtros);
  const marcado = useMarcarLeida({
    alMarcar: (notificacion) => {
      bandeja.registrarLeida(notificacion.id);
      anunciarLeida();
    },
  });
  const claves = clavesDeVacio(filtros, 'notificaciones.vacioDescripcion');

  return (
    <div>
      <EncabezadoPantalla titulo={t('notificaciones.titulo')} descripcion={t('notificaciones.descripcion')} />
      <FiltrosNotificaciones filtros={filtros} hayFiltros={hayFiltros} onCambiar={cambiar} onLimpiar={limpiar} />
      {marcado.error && (
        <Alerta onCerrar={marcado.descartarError}>
          {t('notificaciones.errorMarcar')} {marcado.error.mensaje}
        </Alerta>
      )}
      <ListaNotificaciones
        lista={bandeja}
        etiqueta={t('notificaciones.titulo')}
        vacio={{ titulo: t(claves.titulo), descripcion: t(claves.descripcion) }}
        onMarcarLeida={marcado.marcar}
      />
    </div>
  );
}
