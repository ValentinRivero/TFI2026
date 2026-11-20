import Button from 'react-bootstrap/Button';
import { describir, ESTADO_REGISTRO, REGISTRO_ACTIVO } from '../config/catalogos.js';
import { t } from '../i18n/index.js';
import { textoDeUsos } from '../utils/catalogoSistema.js';
import BotonAccion from './BotonAccion.jsx';
import IndicadorUsos from './IndicadorUsos.jsx';
import { CeldaTabla } from './TablaApilable.jsx';

const columnas = 'catalogoSistema.columnas';

/**
 * Fila de un deporte o servicio: nombre, estado, cuántos registros vigentes lo usan y las acciones. Un ítem activo se
 * edita o se da de baja; uno de baja solo se reactiva. Los usos, si los hay, abren el detalle. `recurso` es una clave de `CATALOGOS_SISTEMA`.
 */
export default function CatalogoItemRow({ recurso, item, onVerUsos, onEditar, onDarDeBaja, onReactivar }) {
  const estado = describir(ESTADO_REGISTRO, item.estado);
  const activo = item.estado === REGISTRO_ACTIVO;

  return (
    <tr>
      <CeldaTabla etiqueta={t(`${columnas}.nombre`)}>{item.nombre}</CeldaTabla>
      <CeldaTabla etiqueta={t(`${columnas}.estado`)}>
        <span className={`badge ${estado.badge}`}>{estado.etiqueta}</span>
      </CeldaTabla>
      <CeldaTabla etiqueta={t(`${columnas}.usos`)} className="num">
        <IndicadorUsos texto={textoDeUsos(recurso, item.usos)} usos={item.usos} nombre={item.nombre} onVer={() => onVerUsos(item)} />
      </CeldaTabla>
      <CeldaTabla etiqueta="" className="text-lg-end">
        <div className="d-flex flex-wrap gap-2 justify-content-lg-end">
          {activo ? (
            <>
              <Button size="sm" variant="outline-secondary" onClick={() => onEditar(item)}>{t('comun.editar')}</Button>
              <Button size="sm" variant="outline-danger" onClick={() => onDarDeBaja(item)}>
                {t('catalogoSistema.darDeBaja')}
              </Button>
            </>
          ) : (
            <BotonAccion size="sm" variant="outline-secondary" onClick={() => onReactivar(item)}>
              {t('catalogoSistema.reactivar')}
            </BotonAccion>
          )}
        </div>
      </CeldaTabla>
    </tr>
  );
}
