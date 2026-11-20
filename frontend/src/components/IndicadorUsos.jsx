import Button from 'react-bootstrap/Button';
import { t } from '../i18n/index.js';

/**
 * Cantidad de registros que usan un ítem. Con usos es un botón que abre el detalle de dónde está en uso; sin usos es
 * solo el texto. `texto` es la cantidad ya redactada (`3 canchas`) y `nombre`, el ítem, para el nombre accesible del botón.
 */
export default function IndicadorUsos({ texto, usos, nombre, onVer }) {
  if (usos === 0) return <span>{texto}</span>;

  return (
    <Button
      variant="link"
      className="p-0 text-start"
      onClick={onVer}
      aria-label={t('usos.verDetalle', { nombre, cantidad: texto })}
    >
      {texto}
    </Button>
  );
}
