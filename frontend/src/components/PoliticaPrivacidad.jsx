import { PARAMETROS } from '../config/parametros.js';
import { t } from '../i18n/index.js';
import { formatearFechaLarga } from '../utils/formatos.js';
import ListaTextos from './ListaTextos.jsx';
import SeccionPolitica from './SeccionPolitica.jsx';
import TablaDatosPersonales from './TablaDatosPersonales.jsx';

const { contacto, version, vigenteDesde, retencionIpMeses, retencionContactoDias } = PARAMETROS.politica;

/** Política de privacidad pública, con el contenido que exige la Ley 25.326. La versión sale de `parametros.js`. */
export default function PoliticaPrivacidad() {
  const parametros = { contacto, meses: retencionIpMeses, dias: retencionContactoDias };

  return (
    <article className="mx-auto" style={{ maxWidth: '52rem' }}>
      <h1 className="h2">{t('privacidad.titulo')}</h1>
      <p className="text-secondary">
        {t('privacidad.version', { version, fecha: formatearFechaLarga(vigenteDesde) })}
      </p>
      <p>{t('privacidad.introduccion')}</p>

      <SeccionPolitica titulo={t('privacidad.responsable.titulo')}>
        <p>
          {t('privacidad.responsable.texto', { contacto })}
          {' '}
          <a href={`mailto:${contacto}`}>{contacto}</a>
        </p>
      </SeccionPolitica>

      <SeccionPolitica titulo={t('privacidad.datos.titulo')}>
        <p>{t('privacidad.datos.introduccion')}</p>
        <TablaDatosPersonales />
      </SeccionPolitica>

      <SeccionPolitica titulo={t('privacidad.destinatarios.titulo')}>
        <p>{t('privacidad.destinatarios.texto')}</p>
      </SeccionPolitica>

      <SeccionPolitica titulo={t('privacidad.proveedores.titulo')}>
        <p>{t('privacidad.proveedores.texto')}</p>
        <ListaTextos clave="privacidad.proveedores.items" />
      </SeccionPolitica>

      <SeccionPolitica titulo={t('privacidad.plazos.titulo')}>
        <ListaTextos clave="privacidad.plazos.items" params={parametros} />
      </SeccionPolitica>

      <SeccionPolitica titulo={t('privacidad.derechos.titulo')}>
        <p>{t('privacidad.derechos.texto', parametros)}</p>
        <ListaTextos clave="privacidad.derechos.items" />
      </SeccionPolitica>

      <SeccionPolitica titulo={t('privacidad.cookies.titulo')}>
        <p>{t('privacidad.cookies.texto')}</p>
      </SeccionPolitica>

      <SeccionPolitica titulo={t('privacidad.aaip.titulo')}>
        <p>{t('privacidad.aaip.texto')}</p>
      </SeccionPolitica>
    </article>
  );
}
