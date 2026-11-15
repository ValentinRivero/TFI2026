import { t } from '../i18n/index.js';
import BotonVolver from './BotonVolver.jsx';
import EstadoVacio from './EstadoVacio.jsx';

/** Estado de una ficha de complejo inexistente o con un identificador inválido, con el regreso al catálogo. */
export default function ComplejoNoEncontrado() {
  return (
    <EstadoVacio titulo={t('complejo.noEncontradoTitulo')} descripcion={t('complejo.noEncontradoDescripcion')}>
      <BotonVolver destino="/">{t('complejo.volver')}</BotonVolver>
    </EstadoVacio>
  );
}
