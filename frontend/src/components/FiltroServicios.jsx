import { useId } from 'react';
import Button from 'react-bootstrap/Button';
import Form from 'react-bootstrap/Form';
import { t } from '../i18n/index.js';
import FiltroDesplegable from './FiltroDesplegable.jsx';
import Icono from './Icono.jsx';

/**
 * Filtro desplegable de selección múltiple: una casilla por servicio y el menú queda abierto al marcar, así se
 * combinan varios sin reabrirlo. Se cierra al hacer clic afuera o con Escape (lo resuelve `Dropdown`). Recibe las
 * opciones y los ids elegidos (texto) por props y avisa con `onAlternar(id)` y `onLimpiar()`.
 */
export default function FiltroServicios({ servicios, elegidos, onAlternar, onLimpiar, className = '' }) {
  const idCampo = useId();
  const cantidad = elegidos.length;

  const pie = (
    <>
      <span className="text-secondary small num">{t('filtros.seleccionados', { cantidad })}</span>
      <Button variant="outline-secondary" size="sm" disabled={cantidad === 0} onClick={onLimpiar}>
        <Icono nombre="cerrar" tamano={14} />
        {t('filtros.limpiarServicios')}
      </Button>
    </>
  );

  return (
    <FiltroDesplegable
      etiqueta={t('filtros.servicios')}
      textoBoton={cantidad > 0 ? t('filtros.serviciosConCantidad', { cantidad }) : t('filtros.cualquierServicio')}
      pie={pie}
      className={className}
    >
      <div role="group" aria-label={t('filtros.servicios')}>
        {servicios.map(({ id, nombre }) => (
          <Form.Check
            key={id}
            type="checkbox"
            id={`${idCampo}-servicio-${id}`}
            className="filtro-opcion filtro-opcion-casilla"
            label={nombre}
            checked={elegidos.includes(String(id))}
            onChange={() => onAlternar(id)}
          />
        ))}
      </div>
    </FiltroDesplegable>
  );
}
