import Button from 'react-bootstrap/Button';
import { describir, ESTADO_CANCHA } from '../config/catalogos.js';
import { t } from '../i18n/index.js';
import { describirCancha } from '../utils/cancha.js';
import { formatearPrecio } from '../utils/formatos.js';
import { CeldaTabla } from './TablaApilable.jsx';

/**
 * Fila de una cancha del panel: datos, estado y acciones. Los horarios los puede abrir cualquier rol (el operador
 * en modo consulta); editar y dar de baja solo aparecen si `puedeAdministrar`.
 */
export default function CanchaRow({ cancha, puedeAdministrar, onHorarios, onEditar, onBaja }) {
  const { etiqueta, badge } = describir(ESTADO_CANCHA, cancha.estado);
  const { superficie, cobertura, iluminacion, duracion } = describirCancha(cancha);
  const columnas = 'gestionCanchas.columnas';

  return (
    <tr>
      <CeldaTabla etiqueta={t(`${columnas}.nombre`)}>
        <span className="fw-semibold">{cancha.nombre}</span>
      </CeldaTabla>
      <CeldaTabla etiqueta={t(`${columnas}.deporte`)}>{cancha.deporte_nombre}</CeldaTabla>
      <CeldaTabla etiqueta={t(`${columnas}.caracteristicas`)}>
        {superficie} - {cobertura} - {iluminacion}
      </CeldaTabla>
      <CeldaTabla etiqueta={t(`${columnas}.turno`)} className="num">{duracion}</CeldaTabla>
      <CeldaTabla etiqueta={t(`${columnas}.precio`)} className="num">{formatearPrecio(cancha.precio_base)}</CeldaTabla>
      <CeldaTabla etiqueta={t(`${columnas}.estado`)}>
        <span className={`badge ${badge}`}>{etiqueta}</span>
      </CeldaTabla>
      <CeldaTabla etiqueta="" className="text-lg-end">
        <div className="d-flex flex-wrap gap-2 justify-content-end">
          <Button size="sm" variant="outline-primary" onClick={() => onHorarios(cancha)}>
            {t('gestionCanchas.horarios')}
          </Button>
          {puedeAdministrar && (
            <>
              <Button size="sm" variant="outline-secondary" onClick={() => onEditar(cancha)}>
                {t('gestionCanchas.editar')}
              </Button>
              <Button size="sm" variant="outline-danger" onClick={() => onBaja(cancha)}>
                {t('gestionCanchas.darDeBaja')}
              </Button>
            </>
          )}
        </div>
      </CeldaTabla>
    </tr>
  );
}
