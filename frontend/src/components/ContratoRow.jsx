import Button from 'react-bootstrap/Button';
import { describir, ESTADO_CONTRATO, ESTADO_USUARIO } from '../config/catalogos.js';
import { t } from '../i18n/index.js';
import { formatearFechaHora } from '../utils/formatos.js';
import { CeldaTabla } from './TablaApilable.jsx';

const columnas = 'contratos.columnas';
const ESTADO_ACTIVO = 1;

/**
 * Fila de un contrato: id del complejo, nombre y dirección, propietario (con una advertencia si su cuenta no está activa), estado del contrato,
 * fecha de alta y la acción de cambiar el estado.
 */
export default function ContratoRow({ contrato, onCambiarEstado }) {
  const estado = describir(ESTADO_CONTRATO, contrato.estado_contrato);
  const { propietario } = contrato;
  const cuenta = describir(ESTADO_USUARIO, propietario?.estado);

  return (
    <tr>
      <CeldaTabla etiqueta={t(`${columnas}.id`)} className="num">{contrato.id}</CeldaTabla>
      <CeldaTabla etiqueta={t(`${columnas}.complejo`)}>
        <div>{contrato.nombre}</div>
        <div className="small text-secondary">{contrato.direccion}</div>
      </CeldaTabla>
      <CeldaTabla etiqueta={t(`${columnas}.propietario`)}>
        <div>{propietario?.nombre_completo ?? '-'}</div>
        {propietario?.email && <div className="small text-secondary">{propietario.email}</div>}
        {propietario && propietario.estado !== ESTADO_ACTIVO && (
          <span className={`badge ${cuenta.badge} mt-1`}>{t('contratos.cuentaPropietario', { estado: cuenta.etiqueta })}</span>
        )}
      </CeldaTabla>
      <CeldaTabla etiqueta={t(`${columnas}.estado`)}>
        <span className={`badge ${estado.badge}`}>{estado.etiqueta}</span>
      </CeldaTabla>
      <CeldaTabla etiqueta={t(`${columnas}.alta`)} className="num">{formatearFechaHora(contrato.fecha_creacion)}</CeldaTabla>
      <CeldaTabla etiqueta="" className="text-lg-end">
        <Button size="sm" variant="outline-secondary" onClick={() => onCambiarEstado(contrato)}>
          {t('contratos.cambiarEstado')}
        </Button>
      </CeldaTabla>
    </tr>
  );
}
