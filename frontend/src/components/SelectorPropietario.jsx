import Form from 'react-bootstrap/Form';
import { PARAMETROS } from '../config/parametros.js';
import { t } from '../i18n/index.js';
import CampoFormulario from './CampoFormulario.jsx';
import CampoSelect from './CampoSelect.jsx';

/**
 * Elección del propietario de un complejo nuevo: se busca entre las cuentas activas con rol de dueño por parte del
 * nombre o del correo y se elige de los resultados. `duenos` es `{ items, cargando, error, minimo }` (ver `useContratos`).
 */
export default function SelectorPropietario({ busqueda, onBuscar, duenos, valor, onElegir, error }) {
  const escribio = busqueda.trim().length >= duenos.minimo;

  return (
    <div>
      <CampoFormulario
        id="propietario-busqueda"
        etiqueta={t('contratos.buscarPropietario')}
        type="search"
        maxLength={PARAMETROS.limitesCampos.busqueda}
        valor={busqueda}
        onCambiar={onBuscar}
        ayuda={t('contratos.ayudaPropietario', { minimo: duenos.minimo })}
        className="mb-2"
      />
      <CampoSelect
        id="propietario-elegido"
        etiqueta={t('contratos.propietario')}
        valor={valor}
        onCambiar={onElegir}
        placeholder={duenos.cargando ? t('comun.cargando') : t('contratos.elegirPropietario')}
        opciones={duenos.items.map((dueno) => ({ valor: String(dueno.id), etiqueta: `${dueno.nombre_completo} (${dueno.email})` }))}
        error={error}
        className="mb-0"
        disabled={!escribio}
      />
      {escribio && !duenos.cargando && !duenos.error && duenos.items.length === 0 && (
        <Form.Text className="d-block mt-1" muted>{t('contratos.sinDuenos')}</Form.Text>
      )}
      {duenos.error && <Form.Text className="d-block mt-1 text-danger">{duenos.error.mensaje}</Form.Text>}
    </div>
  );
}
