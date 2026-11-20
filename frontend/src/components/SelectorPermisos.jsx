import Form from 'react-bootstrap/Form';
import { describirModulo } from '../config/catalogos.js';
import { t } from '../i18n/index.js';
import { agruparPermisosPorModulo } from '../utils/roles.js';

/**
 * Permisos agrupados por módulo, con una casilla por permiso. Los que el backend marca `asignable: false` (exclusivos
 * de la plataforma) se ven deshabilitados y con su aviso, porque un rol personalizado nunca los recibe. En `soloLectura`
 * ninguna casilla se puede cambiar: sirve para inspeccionar los permisos de un rol protegido.
 */
export default function SelectorPermisos({ permisos, seleccionados, onAlternar, soloLectura = false, idBase = 'permiso' }) {
  return (
    <div>
      {agruparPermisosPorModulo(permisos).map(({ modulo, permisos: delModulo }) => (
        <fieldset key={modulo} className="mb-3">
          <legend className="h6 text-secondary">{describirModulo(modulo)}</legend>
          {delModulo.map((permiso) => {
            const reservado = permiso.asignable === false;
            return (
              <Form.Check
                key={permiso.id}
                type="checkbox"
                id={`${idBase}-${permiso.id}`}
                checked={seleccionados.includes(permiso.id)}
                disabled={soloLectura || reservado}
                onChange={() => onAlternar?.(permiso.id)}
                label={(
                  <>
                    {permiso.nombre}
                    <span className="d-block small text-secondary">{permiso.codigo}</span>
                    {reservado && !soloLectura && (
                      <span className="d-block small text-secondary">{t('roles.permisoReservado')}</span>
                    )}
                  </>
                )}
                className="mb-2"
              />
            );
          })}
        </fieldset>
      ))}
    </div>
  );
}
