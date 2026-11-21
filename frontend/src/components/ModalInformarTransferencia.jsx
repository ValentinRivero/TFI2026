import { PARAMETROS } from '../config/parametros.js';
import { t } from '../i18n/index.js';
import { formatearFechaLarga, formatearHora } from '../utils/formatos.js';
import Alerta from './Alerta.jsx';
import CampoFormulario from './CampoFormulario.jsx';
import ModalConfirmar from './ModalConfirmar.jsx';

const { transferenciaTitularMaximo, referenciaMaximo } = PARAMETROS.pagos;

/**
 * Aviso de que se transfirió la seña (o corrección de uno ya enviado). `formulario` es lo que devuelve
 * `useInformarTransferencia`. Aclara que informar no confirma el pago y que los datos se comparten solo con el
 * complejo; un rechazo del servidor se muestra dentro del diálogo, que queda abierto para corregir o cancelar.
 */
export default function ModalInformarTransferencia({ formulario }) {
  const { reserva, errores, error } = formulario;
  const corrige = Boolean(reserva?.transferencia_informada);
  const reenvia = Boolean(reserva?.transferencia_rechazada);

  return (
    <ModalConfirmar
      mostrar={Boolean(reserva)}
      titulo={t(reenvia ? 'transferencia.tituloReenviar' : corrige ? 'transferencia.tituloCorregir' : 'transferencia.titulo')}
      textoConfirmar={t(corrige && !reenvia ? 'transferencia.guardarCorreccion' : 'transferencia.enviar')}
      confirmarDeshabilitado={formulario.enviando}
      onConfirmar={formulario.guardar}
      onCancelar={formulario.cerrar}
    >
      {reserva && (
        <>
          {error && !error.campos?.titular && !error.campos?.referencia && (
            <Alerta variante="danger">{error.mensaje}</Alerta>
          )}
          <p className="small text-secondary">
            {t('transferencia.turno', {
              fecha: formatearFechaLarga(reserva.fecha_turno),
              hora: formatearHora(reserva.hora_inicio),
              complejo: reserva.complejo.nombre,
            })}
          </p>
          <p>{t('transferencia.texto')}</p>
          <CampoFormulario
            id="transferencia-titular"
            etiqueta={t('transferencia.titular')}
            maxLength={transferenciaTitularMaximo}
            autoComplete="off"
            autoFocus
            ayuda={t('transferencia.ayudaTitular')}
            valor={formulario.titular}
            onCambiar={(valor) => formulario.cambiar('titular', valor)}
            error={errores.titular}
          />
          <CampoFormulario
            id="transferencia-referencia"
            etiqueta={t('transferencia.referencia')}
            maxLength={referenciaMaximo}
            autoComplete="off"
            spellCheck={false}
            ayuda={t('transferencia.ayudaReferencia')}
            valor={formulario.referencia}
            onCambiar={(valor) => formulario.cambiar('referencia', valor)}
            error={errores.referencia}
          />
          <p className="small text-secondary mb-0">{t('transferencia.privacidad')}</p>
        </>
      )}
    </ModalConfirmar>
  );
}
