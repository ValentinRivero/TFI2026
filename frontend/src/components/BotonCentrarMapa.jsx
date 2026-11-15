import { t } from '../i18n/index.js';
import Icono from './Icono.jsx';

/** Botón flotante que devuelve el mapa a la vista inicial de la ciudad. */
export default function BotonCentrarMapa({ onClick }) {
  return (
    <button type="button" className="mapa-control mapa-control-centrar" onClick={onClick}>
      <Icono nombre="ubicacion" tamano={18} />
      {t('mapa.centrar')}
    </button>
  );
}
