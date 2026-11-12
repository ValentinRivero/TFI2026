import { PARAMETROS } from '../config/parametros.js';
import { t, tLista } from '../i18n/index.js';
import { formatearFechaLarga } from '../utils/formatos.js';

const { contacto, version, vigenteDesde, retencionIpMeses, retencionContactoDias } = PARAMETROS.politica;

function Seccion({ titulo, children }) {
  return (
    <section className="mb-4">
      <h2 className="h4">{titulo}</h2>
      {children}
    </section>
  );
}

function Lista({ clave, params }) {
  const cantidad = tLista(clave).length;
  return (
    <ul>
      {Array.from({ length: cantidad }, (_, indice) => (
        <li key={indice}>{t(`${clave}.${indice}`, params)}</li>
      ))}
    </ul>
  );
}

/** Política de privacidad pública, con el contenido que exige la Ley 25.326. La versión sale de `parametros.js`. */
export default function Privacidad() {
  const parametros = { contacto, meses: retencionIpMeses, dias: retencionContactoDias };

  return (
    <article className="mx-auto" style={{ maxWidth: '52rem' }}>
      <h1 className="h2">{t('privacidad.titulo')}</h1>
      <p className="text-secondary">
        {t('privacidad.version', { version, fecha: formatearFechaLarga(vigenteDesde) })}
      </p>
      <p>{t('privacidad.introduccion')}</p>

      <Seccion titulo={t('privacidad.responsable.titulo')}>
        <p>
          {t('privacidad.responsable.texto', { contacto })}
          {' '}
          <a href={`mailto:${contacto}`}>{contacto}</a>
        </p>
      </Seccion>

      <Seccion titulo={t('privacidad.datos.titulo')}>
        <p>{t('privacidad.datos.introduccion')}</p>
        <div className="table-responsive superficie">
          <table className="table mb-0 align-top">
            <thead>
              <tr>
                {tLista('privacidad.datos.columnas').map((columna) => <th key={columna}>{columna}</th>)}
              </tr>
            </thead>
            <tbody>
              {tLista('privacidad.datos.filas').map((fila) => (
                <tr key={fila[0]}>
                  {fila.map((celda) => <td key={celda}>{celda}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Seccion>

      <Seccion titulo={t('privacidad.destinatarios.titulo')}>
        <p>{t('privacidad.destinatarios.texto')}</p>
      </Seccion>

      <Seccion titulo={t('privacidad.proveedores.titulo')}>
        <p>{t('privacidad.proveedores.texto')}</p>
        <Lista clave="privacidad.proveedores.items" />
      </Seccion>

      <Seccion titulo={t('privacidad.plazos.titulo')}>
        <Lista clave="privacidad.plazos.items" params={parametros} />
      </Seccion>

      <Seccion titulo={t('privacidad.derechos.titulo')}>
        <p>{t('privacidad.derechos.texto', parametros)}</p>
        <Lista clave="privacidad.derechos.items" />
      </Seccion>

      <Seccion titulo={t('privacidad.cookies.titulo')}>
        <p>{t('privacidad.cookies.texto')}</p>
      </Seccion>

      <Seccion titulo={t('privacidad.aaip.titulo')}>
        <p>{t('privacidad.aaip.texto')}</p>
      </Seccion>
    </article>
  );
}
