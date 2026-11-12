import Card from 'react-bootstrap/Card';
import Form from 'react-bootstrap/Form';
import { PARAMETROS } from '../config/parametros.js';
import { t } from '../i18n/index.js';
import Alerta from './Alerta.jsx';
import BotonAccion from './BotonAccion.jsx';
import CampoFormulario from './CampoFormulario.jsx';

const { limitesCampos } = PARAMETROS;

/**
 * Datos propios editables (presentación): nombre y teléfono. El correo se muestra sin poder editarse. El estado y el
 * envío los maneja `pages/Perfil.jsx`; `error` es el `ErrorApi` del último intento y `guardado`, si salió bien.
 */
export default function FormularioPerfil({ email, valores, onCambiar, onEnviar, enviando, hayCambios, error, guardado }) {
  const campos = error?.campos ?? {};

  return (
    <Card body>
      <Form onSubmit={onEnviar} noValidate>
        {error && <Alerta variante="danger">{error.mensaje}</Alerta>}
        {guardado && <Alerta variante="success">{t('perfil.guardado')}</Alerta>}
        <CampoFormulario
          id="perfil-email"
          etiqueta={t('perfil.email')}
          type="email"
          valor={email}
          onCambiar={() => {}}
          ayuda={t('perfil.emailAyuda')}
          disabled
        />
        <CampoFormulario
          id="perfil-nombre"
          etiqueta={t('perfil.nombre')}
          autoComplete="name"
          required
          maxLength={limitesCampos.nombre}
          valor={valores.nombre_completo}
          onCambiar={(valor) => onCambiar('nombre_completo', valor)}
          error={campos.nombre_completo}
        />
        <CampoFormulario
          id="perfil-telefono"
          etiqueta={t('perfil.telefono')}
          type="tel"
          autoComplete="tel"
          inputMode="tel"
          maxLength={limitesCampos.telefono}
          ayuda={t('registro.ayudaTelefono')}
          className="mb-4"
          valor={valores.telefono}
          onCambiar={(valor) => onCambiar('telefono', valor)}
          error={campos.telefono}
        />
        <BotonAccion type="submit" cargando={enviando} disabled={!hayCambios} textoCargando={t('perfil.guardando')}>
          {t('comun.guardar')}
        </BotonAccion>
      </Form>
    </Card>
  );
}
