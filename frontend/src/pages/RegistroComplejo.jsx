import EncabezadoPantalla from '../components/EncabezadoPantalla.jsx';
import FiltrosNotificaciones from '../components/FiltrosNotificaciones.jsx';
import ListaNotificaciones from '../components/ListaNotificaciones.jsx';
import PestanasCategorias from '../components/PestanasCategorias.jsx';
import useBandejaNotificaciones from '../hooks/useBandejaNotificaciones.js';
import useContextoPanel from '../hooks/useContextoPanel.js';
import useFiltrosNotificaciones from '../hooks/useFiltrosNotificaciones.js';
import { t } from '../i18n/index.js';
import { listarRegistroDelComplejo } from '../services/notificacionService.js';
import { filtrosDeRegistro } from '../utils/notificaciones.js';

const CAMPOS_DE_FILTRO = ['prioridad'];

/**
 * Registro del complejo activo (dueño, operador y superadmin): todo lo que ocurrió, de lo más reciente a lo más
 * antiguo, con los ids de las reservas, canchas y usuarios. A diferencia de la bandeja personal no tiene estado de
 * lectura: nada se marca ni se oculta. Se filtra por categoría (pestañas) y por prioridad; el operador no ve lo comercial.
 */
export default function RegistroComplejo() {
  const { complejo } = useContextoPanel();
  const { filtros, cambiar, limpiar, hayFiltros } = useFiltrosNotificaciones();
  const registro = useBandejaNotificaciones(
    (filtrosDeLista, pagina, signal) => listarRegistroDelComplejo(complejo.id, filtrosDeRegistro(filtrosDeLista), pagina, signal),
    filtrosDeRegistro(filtros),
    [complejo.id],
  );

  return (
    <div>
      <EncabezadoPantalla
        titulo={t('notificaciones.registroTitulo')}
        descripcion={t('notificaciones.registroDescripcion', { complejo: complejo.nombre })}
      />
      <PestanasCategorias activa={filtros.categoria} onCambiar={(categoria) => cambiar('categoria', categoria)} />
      <FiltrosNotificaciones
        filtros={filtros}
        campos={CAMPOS_DE_FILTRO}
        hayFiltros={hayFiltros && Boolean(filtros.prioridad || filtros.categoria)}
        onCambiar={cambiar}
        onLimpiar={limpiar}
      />
      <ListaNotificaciones
        lista={registro}
        etiqueta={t('notificaciones.registroTitulo')}
        mostrarEstado={false}
        vacio={{ titulo: t('notificaciones.vacioTitulo'), descripcion: t('notificaciones.registroVacioDescripcion') }}
      />
    </div>
  );
}
