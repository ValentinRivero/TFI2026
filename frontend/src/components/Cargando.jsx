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
 * Indicador de la carga entre pantallas (variante `superpuesto`). Está separado del spinner de botones y secciones
 * para poder reemplazarlo por una imagen o una animación propia sin tocar el resto: alcanza con cambiar esta función
 * y las reglas `.cargando-transicion` de tema.css.
 */
function IndicadorTransicion() {
  return <span className="cargando-transicion" aria-hidden="true" />;
}

/**
 * Estado de carga de toda petición asíncrona.
 * - `superpuesto`: capa translúcida sobre el área de contenido (debajo de la barra superior) mientras carga una
 *   pantalla; aparece con una demora corta para que los cambios instantáneos no parpadeen. El contenedor debe tener
 *   `position: relative`.
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

  if (variante === 'superpuesto') {
    return (
      <div role="status" className={`cargando-superpuesto ${className}`.trim()}>
        <IndicadorTransicion />
        <span className="visually-hidden">{leyenda}</span>
      </div>
    );
  }

  return (
    <div role="status" className={`${variante === 'pantalla' ? 'cargando-pantalla' : 'cargando-seccion'} ${className}`.trim()}>
      <Indicador />
      <span>{leyenda}</span>
    </div>
  );
}
