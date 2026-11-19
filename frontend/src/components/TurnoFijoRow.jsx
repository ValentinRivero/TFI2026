import Button from 'react-bootstrap/Button';
import { describir, DIA_SEMANA, ESTADO_TURNO_FIJO, TURNO_FIJO_PAUSADO } from '../config/catalogos.js';
import { t } from '../i18n/index.js';
import { formatearFechaCorta, formatearHora } from '../utils/formatos.js';
import { CeldaTabla } from './TablaApilable.jsx';

const columnas = 'turnosFijos.columnas';

/**
 * Fila de un turno fijo: cancha, día y horario, vigencia, cliente, estado (con el conflicto de operatoria y las
 * fechas en espera, si las hay) y las acciones: registrar fechas, editar el horario, pausar o reanudar y dar de baja.
 */
export default function TurnoFijoRow({ turno, ocupado, onEditar, onRegistrarFechas, onAlternarPausa, onBaja }) {
  const { etiqueta, badge } = describir(ESTADO_TURNO_FIJO, turno.estado);
  const pausado = turno.estado === TURNO_FIJO_PAUSADO;
  const enEspera = turno.fechas_en_espera?.length ?? 0;

  return (
    <tr>
      <CeldaTabla etiqueta={t(`${columnas}.cancha`)}>{turno.cancha_nombre}</CeldaTabla>
      <CeldaTabla etiqueta={t(`${columnas}.horario`)} className="num">
        <div>{DIA_SEMANA[turno.dia_semana]?.etiqueta ?? turno.dia_semana}</div>
        <div>{t('grilla.resumenHorarioValor', { inicio: formatearHora(turno.hora_inicio), fin: formatearHora(turno.hora_fin) })}</div>
      </CeldaTabla>
      <CeldaTabla etiqueta={t(`${columnas}.vigencia`)} className="num">
        {turno.fecha_fin_vigencia
          ? t('turnosFijos.vigenciaRango', {
            desde: formatearFechaCorta(turno.fecha_inicio_vigencia),
            hasta: formatearFechaCorta(turno.fecha_fin_vigencia),
          })
          : t('turnosFijos.vigenciaSinFin', { desde: formatearFechaCorta(turno.fecha_inicio_vigencia) })}
      </CeldaTabla>
      <CeldaTabla etiqueta={t(`${columnas}.cliente`)}>
        <div>{turno.cliente?.nombre || '-'}</div>
        {turno.cliente?.telefono && <div className="small text-secondary num">{turno.cliente.telefono}</div>}
      </CeldaTabla>
      <CeldaTabla etiqueta={t(`${columnas}.estado`)}>
        <span className={`badge ${badge}`}>{etiqueta}</span>
        {enEspera > 0 && <div className="small text-secondary mt-1">{t('turnosFijos.fechasEnEspera', { cantidad: enEspera })}</div>}
        {turno.conflicto_operatoria && (
          <div className="small text-danger mt-1">{t('agenda.conflicto', { motivo: turno.conflicto_operatoria })}</div>
        )}
      </CeldaTabla>
      <CeldaTabla etiqueta="" className="text-lg-end">
        <div className="d-flex flex-wrap justify-content-lg-end gap-2">
          <Button size="sm" variant="outline-primary" disabled={ocupado} onClick={() => onRegistrarFechas(turno)}>
            {t('turnosFijos.registrarFechas')}
          </Button>
          <Button size="sm" variant="outline-secondary" disabled={ocupado} onClick={() => onEditar(turno)}>
            {t('turnosFijos.editar')}
          </Button>
          <Button size="sm" variant="outline-secondary" disabled={ocupado} onClick={() => onAlternarPausa(turno)}>
            {pausado ? t('turnosFijos.reanudar') : t('turnosFijos.pausar')}
          </Button>
          <Button size="sm" variant="outline-danger" disabled={ocupado} onClick={() => onBaja(turno)}>
            {t('turnosFijos.darDeBaja')}
          </Button>
        </div>
      </CeldaTabla>
    </tr>
  );
}
