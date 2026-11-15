import Button from 'react-bootstrap/Button';
import Card from 'react-bootstrap/Card';
import Form from 'react-bootstrap/Form';
import { t } from '../i18n/index.js';
import Alerta from './Alerta.jsx';
import BotonAccion from './BotonAccion.jsx';
import CamposComplejo from './CamposComplejo.jsx';

/**
 * Perfil comercial del complejo (presentación): dirección, coordenadas, teléfono, límite de cancelación e
 * información de la seña. Con `soloLectura` los campos se muestran atenuados y deshabilitados (sin foco ni selección) y no hay botones.
 * El estado lo maneja `useConfiguracionComplejo`; `errores` es un texto por campo y `error`, el `ErrorApi` del envío.
 */
export default function FormularioComplejo({
  valores,
  errores,
  onCambiar,
  onEnviar,
  onDescartar,
  enviando,
  hayCambios,
  error,
  guardado,
  soloLectura = false,
}) {
  const campo = (nombre) => ({
    valor: valores[nombre],
    onCambiar: (valor) => onCambiar(nombre, valor),
    error: errores[nombre],
    disabled: soloLectura,
    tabIndex: soloLectura ? -1 : undefined,
  });

  return (
    <Card body className="mb-4">
      <h2 className="h5 mb-3">{t('configuracion.datos')}</h2>
      <Form onSubmit={onEnviar} noValidate>
        <fieldset disabled={soloLectura} className={`border-0 p-0 m-0${soloLectura ? ' solo-lectura' : ''}`}>
        {error && <Alerta variante="danger">{error.mensaje}</Alerta>}
        {guardado && <Alerta variante="success">{t('configuracion.guardado')}</Alerta>}
        <CamposComplejo campo={campo} />
        </fieldset>
        {!soloLectura && (
          <div className="d-flex flex-wrap gap-2 mt-4">
            <BotonAccion type="submit" cargando={enviando} disabled={!hayCambios} textoCargando={t('configuracion.guardando')}>
              {t('comun.guardar')}
            </BotonAccion>
            <Button variant="outline-secondary" disabled={!hayCambios || enviando} onClick={onDescartar}>
              {t('configuracion.descartar')}
            </Button>
          </div>
        )}
      </Form>
    </Card>
  );
}
