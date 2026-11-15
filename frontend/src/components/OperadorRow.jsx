import Button from 'react-bootstrap/Button';
import { t } from '../i18n/index.js';
import { CeldaTabla } from './TablaApilable.jsx';

/** Fila de un operador vinculado: nombre, correo y teléfono (solo los ve quien administra el complejo) y desvincular. */
export default function OperadorRow({ operador, onDesvincular }) {
  return (
    <tr>
      <CeldaTabla etiqueta={t('operadores.nombre')}>{operador.nombre_completo}</CeldaTabla>
      <CeldaTabla etiqueta={t('operadores.correo')}>{operador.email}</CeldaTabla>
      <CeldaTabla etiqueta={t('operadores.telefono')} className="num">{operador.telefono || '-'}</CeldaTabla>
      <CeldaTabla etiqueta="" className="text-lg-end">
        <Button size="sm" variant="outline-danger" onClick={() => onDesvincular(operador)}>
          {t('operadores.desvincular')}
        </Button>
      </CeldaTabla>
    </tr>
  );
}
