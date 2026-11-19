import { PARAMETROS } from '../config/parametros.js';
import { t } from '../i18n/index.js';
import Alerta from './Alerta.jsx';
import AlertaReintento from './AlertaReintento.jsx';
import Cargando from './Cargando.jsx';
import ModalConfirmar from './ModalConfirmar.jsx';

function ResumenDeBaja({ vistaPrevia }) {
  const { reservas_a_cancelar: aCancelar, reservas_senadas_conservadas: senadas, turnos_fijos_a_dar_de_baja: fijos } = vistaPrevia;

  return (
    <>
      <p>{t('perfil.bajaIntroduccion')}</p>
      <dl className="row g-2">
        <dt className="col-9 fw-normal">{t('perfil.bajaACancelar')}</dt>
        <dd className="col-3 mb-0 num text-end">{aCancelar}</dd>
        <dt className="col-9 fw-normal">{t('perfil.bajaSenadas')}</dt>
        <dd className="col-3 mb-0 num text-end">{senadas}</dd>
        <dt className="col-9 fw-normal">{t('perfil.bajaTurnosFijos')}</dt>
        <dd className="col-3 mb-0 num text-end">{fijos}</dd>
      </dl>
      {senadas > 0 && (
        <Alerta variante="info">
          {t('perfil.bajaSenadasDetalle', { dias: PARAMETROS.politica.retencionContactoDias })}
        </Alerta>
      )}
      <p className="mb-0">{t('perfil.bajaAnonimiza')}</p>
    </>
  );
}

/**
 * Confirmación de la baja de la cuenta. Muestra primero la vista previa del servidor (`vistaPrevia`): lo que se
 * cancela, lo que se conserva y, si la baja hoy se rechazaría, el impedimento. Mientras no haya vista previa válida
 * o haya un impedimento, no se puede confirmar. `errorBaja` es el rechazo del servidor al ejecutar la baja.
 */
export default function ModalBajaCuenta({
  mostrar,
  cargando,
  vistaPrevia,
  error,
  errorBaja,
  onReintentar,
  onConfirmar,
  onCancelar,
}) {
  const impedimento = vistaPrevia?.impedimento ?? null;

  return (
    <ModalConfirmar
      mostrar={mostrar}
      titulo={t('perfil.bajaModalTitulo')}
      variante="danger"
      textoConfirmar={t('perfil.bajaConfirmar')}
      textoCancelar={impedimento ? t('comun.cerrar') : t('perfil.bajaConservar')}
      confirmarDeshabilitado={cargando || Boolean(error) || !vistaPrevia || Boolean(impedimento)}
      onConfirmar={onConfirmar}
      onCancelar={onCancelar}
    >
      {cargando && <Cargando variante="seccion" />}
      {error && <AlertaReintento titulo={t('perfil.bajaErrorVistaPrevia')} mensaje={error.mensaje} onReintentar={onReintentar} />}
      {errorBaja && <Alerta variante="danger">{errorBaja.mensaje}</Alerta>}
      {impedimento && <Alerta variante="warning" titulo={t('perfil.bajaImpedimento')}>{impedimento}</Alerta>}
      {vistaPrevia && !impedimento && <ResumenDeBaja vistaPrevia={vistaPrevia} />}
    </ModalConfirmar>
  );
}
