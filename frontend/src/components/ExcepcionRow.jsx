import Button from 'react-bootstrap/Button';
import { describir, ES_DIA_COMPLETO, TIPO_MOTIVO_EXCEPCION } from '../config/catalogos.js';
import { t } from '../i18n/index.js';
import { formatearFechaCorta, formatearHora } from '../utils/formatos.js';
import { CeldaTabla } from './TablaApilable.jsx';

const columnas = 'excepciones.columnas';

/** Fila de una excepción: alcance (complejo o cancha), fechas, horario, motivo, descripción y baja. */
export default function ExcepcionRow({ excepcion, onBaja }) {
  const { etiqueta, badge } = describir(TIPO_MOTIVO_EXCEPCION, excepcion.tipo_motivo);
  const diaCompleto = excepcion.es_dia_completo === ES_DIA_COMPLETO;
  const mismoDia = excepcion.fecha_inicio === excepcion.fecha_fin;

  return (
    <tr>
      <CeldaTabla etiqueta={t(`${columnas}.alcance`)}>
        {excepcion.cancha ? excepcion.cancha_nombre : t('excepciones.todoElComplejo')}
      </CeldaTabla>
      <CeldaTabla etiqueta={t(`${columnas}.fechas`)} className="num">
        {mismoDia
          ? formatearFechaCorta(excepcion.fecha_inicio)
          : t('excepciones.rango', {
            desde: formatearFechaCorta(excepcion.fecha_inicio),
            hasta: formatearFechaCorta(excepcion.fecha_fin),
          })}
      </CeldaTabla>
      <CeldaTabla etiqueta={t(`${columnas}.horario`)} className="num">
        {diaCompleto
          ? t('excepciones.todoElDia')
          : t('grilla.resumenHorarioValor', {
            inicio: formatearHora(excepcion.hora_inicio),
            fin: formatearHora(excepcion.hora_fin),
          })}
      </CeldaTabla>
      <CeldaTabla etiqueta={t(`${columnas}.motivo`)}>
        <span className={`badge ${badge}`}>{etiqueta}</span>
      </CeldaTabla>
      <CeldaTabla etiqueta={t(`${columnas}.descripcion`)}>{excepcion.descripcion || '-'}</CeldaTabla>
      <CeldaTabla etiqueta="" className="text-lg-end">
        <Button size="sm" variant="outline-danger" onClick={() => onBaja(excepcion)}>
          {t('excepciones.darDeBaja')}
        </Button>
      </CeldaTabla>
    </tr>
  );
}
