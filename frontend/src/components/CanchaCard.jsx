import { COBERTURA, DURACION_TURNO, ILUMINACION, TIPO_SUPERFICIE } from '../config/catalogos.js';
import { t } from '../i18n/index.js';
import { formatearPrecio } from '../utils/formatos.js';

// El catálogo de códigos manda; si el backend suma un valor que el cliente todavía no conoce, se usa su nombre.
const etiquetaDe = (catalogo, codigo, nombreApi) => catalogo[codigo]?.etiqueta ?? nombreApi ?? '';

function Dato({ titulo, children }) {
  return (
    <div className="col-6">
      <dt className="small text-secondary fw-normal">{titulo}</dt>
      <dd className="mb-0">{children}</dd>
    </div>
  );
}

/** Ficha pública de una cancha activa: deporte, superficie, cobertura, iluminación, duración del turno y precio base. */
export default function CanchaCard({ cancha }) {
  const duracion = DURACION_TURNO[cancha.duracion_turno_min]?.etiqueta
    ?? t('cancha.minutos', { minutos: cancha.duracion_turno_min });

  return (
    <article className="card h-100">
      <div className="card-body">
        <div className="d-flex flex-wrap justify-content-between align-items-start gap-2 mb-3">
          <h3 className="h5 mb-0">{cancha.nombre}</h3>
          {cancha.deporte && <span className="badge badge-info">{cancha.deporte.nombre}</span>}
        </div>
        <dl className="row g-3 mb-0">
          <Dato titulo={t('cancha.superficie')}>
            {etiquetaDe(TIPO_SUPERFICIE, cancha.tipo_superficie, cancha.tipo_superficie_nombre)}
          </Dato>
          <Dato titulo={t('cancha.cobertura')}>
            {etiquetaDe(COBERTURA, cancha.cobertura, cancha.cobertura_nombre)}
          </Dato>
          <Dato titulo={t('cancha.iluminacion')}>
            {etiquetaDe(ILUMINACION, cancha.iluminacion, cancha.iluminacion_nombre)}
          </Dato>
          <Dato titulo={t('cancha.turno')}><span className="num">{duracion}</span></Dato>
          <Dato titulo={t('cancha.precio')}>
            <span className="num fs-5">{formatearPrecio(cancha.precio_base)}</span> {t('cancha.porTurno')}
          </Dato>
        </dl>
      </div>
    </article>
  );
}
