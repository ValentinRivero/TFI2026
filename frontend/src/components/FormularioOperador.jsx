import Form from 'react-bootstrap/Form';
import { PARAMETROS } from '../config/parametros.js';
import { t } from '../i18n/index.js';
import BotonAccion from './BotonAccion.jsx';
import CampoFormulario from './CampoFormulario.jsx';

/**
 * Vinculación de un operador por el correo exacto de su cuenta. El mensaje de "no disponible" del backend es el mismo
 * para una cuenta inexistente o ajena (no permite averiguar qué cuentas existen) y se muestra tal cual bajo el campo.
 */
export default function FormularioOperador({ email, onCambiar, onEnviar, enviando, error }) {
  const mensaje = error?.campos?.email ?? error?.mensaje;

  return (
    <Form onSubmit={onEnviar} noValidate className="mb-4">
      <div className="d-flex flex-wrap align-items-start gap-2">
        <div className="campo-operador">
          <CampoFormulario
            id="operador-email"
            etiqueta={t('operadores.email')}
            type="email"
            autoComplete="off"
            maxLength={PARAMETROS.limitesCampos.email}
            valor={email}
            onCambiar={onCambiar}
            error={mensaje}
            ayuda={t('operadores.ayudaEmail')}
            className="mb-0"
          />
        </div>
        <BotonAccion
          type="submit"
          cargando={enviando}
          disabled={email.trim() === ''}
          textoCargando={t('operadores.vinculando')}
          className="boton-alineado-campo"
        >
          {t('operadores.vincular')}
        </BotonAccion>
      </div>
    </Form>
  );
}
