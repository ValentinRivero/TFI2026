import Card from 'react-bootstrap/Card';
import Form from 'react-bootstrap/Form';
import { Link } from 'react-router-dom';
import { PARAMETROS } from '../config/parametros.js';
import { t } from '../i18n/index.js';
import Alerta from './Alerta.jsx';
import BotonAccion from './BotonAccion.jsx';
import CampoFormulario from './CampoFormulario.jsx';

const { limitesCampos, password: reglasPassword } = PARAMETROS;

/**
 * Pantalla de registro (presentación): el estado y el envío los maneja `pages/Registro.jsx`. La casilla de la
 * política nunca viene marcada: el consentimiento tiene que ser expreso.
 */
export default function FormularioRegistro({
  valores,
  onCambiar,
  aceptaPolitica,
  onAceptarPolitica,
  intentoSinAceptar,
  onEnviar,
  enviando,
  error,
}) {
  const campos = error?.campos ?? {};
  const campo = (nombre, id, etiqueta, propiedades = {}) => (
    <CampoFormulario
      id={`registro-${id}`}
      etiqueta={etiqueta}
      valor={valores[nombre]}
      onCambiar={(valor) => onCambiar(nombre, valor)}
      error={campos[nombre]}
      {...propiedades}
    />
  );

  return (
    <div className="mx-auto" style={{ maxWidth: '32rem' }}>
      <h1 className="h2">{t('registro.titulo')}</h1>
      <p className="text-secondary">{t('registro.descripcion')}</p>
      <Card body>
        <Form onSubmit={onEnviar} noValidate>
          {error && <Alerta variante="danger">{error.mensaje}</Alerta>}
          {campo('nombre_completo', 'nombre', t('registro.nombre'), {
            autoComplete: 'name', required: true, maxLength: limitesCampos.nombre,
          })}
          {campo('email', 'email', t('registro.email'), {
            type: 'email', autoComplete: 'email', inputMode: 'email', required: true, maxLength: limitesCampos.email,
          })}
          {campo('telefono', 'telefono', t('registro.telefono'), {
            type: 'tel', autoComplete: 'tel', inputMode: 'tel', maxLength: limitesCampos.telefono,
            ayuda: t('registro.ayudaTelefono'),
          })}
          {campo('password', 'password', t('registro.password'), {
            type: 'password',
            autoComplete: 'new-password',
            required: true,
            minLength: reglasPassword.largoMinimo,
            maxLength: limitesCampos.password,
            ayuda: t('registro.ayudaPassword', { largo: reglasPassword.largoMinimo }),
          })}
          <Form.Group className="mb-4" controlId="registro-politica">
            <Form.Check
              type="checkbox"
              checked={aceptaPolitica}
              onChange={(evento) => onAceptarPolitica(evento.target.checked)}
              isInvalid={Boolean(campos.acepta_politica_privacidad) || (intentoSinAceptar && !aceptaPolitica)}
              feedback={campos.acepta_politica_privacidad ?? t('registro.debeAceptar')}
              feedbackType="invalid"
              label={(
                <>
                  {t('registro.aceptoPoliticaAntes')}
                  <Link to="/privacidad" target="_blank" rel="noopener">{t('registro.aceptoPoliticaLink')}</Link>
                </>
              )}
            />
          </Form.Group>
          <BotonAccion type="submit" className="w-100" cargando={enviando} textoCargando={t('registro.creando')}>
            {t('registro.enviar')}
          </BotonAccion>
        </Form>
      </Card>
      <p className="mt-3 mb-0 text-center">
        {t('registro.conCuenta')} <Link to="/login">{t('registro.iniciarSesion')}</Link>
      </p>
    </div>
  );
}
