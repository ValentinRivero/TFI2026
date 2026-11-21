import { useSearchParams } from 'react-router-dom';
import Alerta from '../components/Alerta.jsx';
import EncabezadoPantalla from '../components/EncabezadoPantalla.jsx';
import ListaReservas from '../components/ListaReservas.jsx';
import ModalCancelarReserva from '../components/ModalCancelarReserva.jsx';
import ModalInformarTransferencia from '../components/ModalInformarTransferencia.jsx';
import PestanasReservas from '../components/PestanasReservas.jsx';
import { VIGENCIA_RESERVA } from '../config/catalogos.js';
import useCancelarReserva from '../hooks/useCancelarReserva.js';
import useInformarTransferencia from '../hooks/useInformarTransferencia.js';
import useListaIncremental from '../hooks/useListaIncremental.js';
import { t } from '../i18n/index.js';
import { listarMisReservas } from '../services/reservaService.js';

/**
 * Reservas del jugador: las que están por jugarse y el historial, en listas que crecen con "Mostrar más". La vista
 * elegida vive en la URL y cada cambio reemplaza la entrada del historial.
 */
export default function MisReservas() {
  const [parametros, setParametros] = useSearchParams();
  const vigencia = parametros.get('vigencia') === VIGENCIA_RESERVA.PASADAS ? VIGENCIA_RESERVA.PASADAS : VIGENCIA_RESERVA.PROXIMAS;

  const lista = useListaIncremental((pagina, signal) => listarMisReservas(vigencia, pagina, signal), [vigencia]);
  const cancelacion = useCancelarReserva({ alCancelar: lista.recargar });
  const transferencia = useInformarTransferencia({ alGuardar: lista.recargar });

  const cambiarVista = (valor) => {
    setParametros(valor === VIGENCIA_RESERVA.PASADAS ? { vigencia: valor } : {}, { replace: true });
  };

  return (
    <div>
      <EncabezadoPantalla titulo={t('misReservas.titulo')} descripcion={t('misReservas.descripcion')} />
      <PestanasReservas activa={vigencia} onCambiar={cambiarVista} />
      {cancelacion.aviso && (
        <Alerta variante="success" onCerrar={cancelacion.descartarAviso}>{cancelacion.aviso}</Alerta>
      )}
      {transferencia.aviso && (
        <Alerta variante="success" onCerrar={transferencia.descartarAviso}>{transferencia.aviso}</Alerta>
      )}
      <ListaReservas
        lista={lista}
        vigencia={vigencia}
        onCancelar={cancelacion.pedir}
        onInformarTransferencia={transferencia.abrir}
      />
      <ModalInformarTransferencia formulario={transferencia} />
      <ModalCancelarReserva
        reserva={cancelacion.reserva}
        error={cancelacion.error}
        onConfirmar={cancelacion.confirmar}
        onCancelar={cancelacion.cerrar}
      />
    </div>
  );
}
