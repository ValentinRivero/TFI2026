import useTema from '../hooks/useTema.js';
import { t } from '../i18n/index.js';
import Icono from './Icono.jsx';

/**
 * Botón de la barra superior que alterna entre modo claro y oscuro. Muestra el ícono del modo al que se pasa y lo
 * anuncia en su etiqueta. `className` permite mostrarlo solo en escritorio o solo en móvil.
 */
export default function BotonTema({ className = '' }) {
  const { esOscuro, alternar } = useTema();
  const etiqueta = t(esOscuro ? 'tema.cambiarAClaro' : 'tema.cambiarAOscuro');

  return (
    <button
      type="button"
      className={`boton-tema ${className}`.trim()}
      aria-label={etiqueta}
      title={etiqueta}
      onClick={alternar}
    >
      <Icono nombre={esOscuro ? 'sol' : 'luna'} tamano={20} />
    </button>
  );
}
