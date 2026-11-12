import Alerta from '../components/Alerta.jsx';
import EncabezadoPantalla from '../components/EncabezadoPantalla.jsx';
import FiltrosExcepciones from '../components/FiltrosExcepciones.jsx';
import FormularioExcepcion from '../components/FormularioExcepcion.jsx';
import ModalConfirmarAccion from '../components/ModalConfirmarAccion.jsx';
import TablaExcepciones from '../components/TablaExcepciones.jsx';
import useContextoPanel from '../hooks/useContextoPanel.js';
import useExcepciones from '../hooks/useExcepciones.js';
import { t } from '../i18n/index.js';

/**
 * Excepciones horarias del complejo activo (cierres por mantenimiento, clima, feriados...). Las gestionan el
 * dueño, el operador y el superadmin. Las excepciones no se editan: se dan de baja y se registra otra.
 */
export default function GestionExcepciones() {
  const { complejo } = useContextoPanel();
  const excepciones = useExcepciones(complejo.id);
  const { baja } = excepciones;

  return (
    <div>
      <EncabezadoPantalla titulo={t('excepciones.titulo')} descripcion={t('excepciones.descripcion')} />

      {excepciones.avisoAlta && (
        <Alerta variante="warning" onCerrar={excepciones.descartarAvisoAlta}>{excepciones.avisoAlta}</Alerta>
      )}
      {excepciones.avisoBaja && (
        <Alerta variante="success" onCerrar={excepciones.descartarAvisoBaja}>{excepciones.avisoBaja}</Alerta>
      )}

      <FormularioExcepcion formulario={excepciones.formulario} canchas={excepciones.canchas} />

      <FiltrosExcepciones
        filtros={excepciones.filtros}
        canchas={excepciones.canchas}
        onCambiar={excepciones.cambiarFiltro}
        onLimpiar={excepciones.limpiarFiltros}
      />
      <TablaExcepciones lista={excepciones.lista} onBaja={baja.pedir} />

      <ModalConfirmarAccion
        abierto={Boolean(baja.excepcion)}
        titulo={t('excepciones.bajaTitulo')}
        texto={t('excepciones.bajaTexto')}
        error={baja.error}
        textoConfirmar={t('excepciones.bajaConfirmar')}
        onConfirmar={baja.confirmar}
        onCancelar={baja.cerrar}
      />
    </div>
  );
}
