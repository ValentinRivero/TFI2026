import { useState } from 'react';
import { t } from '../i18n/index.js';
import { informarTransferencia } from '../services/reservaService.js';
import { cuerpoTransferencia, validarTransferencia } from '../utils/pagos.js';
import useEnvio from './useEnvio.js';

const avisoDeEnvio = (reserva) => {
  if (reserva.transferencia_rechazada) return 'transferencia.avisoReenviada';
  return reserva.transferencia_informada ? 'transferencia.avisoCorregida' : 'transferencia.avisoInformada';
};

/**
 * Aviso del jugador de que transfirió la seña de una reserva propia: quién transfirió y el número de operación. Si ya
 * había informado una transferencia (y la seña sigue pendiente), `abrir` parte de esos datos para corregirlos. Los
 * errores por campo combinan la validación local (tras el primer intento) con los del servidor. Si el servidor rechaza
 * porque la reserva cambió (400) o ya no existe (404), se recarga la lista para mostrar su estado real.
 * `alGuardar` recarga la lista y `aviso` confirma lo ocurrido hasta que se descarte.
 */
export default function useInformarTransferencia({ alGuardar }) {
  const [edicion, setEdicion] = useState(null);
  const [aviso, setAviso] = useState(null);
  const envio = useEnvio();

  const abrir = (reserva) => {
    envio.limpiar();
    setAviso(null);
    setEdicion({
      reserva,
      titular: reserva.transferencia?.titular ?? '',
      referencia: reserva.transferencia?.referencia ?? '',
      intentado: false,
    });
  };

  const cerrar = () => {
    envio.limpiar();
    setEdicion(null);
  };

  const cambiar = (campo, valor) => {
    envio.limpiar();
    setEdicion((actual) => ({ ...actual, [campo]: valor }));
  };

  const erroresLocales = edicion ? validarTransferencia(edicion) : {};
  const errores = { ...(edicion?.intentado ? erroresLocales : {}), ...(envio.error?.campos ?? {}) };

  const guardar = async () => {
    if (!edicion) return;
    setEdicion((actual) => ({ ...actual, intentado: true }));
    if (Object.keys(erroresLocales).length > 0) return;
    const { reserva } = edicion;
    const resultado = await envio.enviar(() => informarTransferencia(reserva.id, cuerpoTransferencia(edicion)));
    if (resultado.ok) {
      setEdicion(null);
      setAviso(t(avisoDeEnvio(reserva)));
      alGuardar();
    } else if ([400, 404].includes(resultado.error.status) && !resultado.error.campos?.titular && !resultado.error.campos?.referencia) {
      alGuardar();
    }
  };

  return {
    reserva: edicion?.reserva ?? null,
    titular: edicion?.titular ?? '',
    referencia: edicion?.referencia ?? '',
    errores,
    error: envio.error,
    enviando: envio.enviando,
    aviso,
    abrir,
    cerrar,
    cambiar,
    guardar,
    descartarAviso: () => setAviso(null),
  };
}
