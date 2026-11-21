import Col from 'react-bootstrap/Col';
import Row from 'react-bootstrap/Row';
import { PARAMETROS } from '../config/parametros.js';
import { t } from '../i18n/index.js';
import CampoFormulario from './CampoFormulario.jsx';

const { limitesCampos, pagos } = PARAMETROS;

/**
 * Seña y datos de transferencia del complejo: porcentaje de seña (0 no exige seña), alias y titular de la cuenta. Con
 * `campo(nombre)` igual que `CamposComplejo`: devuelve `valor`, `onCambiar`, `error` y, en solo lectura, `disabled`.
 */
export default function CamposSena({ campo, prefijo = 'complejo' }) {
  return (
    <section aria-labelledby={`${prefijo}-sena-titulo`} className="mt-4">
      <h3 id={`${prefijo}-sena-titulo`} className="h6">{t('configuracion.senaTitulo')}</h3>
      <p className="small text-secondary">{t('configuracion.senaDescripcion')}</p>
      <Row className="g-3">
        <Col sm={6} md={4}>
          <CampoFormulario
            id={`${prefijo}-porcentaje-sena`}
            etiqueta={t('configuracion.porcentajeSena')}
            type="number"
            min={0}
            max={pagos.porcentajeSenaMaximo}
            inputMode="numeric"
            ayuda={t('configuracion.ayudaPorcentajeSena')}
            className="mb-0"
            {...campo('porcentaje_sena')}
          />
        </Col>
        <Col sm={6} md={4}>
          <CampoFormulario
            id={`${prefijo}-alias`}
            etiqueta={t('configuracion.aliasTransferencia')}
            maxLength={pagos.aliasLargoMaximo}
            autoComplete="off"
            spellCheck={false}
            ayuda={t('configuracion.ayudaAlias', { minimo: pagos.aliasLargoMinimo, maximo: pagos.aliasLargoMaximo })}
            className="mb-0"
            {...campo('alias_transferencia')}
          />
        </Col>
        <Col md={4}>
          <CampoFormulario
            id={`${prefijo}-titular`}
            etiqueta={t('configuracion.titularTransferencia')}
            maxLength={limitesCampos.titularTransferencia}
            ayuda={t('configuracion.ayudaTitular')}
            className="mb-0"
            {...campo('titular_transferencia')}
          />
        </Col>
      </Row>
    </section>
  );
}
