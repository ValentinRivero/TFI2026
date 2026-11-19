import Button from 'react-bootstrap/Button';
import { PARAMETROS } from '../config/parametros.js';
import { t } from '../i18n/index.js';
import { pronosticoDeFecha } from '../utils/clima.js';
import { formatearDiaCorto, formatearFechaLarga, formatearTemperatura } from '../utils/formatos.js';
import Cargando from './Cargando.jsx';
import Icono from './Icono.jsx';

const { nombre, url, licencia } = PARAMETROS.atribuciones.clima;

// La licencia de los datos exige mostrar la fuente junto a ellos, en todas las variantes.
function Atribucion({ className = '' }) {
  return (
    <p className={`small text-secondary mb-0 ${className}`.trim()}>
      {t('clima.fuente')}{' '}
      <a href={url} target="_blank" rel="noopener noreferrer" title={t('clima.licenciaTitulo', { licencia })}>{nombre}</a>
    </p>
  );
}

const lluvia = (dia) => (
  dia.probabilidad_lluvia === null || dia.probabilidad_lluvia === undefined
    ? ''
    : t('clima.lluvia', { valor: Math.round(dia.probabilidad_lluvia) })
);

function ActualDelClima({ actual }) {
  return (
    <div className="d-flex align-items-baseline gap-3 flex-wrap">
      <span className="num display-6 mb-0">{formatearTemperatura(actual.temperatura)}</span>
      <div>
        <div className="fw-semibold">{actual.descripcion}</div>
        <div className="small text-secondary">{t('clima.viento', { valor: Math.round(actual.viento_kmh) })}</div>
      </div>
    </div>
  );
}

function DiaCompacto({ dia }) {
  return (
    <li className="clima-dia-compacto">
      <span className="small text-secondary">{formatearDiaCorto(dia.fecha)}</span>
      <span className="num">
        {formatearTemperatura(dia.temperatura_max)}
        <span className="text-secondary"> / {formatearTemperatura(dia.temperatura_min)}</span>
      </span>
      <span className="small">{dia.descripcion}</span>
    </li>
  );
}

function Compacto({ datos }) {
  return (
    <section className="superficie p-3" aria-labelledby="clima-titulo">
      <div className="d-flex flex-column flex-lg-row gap-3 gap-lg-4 align-items-lg-center">
        <div>
          <h2 id="clima-titulo" className="h6 text-secondary mb-1">{t('clima.tituloGoya')}</h2>
          <ActualDelClima actual={datos.actual} />
        </div>
        <ul className="list-unstyled d-flex flex-wrap gap-2 mb-0 flex-grow-1 justify-content-lg-end">
          {datos.pronostico.map((dia) => <DiaCompacto key={dia.fecha} dia={dia} />)}
        </ul>
      </div>
      <Atribucion className="mt-2" />
    </section>
  );
}

function Detalle({ datos }) {
  return (
    <section className="superficie p-3 h-100" aria-labelledby="clima-titulo">
      <h2 id="clima-titulo" className="h5">{t('clima.titulo')}</h2>
      <div className="mb-3"><ActualDelClima actual={datos.actual} /></div>
      {datos.pronostico.length > 0 && (
        <>
          <h3 className="h6 text-secondary">{t('clima.pronostico')}</h3>
          <ul className="list-unstyled mb-3">
            {datos.pronostico.map((dia) => (
              <li key={dia.fecha} className="d-flex flex-wrap justify-content-between gap-2 py-1 border-top">
                <span>
                  <span>{formatearFechaLarga(dia.fecha)}</span>
                  <span className="text-secondary"> · {dia.descripcion}</span>
                </span>
                <span className="num">
                  {t('clima.maxMin', {
                    max: formatearTemperatura(dia.temperatura_max),
                    min: formatearTemperatura(dia.temperatura_min),
                  })}
                  {lluvia(dia) && <span className="text-secondary"> · {lluvia(dia)}</span>}
                </span>
              </li>
            ))}
          </ul>
        </>
      )}
      <Atribucion />
    </section>
  );
}

function DelDia({ datos, fecha }) {
  const dia = pronosticoDeFecha(datos, fecha);
  if (!dia) {
    return <p className="small text-secondary mb-0">{t('clima.sinPronosticoFecha')}</p>;
  }
  return (
    <div className="clima-dia">
      <Icono nombre="informacion" tamano={18} className="flex-shrink-0 text-secondary" />
      <span className="num">{t('clima.maxMin', {
        max: formatearTemperatura(dia.temperatura_max),
        min: formatearTemperatura(dia.temperatura_min),
      })}</span>
      <span>{dia.descripcion}</span>
      {lluvia(dia) && <span className="text-secondary">{lluvia(dia)}</span>}
      <Atribucion className="w-100" />
    </div>
  );
}

const VARIANTES = { compacto: Compacto, detalle: Detalle, dia: DelDia };

/**
 * Pronóstico del clima, siempre visible: mientras carga muestra el indicador y, si Node o el proveedor no
 * responden, un aviso discreto con "Reintentar" en el mismo lugar. Variantes:
 * - `compacto`: temperatura actual y los próximos días en una franja (portada del catálogo).
 * - `detalle`: actual y desglose por día, con probabilidad de lluvia (ficha del complejo).
 * - `dia`: el pronóstico de `fecha` (`AAAA-MM-DD`) junto al selector de fecha y en el resumen del turno.
 * Recibe el estado de `useClima` (`datos`, `error`, `cargando`, `recargar`).
 */
export default function ClimaCard({ datos, error, cargando, recargar, variante = 'detalle', fecha }) {
  const Variante = VARIANTES[variante] ?? Detalle;
  const envoltorio = variante === 'dia' ? 'clima-estado clima-estado-chico' : 'superficie p-3 clima-estado';

  if (cargando && !datos) {
    return (
      <div className={envoltorio} aria-busy="true">
        <Cargando variante="inline" texto={t('clima.cargando')} />
      </div>
    );
  }

  if (error || !datos) {
    return (
      <div className={envoltorio} role="status">
        <span className="d-inline-flex align-items-center gap-2 text-secondary">
          <Icono nombre="alerta" tamano={18} className="flex-shrink-0" />
          {t('clima.noDisponible')}
        </span>
        <Button variant="outline-secondary" size="sm" onClick={recargar}>{t('comun.reintentar')}</Button>
      </div>
    );
  }

  return <Variante datos={datos} fecha={fecha} />;
}
