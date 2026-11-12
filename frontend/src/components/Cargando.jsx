import { t } from '../i18n/index.js';

/**
 * Único lugar que conoce el aspecto del indicador de carga. Para reemplazarlo por una imagen o una animación propia
 * alcanza con cambiar esta función (y, si hace falta, las reglas `.cargando-*` de tema.css): ningún otro archivo
 * depende de cómo se ve.
 */
function Indicador({ chico = false }) {
  return <span className={`cargando-indicador${chico ? ' cargando-indicador-chico' : ''}`} aria-hidden="true" />;
}

/**
 * Estado de carga de toda petición asíncrona.
 * - `pantalla`: ocupa el espacio de una página (carga de rutas).
 * - `seccion`: reemplaza el contenido de un bloque mientras llegan sus datos.
 * - `boton`: indicador chico dentro de un botón.
 * - `inline`: indicador chico junto a un texto.
 */
export default function Cargando({ variante = 'seccion', texto, className = '' }) {
  const leyenda = texto ?? t('comun.cargando');

  if (variante === 'boton' || variante === 'inline') {
    return (
      <span role="status" className={`d-inline-flex align-items-center gap-2 ${className}`.trim()}>
        <Indicador chico />
        {variante === 'inline' ? <span>{leyenda}</span> : <span className="visually-hidden">{leyenda}</span>}
      </span>
    );
  }

  return (
    <div role="status" className={`${variante === 'pantalla' ? 'cargando-pantalla' : 'cargando-seccion'} ${className}`.trim()}>
      <Indicador />
      <span>{leyenda}</span>
    </div>
  );
}
