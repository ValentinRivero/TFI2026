import Button from 'react-bootstrap/Button';
import { describir, ESTADO_USUARIO, ETIQUETA_ROL } from '../config/catalogos.js';
import { t } from '../i18n/index.js';
import { formatearFechaHora } from '../utils/formatos.js';
import { CeldaTabla } from './TablaApilable.jsx';

const columnas = 'usuarios.columnas';

/** Fila de una cuenta: id, datos de contacto, rol, complejo operado (si es operador), estado, alta y la acción de abrir su ficha. */
export default function UsuarioRow({ usuario, onAbrir }) {
  const estado = describir(ESTADO_USUARIO, usuario.estado);

  return (
    <tr>
      <CeldaTabla etiqueta={t(`${columnas}.id`)} className="num">{usuario.id}</CeldaTabla>
      <CeldaTabla etiqueta={t(`${columnas}.cuenta`)}>
        <div>{usuario.nombre_completo}</div>
        <div className="small text-secondary">{usuario.email}</div>
        {usuario.telefono && <div className="small text-secondary num">{usuario.telefono}</div>}
      </CeldaTabla>
      <CeldaTabla etiqueta={t(`${columnas}.rol`)}>{ETIQUETA_ROL[usuario.rol] ?? usuario.rol}</CeldaTabla>
      <CeldaTabla etiqueta={t(`${columnas}.complejo`)}>{usuario.complejo_operado_nombre || '-'}</CeldaTabla>
      <CeldaTabla etiqueta={t(`${columnas}.estado`)}>
        <span className={`badge ${estado.badge}`}>{estado.etiqueta}</span>
      </CeldaTabla>
      <CeldaTabla etiqueta={t(`${columnas}.alta`)} className="num">{formatearFechaHora(usuario.fecha_creacion)}</CeldaTabla>
      <CeldaTabla etiqueta="" className="text-lg-end">
        <Button size="sm" variant="outline-secondary" onClick={() => onAbrir(usuario)}>{t('usuarios.verFicha')}</Button>
      </CeldaTabla>
    </tr>
  );
}
