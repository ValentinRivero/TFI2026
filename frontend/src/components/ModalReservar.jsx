import { t } from '../i18n/index.js';
import { pronosticoDeFecha } from '../utils/clima.js';
import { calcularDesglose, exigeSena, filasDeDesglose } from '../utils/pagos.js';
import Alerta from './Alerta.jsx';
import AvisoSinCancelacion from './AvisoSinCancelacion.jsx';
import ClimaCard from './ClimaCard.jsx';
import CondicionesSena from './CondicionesSena.jsx';
import DatosTurno from './DatosTurno.jsx';
import DesgloseMontos from './DesgloseMontos.jsx';
import ModalConfirmar from './ModalConfirmar.jsx';

/**
 * Confirmación de la reserva: turno elegido, pronóstico del día (si entra en la ventana del clima), montos (con la
 * seña a transferir y el saldo si el complejo la exige), condiciones de seña y margen de cancelación del complejo. `error` es el `ErrorApi` de un intento rechazado; `onConfirmar` puede
 * devolver una promesa y `ModalConfirmar` evita el doble envío. `horasSinCancelacion` repite la advertencia cuando
 * el turno ya está dentro del margen de cancelación.
 */
export default function ModalReservar({ mostrar, complejo, cancha, bloque, fecha, clima, error, horasSinCancelacion, onConfirmar, onCancelar }) {
  if (!cancha || !bloque) return null;
  const horas = complejo.horas_limite_cancelacion;
  const hayPronostico = Boolean(pronosticoDeFecha(clima.datos, fecha));
  const conSena = exigeSena(complejo);

  return (
    <ModalConfirmar
      mostrar={mostrar}
      titulo={t('reserva.titulo')}
      onConfirmar={onConfirmar}
      onCancelar={onCancelar}
      textoConfirmar={t('reserva.confirmar')}
    >
      {error && <Alerta variante="danger">{error.mensaje}</Alerta>}
      {horasSinCancelacion && <AvisoSinCancelacion horas={horasSinCancelacion} />}
      <DatosTurno cancha={cancha} bloque={bloque} fecha={fecha} />
      {hayPronostico && <div className="mb-3"><ClimaCard {...clima} variante="dia" fecha={fecha} /></div>}
      {conSena && (
        <section className="mb-3" aria-label={t('reserva.desgloseTitulo')}>
          <h3 className="h6">{t('reserva.desgloseTitulo')}</h3>
          <DesgloseMontos filas={filasDeDesglose(calcularDesglose(bloque.precio, complejo.porcentaje_sena))} className="mb-2" />
          <p className="small text-secondary mb-0">{t('reserva.desgloseSenaAviso')}</p>
        </section>
      )}
      <h3 className="h6">{t('complejo.sena')}</h3>
      <p><CondicionesSena complejo={complejo} /></p>
      <h3 className="h6">{t('complejo.cancelacion')}</h3>
      <p className="mb-0">
        {horas > 0 ? t('complejo.cancelacionHoras', { horas }) : t('complejo.cancelacionHasta')}
      </p>
    </ModalConfirmar>
  );
}
