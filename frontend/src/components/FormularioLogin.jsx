import Card from 'react-bootstrap/Card';
import Form from 'react-bootstrap/Form';
import { Link } from 'react-router-dom';
import { PARAMETROS } from '../config/parametros.js';
import { t } from '../i18n/index.js';
import Alerta from './Alerta.jsx';
import BotonAccion from './BotonAccion.jsx';
import CampoFormulario from './CampoFormulario.jsx';

/** Pantalla de inicio de sesión (presentación): el estado y el envío los maneja `pages/Login.jsx`. */
export default function FormularioLogin({ valores, onCambiar, onEnviar, enviando, error, aviso }) {
  return (
    <div className="mx-auto" style={{ maxWidth: '28rem' }}>
      <h1 className="h2">{t('login.titulo')}</h1>
      <p className="text-secondary">{t('login.descripcion')}</p>
      {aviso && <Alerta variante="info">{aviso}</Alerta>}
      <Card body>
        <Form onSubmit={onEnviar} noValidate>
          {error && <Alerta variante="danger">{error.mensaje}</Alerta>}
          <CampoFormulario
            id="login-email"
            etiqueta={t('login.email')}
            type="email"
            autoComplete="email"
            inputMode="email"
            required
            maxLength={PARAMETROS.limitesCampos.email}
            valor={valores.email}
            onCambiar={(valor) => onCambiar('email', valor)}
          />
          <CampoFormulario
            id="login-password"
            etiqueta={t('login.password')}
            type="password"
            autoComplete="current-password"
            required
            maxLength={PARAMETROS.limitesCampos.password}
            className="mb-4"
            valor={valores.password}
            onCambiar={(valor) => onCambiar('password', valor)}
          />
          <BotonAccion type="submit" className="w-100" cargando={enviando} textoCargando={t('login.ingresando')}>
            {t('login.enviar')}
          </BotonAccion>
        </Form>
      </Card>
      <p className="mt-3 mb-0 text-center">
        {t('login.sinCuenta')} <Link to="/registro">{t('login.crearCuenta')}</Link>
      </p>
    </div>
  );
}
