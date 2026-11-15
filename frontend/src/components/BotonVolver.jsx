import { Link, useLocation, useNavigate } from 'react-router-dom';
import { t } from '../i18n/index.js';
import Icono from './Icono.jsx';

/**
 * Botón para volver a la pantalla anterior. Si la persona llegó navegando dentro de la aplicación vuelve atrás en el
 * historial (así el catálogo conserva sus filtros); si abrió el enlace directamente, va a `destino`.
 */
export default function BotonVolver({ destino = '/', children, className = '' }) {
  const ubicacion = useLocation();
  const navegar = useNavigate();
  const hayHistorial = ubicacion.key !== 'default';

  const volver = (evento) => {
    if (!hayHistorial) return;
    evento.preventDefault();
    navegar(-1);
  };

  return (
    <Link to={destino} onClick={volver} className={`boton-volver ${className}`.trim()}>
      <Icono nombre="anterior" tamano={18} />
      {children ?? t('comun.volver')}
    </Link>
  );
}
