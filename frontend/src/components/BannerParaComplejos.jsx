import { Link } from 'react-router-dom';
import { PARAMETROS } from '../config/parametros.js';
import { t } from '../i18n/index.js';
import Icono from './Icono.jsx';

const { politica } = PARAMETROS;

const BENEFICIOS = Object.freeze([
  Object.freeze({ icono: 'calendario', clave: 'agenda' }),
  Object.freeze({ icono: 'repetir', clave: 'turnosFijos' }),
  Object.freeze({ icono: 'candado', clave: 'excepciones' }),
  Object.freeze({ icono: 'grafico', clave: 'reportes' }),
]);

/**
 * Desplegable para propietarios y administradores de complejos, al final del catálogo: cerrado muestra solo su
 * título y una flecha; al tocarlo se abre el detalle. Es un `<details>` nativo, así que el teclado y los lectores de
 * pantalla lo resuelven sin estado propio. Con una cuenta administrativa (`tienePanel`) lleva al panel de gestión;
 * sin ella, al correo de contacto oficial.
 */
export default function BannerParaComplejos({ tienePanel = false }) {
  const asunto = encodeURIComponent(t('portada.complejos.asunto'));

  return (
    <details className="superficie banner-complejos mt-5">
      <summary className="banner-complejos-resumen">
        <h2 className="banner-complejos-etiqueta">{t('portada.complejos.etiqueta')}</h2>
        <Icono nombre="abajo" tamano={22} className="banner-complejos-flecha" />
      </summary>
      <div className="banner-complejos-cuerpo">
        <div className="d-flex flex-column flex-lg-row gap-4 align-items-lg-center justify-content-between">
          <div>
            <h3 className="h4">{t('portada.complejos.titulo')}</h3>
            <p className="text-secondary">{t('portada.complejos.descripcion')}</p>
            <ul className="banner-complejos-lista list-unstyled mb-0" aria-label={t('portada.complejos.beneficios')}>
              {BENEFICIOS.map(({ icono, clave }) => (
                <li key={clave}>
                  <Icono nombre={icono} tamano={18} className="flex-shrink-0 text-primary" />
                  {t(`portada.complejos.${clave}`)}
                </li>
              ))}
            </ul>
          </div>
          <div className="flex-shrink-0">
            {tienePanel ? (
              <Link to="/panel" className="btn btn-primary">
                <Icono nombre="inicio" tamano={18} />
                {t('portada.complejos.irAlPanel')}
              </Link>
            ) : (
              <a href={`mailto:${politica.contacto}?subject=${asunto}`} className="btn btn-primary">
                <Icono nombre="correo" tamano={18} />
                {t('portada.complejos.contactar')}
              </a>
            )}
          </div>
        </div>
      </div>
    </details>
  );
}
