import Button from 'react-bootstrap/Button';
import useCopiar from '../hooks/useCopiar.js';
import { t } from '../i18n/index.js';
import Icono from './Icono.jsx';

/**
 * Un dato para transferir (alias, CBU o CVU) con su botón de copiar. El resultado ("Copiado" o el aviso de que no se
 * pudo) se anuncia a lectores de pantalla y se muestra unos segundos en el botón.
 */
export default function FilaCopiable({ etiqueta, valor, textoBoton, className = '' }) {
  const { copiar, copiado, fallo } = useCopiar(valor);

  return (
    <div className={className}>
      <div className="d-flex flex-wrap align-items-center gap-3">
        <div>
          <div className="small text-secondary">{etiqueta}</div>
          <strong className="fs-5 alias-transferencia">{valor}</strong>
        </div>
        <Button variant={copiado ? 'success' : 'outline-primary'} onClick={copiar}>
          <Icono nombre={copiado ? 'check' : 'copiar'} />
          {copiado ? t('pagos.aliasCopiado') : textoBoton}
        </Button>
      </div>
      <p role="status" className={fallo ? 'small text-danger mt-2 mb-0' : 'visually-hidden'}>
        {copiado && t('pagos.aliasCopiado')}
        {fallo && t('pagos.errorCopiar')}
      </p>
    </div>
  );
}
