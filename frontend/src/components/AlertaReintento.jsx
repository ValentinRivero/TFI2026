import Button from 'react-bootstrap/Button';
import { t } from '../i18n/index.js';
import Alerta from './Alerta.jsx';

/** Error de una consulta con su mensaje y el botón "Reintentar"; `children` suma otras acciones. */
export default function AlertaReintento({ titulo, mensaje, onReintentar, children }) {
  return (
    <Alerta titulo={titulo}>
      <p className="mb-2">{mensaje}</p>
      <div className="d-flex flex-wrap gap-2">
        <Button variant="outline-secondary" onClick={onReintentar}>{t('comun.reintentar')}</Button>
        {children}
      </div>
    </Alerta>
  );
}
