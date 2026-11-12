import { t } from '../i18n/index.js';

/** Datos comerciales del complejo: condiciones de seña, margen de cancelación, servicios y teléfono de contacto. */
export default function FichaComplejo({ complejo }) {
  const { telefono_contacto: telefono, info_sena: sena, horas_limite_cancelacion: horas, servicios } = complejo;

  return (
    <section className="superficie p-3 h-100" aria-label={t('complejo.datos')}>
      <dl className="mb-0">
        <dt className="h6">{t('complejo.sena')}</dt>
        <dd className="texto-multilinea">{sena || <span className="text-secondary">{t('complejo.senaVacia')}</span>}</dd>

        <dt className="h6">{t('complejo.cancelacion')}</dt>
        <dd>{horas > 0 ? t('complejo.cancelacionHoras', { horas }) : t('complejo.cancelacionHasta')}</dd>

        <dt className="h6">{t('complejo.servicios')}</dt>
        <dd>
          {servicios.length > 0 ? (
            <span className="d-flex flex-wrap gap-2">
              {servicios.map((servicio) => <span key={servicio.id} className="badge badge-neutro">{servicio.nombre}</span>)}
            </span>
          ) : <span className="text-secondary">{t('complejo.sinServicios')}</span>}
        </dd>

        {telefono && (
          <>
            <dt className="h6">{t('complejo.telefono')}</dt>
            <dd className="mb-0 num">
              <a href={`tel:${telefono.replace(/[^\d+]/g, '')}`}>{telefono}</a>
            </dd>
          </>
        )}
      </dl>
    </section>
  );
}
