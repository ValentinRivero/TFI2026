import Form from 'react-bootstrap/Form';
import { describir, ESTADO_USUARIO, ETIQUETA_ROL, opcionesDe, ROL } from '../config/catalogos.js';
import { PARAMETROS } from '../config/parametros.js';
import { t } from '../i18n/index.js';
import Alerta from './Alerta.jsx';
import CampoFormulario from './CampoFormulario.jsx';
import CampoSelect from './CampoSelect.jsx';
import ModalConfirmar from './ModalConfirmar.jsx';

const OPCIONES_ROL = opcionesDe(ETIQUETA_ROL);
const OPCIONES_ESTADO = opcionesDe(ESTADO_USUARIO);

/**
 * Ficha de una cuenta (presentación). Se abre en modo consulta, con todos los campos deshabilitados, y recién con
 * "Habilitar edición" se pueden modificar nombre, teléfono, rol, complejo operado (solo para operadores) y estado;
 * "Cancelar edición" vuelve a la consulta sin guardar. Las restricciones de negocio las valida el backend (`400`): el
 * mensaje general se muestra arriba y el de un campo, bajo ese campo. `ficha` es lo que devuelve `useUsuarios`.
 */
export default function ModalFichaUsuario({ ficha }) {
  const { usuario, valores, errores, error, enviando, editando } = ficha;
  const campo = (nombre) => ({
    valor: valores?.[nombre] ?? '',
    onCambiar: (valor) => ficha.cambiar(nombre, valor),
    error: errores[nombre],
    tabIndex: editando ? undefined : -1,
  });
  const estado = describir(ESTADO_USUARIO, usuario?.estado);

  return (
    <ModalConfirmar
      mostrar={Boolean(usuario)}
      titulo={editando ? t('usuarios.editarTitulo') : t('usuarios.fichaTitulo')}
      textoConfirmar={editando ? t('comun.guardar') : t('usuarios.habilitarEdicion')}
      textoCancelar={editando ? t('usuarios.cancelarEdicion') : t('comun.cerrar')}
      confirmarDeshabilitado={enviando}
      onConfirmar={editando ? ficha.guardar : ficha.habilitarEdicion}
      onCancelar={editando ? ficha.cancelarEdicion : ficha.cerrar}
    >
      {usuario && valores && (
        <Form onSubmit={ficha.guardar} noValidate>
          {error && <Alerta variante="danger">{error.mensaje}</Alerta>}
          <p className="text-secondary d-flex flex-wrap align-items-center gap-2">
            <span className="num">{t('usuarios.numero', { id: usuario.id })}</span>
            <span className={`badge ${estado.badge}`}>{estado.etiqueta}</span>
            <span>{usuario.email}</span>
          </p>
          {!editando && <p className="small text-secondary">{t('usuarios.modoConsulta')}</p>}
          <fieldset disabled={!editando} className={`border-0 p-0 m-0${editando ? '' : ' solo-lectura'}`}>
            <CampoFormulario
              id="usuario-nombre"
              etiqueta={t('usuarios.nombre')}
              maxLength={PARAMETROS.limitesCampos.nombre}
              {...campo('nombre_completo')}
            />
            <CampoFormulario
              id="usuario-telefono"
              etiqueta={t('usuarios.telefono')}
              type="tel"
              inputMode="tel"
              maxLength={PARAMETROS.limitesCampos.telefono}
              {...campo('telefono')}
            />
            <CampoSelect id="usuario-rol" etiqueta={t('usuarios.rol')} opciones={OPCIONES_ROL} {...campo('rol')} />
            {valores.rol === ROL.OPERADOR && (
              <CampoSelect
                id="usuario-complejo"
                etiqueta={t('usuarios.complejoOperado')}
                placeholder={t('usuarios.sinComplejo')}
                opciones={ficha.complejos.map((complejo) => ({ valor: String(complejo.id), etiqueta: complejo.nombre }))}
                {...campo('complejo_operado')}
              />
            )}
            <CampoSelect
              id="usuario-estado"
              etiqueta={t('usuarios.estado')}
              opciones={OPCIONES_ESTADO}
              ayuda={editando ? t('usuarios.ayudaEstado') : undefined}
              className="mb-0"
              {...campo('estado')}
            />
          </fieldset>
          <button type="submit" className="d-none" tabIndex={-1} aria-hidden="true" disabled={!editando} />
        </Form>
      )}
    </ModalConfirmar>
  );
}
