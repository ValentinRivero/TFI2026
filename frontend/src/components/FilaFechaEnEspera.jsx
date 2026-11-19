import Button from 'react-bootstrap/Button';
import { DIA_SEMANA } from '../config/catalogos.js';
import { t } from '../i18n/index.js';
import { formatearFechaLarga, formatearHora } from '../utils/formatos.js';
import { CeldaTabla } from './TablaApilable.jsx';

const columnas = 'turnosFijos.espera.columnas';

/**
 * Fila de una fecha de turno fijo en espera por una excepción horaria: turno, fecha, motivo de la excepción y las dos
 * decisiones posibles. `fila` es `{ turno, fecha, motivo }` (ver `aFilasEnEspera`).
 */
export default function FilaFechaEnEspera({ fila, onMantener, onCancelar }) {
  const { turno, fecha, motivo } = fila;

  return (
    <tr>
      <CeldaTabla etiqueta={t(`${columnas}.turno`)}>
        <div>{turno.cancha_nombre}</div>
        <div className="small text-secondary num">
          {DIA_SEMANA[turno.dia_semana]?.etiqueta ?? turno.dia_semana}, {formatearHora(turno.hora_inicio)} - {formatearHora(turno.hora_fin)}
        </div>
      </CeldaTabla>
      <CeldaTabla etiqueta={t(`${columnas}.cliente`)}>{turno.cliente?.nombre || '-'}</CeldaTabla>
      <CeldaTabla etiqueta={t(`${columnas}.fecha`)} className="num">{formatearFechaLarga(fecha)}</CeldaTabla>
      <CeldaTabla etiqueta={t(`${columnas}.motivo`)}>{motivo || '-'}</CeldaTabla>
      <CeldaTabla etiqueta="" className="text-lg-end">
        <div className="d-flex flex-wrap justify-content-lg-end gap-2">
          <Button size="sm" variant="outline-primary" onClick={() => onMantener(fila)}>{t('turnosFijos.espera.mantener')}</Button>
          <Button size="sm" variant="outline-danger" onClick={() => onCancelar(fila)}>{t('turnosFijos.espera.cancelar')}</Button>
        </div>
      </CeldaTabla>
    </tr>
  );
}
