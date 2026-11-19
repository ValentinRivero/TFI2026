import Button from 'react-bootstrap/Button';
import Card from 'react-bootstrap/Card';
import Col from 'react-bootstrap/Col';
import Form from 'react-bootstrap/Form';
import Row from 'react-bootstrap/Row';
import { ESTADO_CONTRATO, ESTADOS_CONTRATO_INICIALES, opcionesDe } from '../config/catalogos.js';
import { t } from '../i18n/index.js';
import Alerta from './Alerta.jsx';
import BotonAccion from './BotonAccion.jsx';
import CamposComplejo from './CamposComplejo.jsx';
import CampoSelect from './CampoSelect.jsx';
import SelectorPropietario from './SelectorPropietario.jsx';

const OPCIONES_ESTADO_INICIAL = opcionesDe(ESTADO_CONTRATO, ESTADOS_CONTRATO_INICIALES);

/**
 * Alta de un complejo con su contrato (presentación): propietario (un dueño activo), perfil comercial y estado inicial
 * del contrato. `formulario` es lo que devuelve `useContratos` en `alta`.
 */
export default function FormularioComplejoNuevo({ formulario }) {
  const { valores, errores, error, enviando, cambiar, enviar, cerrar } = formulario;
  const campo = (nombre) => ({ valor: valores[nombre], onCambiar: (valor) => cambiar(nombre, valor), error: errores[nombre] });

  return (
    <Card body className="mb-4">
      <h2 className="h5 mb-3">{t('contratos.altaTitulo')}</h2>
      <Form onSubmit={enviar} noValidate>
        {error && <Alerta variante="danger">{error.mensaje}</Alerta>}
        <Row className="g-3 mb-3">
          <Col md={6}>
            <SelectorPropietario
              busqueda={formulario.busquedaDueno}
              onBuscar={formulario.buscarDueno}
              duenos={formulario.duenos}
              valor={valores.propietario}
              onElegir={(valor) => cambiar('propietario', valor)}
              error={errores.propietario}
            />
          </Col>
          <Col md={6}>
            <CampoSelect
              id="complejo-nuevo-estado"
              etiqueta={t('contratos.estadoInicial')}
              opciones={OPCIONES_ESTADO_INICIAL}
              ayuda={t('contratos.ayudaEstadoInicial')}
              className="mb-0"
              {...campo('estado_contrato')}
            />
          </Col>
        </Row>
        <CamposComplejo campo={campo} prefijo="complejo-nuevo" />
        <div className="d-flex flex-wrap gap-2 mt-4">
          <BotonAccion type="submit" cargando={enviando} textoCargando={t('contratos.creando')}>
            {t('contratos.crear')}
          </BotonAccion>
          <Button variant="outline-secondary" onClick={cerrar} disabled={enviando}>{t('comun.cancelar')}</Button>
        </div>
      </Form>
    </Card>
  );
}
