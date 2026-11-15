import { t } from '../i18n/index.js';
import BotonVolver from './BotonVolver.jsx';
import Icono from './Icono.jsx';

/** Cabecera del detalle: botón para volver, nombre y dirección del complejo. */
export default function EncabezadoComplejo({ complejo }) {
  return (
    <>
      <div className="mb-3"><BotonVolver destino="/">{t('complejo.volver')}</BotonVolver></div>
      <header className="mb-4">
        <h1 className="display-6 mb-1">{complejo.nombre}</h1>
        <p className="text-secondary mb-0 d-flex align-items-start gap-1">
          <Icono nombre="ubicacion" tamano={18} className="flex-shrink-0 mt-1" />
          <span>{complejo.direccion}</span>
        </p>
      </header>
    </>
  );
}
