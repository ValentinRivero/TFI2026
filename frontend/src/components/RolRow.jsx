import Button from 'react-bootstrap/Button';
import { describir, ESTADO_REGISTRO, ETIQUETA_ROL, REGISTRO_ACTIVO } from '../config/catalogos.js';
import { t } from '../i18n/index.js';
import { esRolEditable } from '../utils/roles.js';
import BotonAccion from './BotonAccion.jsx';
import Icono from './Icono.jsx';
import IndicadorUsos from './IndicadorUsos.jsx';
import { CeldaTabla } from './TablaApilable.jsx';

const columnas = 'roles.columnas';

/**
 * Fila de un rol: nombre (con el distintivo de rol base), descripción, estado, cuentas que lo usan y permisos. Un rol
 * base solo se consulta y se marca como protegido; uno personalizado activo se edita o se da de baja, y uno de baja se
 * reactiva.
 */
export default function RolRow({ rol, onVerUsos, onVerPermisos, onEditar, onDarDeBaja, onReactivar }) {
  const estado = describir(ESTADO_REGISTRO, rol.estado);
  const activo = rol.estado === REGISTRO_ACTIVO;
  const editable = esRolEditable(rol);
  const etiqueta = ETIQUETA_ROL[rol.nombre];

  return (
    <tr>
      <CeldaTabla etiqueta={t(`${columnas}.nombre`)}>
        <div>{etiqueta ?? rol.nombre}</div>
        {etiqueta && <div className="small text-secondary num">{rol.nombre}</div>}
        {rol.es_base && <span className="badge badge-info mt-1">{t('roles.rolBase')}</span>}
      </CeldaTabla>
      <CeldaTabla etiqueta={t(`${columnas}.descripcion`)}>{rol.descripcion || '-'}</CeldaTabla>
      <CeldaTabla etiqueta={t(`${columnas}.estado`)}>
        <span className={`badge ${estado.badge}`}>{estado.etiqueta}</span>
      </CeldaTabla>
      <CeldaTabla etiqueta={t(`${columnas}.usos`)} className="num">
        <IndicadorUsos
          texto={t(rol.usos === 1 ? 'roles.usosUno' : 'roles.usosVarios', { cantidad: rol.usos })}
          usos={rol.usos}
          nombre={rol.nombre}
          onVer={() => onVerUsos(rol)}
        />
      </CeldaTabla>
      <CeldaTabla etiqueta={t(`${columnas}.permisos`)}>
        <Button size="sm" variant="outline-secondary" onClick={() => onVerPermisos(rol)}>
          {t('roles.verPermisos', { cantidad: rol.permisos.length })}
        </Button>
      </CeldaTabla>
      <CeldaTabla etiqueta="" className="text-lg-end">
        {!editable && (
          <span className="small text-secondary d-inline-flex align-items-center gap-1">
            <Icono nombre="candado" tamano={16} />
            {t('roles.protegido')}
          </span>
        )}
        {editable && (
          <div className="d-flex flex-wrap gap-2 justify-content-lg-end">
            {activo ? (
              <>
                <Button size="sm" variant="outline-secondary" onClick={() => onEditar(rol)}>{t('comun.editar')}</Button>
                <Button size="sm" variant="outline-danger" onClick={() => onDarDeBaja(rol)}>{t('roles.darDeBaja')}</Button>
              </>
            ) : (
              <BotonAccion size="sm" variant="outline-secondary" onClick={() => onReactivar(rol)}>
                {t('roles.reactivar')}
              </BotonAccion>
            )}
          </div>
        )}
      </CeldaTabla>
    </tr>
  );
}
