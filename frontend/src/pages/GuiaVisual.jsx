import { useState } from 'react';
import Button from 'react-bootstrap/Button';
import Form from 'react-bootstrap/Form';
import Alerta from '../components/Alerta.jsx';
import BotonAccion from '../components/BotonAccion.jsx';
import Cargando from '../components/Cargando.jsx';
import Icono from '../components/Icono.jsx';
import ModalConfirmar from '../components/ModalConfirmar.jsx';
import Paginador from '../components/Paginador.jsx';
import {
  COBERTURA,
  ESTADO_BLOQUE,
  ESTADO_CONTRATO,
  ESTADO_RESERVA,
  PRIORIDAD_NOTIFICACION,
  describir,
} from '../config/catalogos.js';
import { t } from '../i18n/index.js';
import { formatearHora, formatearPrecio } from '../utils/formatos.js';

const COLORES = [
  ['--tema-primario', 'Primario'],
  ['--tema-primario-hover', 'Primario hover'],
  ['--tema-pizarra', 'Pizarra'],
  ['--tema-fondo', 'Fondo'],
  ['--tema-superficie', 'Superficie'],
  ['--tema-borde', 'Borde'],
];

const BLOQUES = [
  { estado: 'LIBRE', hora: '14:00:00', detalle: 38000 },
  { estado: 'OCUPADO', hora: '15:00:00', detalle: 'Ocupado' },
  { estado: 'CERRADO_EXCEPCION', hora: '16:00:00', detalle: 'Mantenimiento' },
  { estado: 'NO_DISPONIBLE', hora: '17:00:00', detalle: 'No disponible' },
];

const FILAS = [
  { id: 1, cancha: 'Cancha 1', horario: '20:00:00', precio: '38000.00', estado: 3 },
  { id: 2, cancha: 'Cancha 2', horario: '21:00:00', precio: '42000.00', estado: 1 },
  { id: 3, cancha: 'Cancha 1', horario: '22:00:00', precio: '38000.00', estado: 5 },
  { id: 4, cancha: 'Pádel 1', horario: '19:30:00', precio: '30000.00', estado: 7 },
];

const esperar = (ms) => new Promise((resolver) => {
  setTimeout(resolver, ms);
});

function Seccion({ titulo, children }) {
  return (
    <section className="mb-5">
      <h2 className="h3 border-bottom pb-2 mb-3">{titulo}</h2>
      {children}
    </section>
  );
}

function Casillero({ bloque, seleccionado, onElegir }) {
  const { casillero } = ESTADO_BLOQUE[bloque.estado];
  const clase = seleccionado ? 'seleccionado' : casillero;
  const libre = bloque.estado === 'LIBRE';
  return (
    <button
      type="button"
      className={`casillero casillero-${clase}`}
      disabled={!libre}
      aria-pressed={libre ? seleccionado : undefined}
      onClick={() => onElegir(bloque.hora)}
    >
      <span className="casillero__hora num">
        <span className="casillero__marca me-1"><Icono nombre="check" tamano={14} /></span>
        {formatearHora(bloque.hora)}
      </span>
      <span className="casillero__detalle">
        {typeof bloque.detalle === 'number' ? formatearPrecio(bloque.detalle) : bloque.detalle}
      </span>
    </button>
  );
}

export default function GuiaVisual() {
  const [elegido, setElegido] = useState(null);
  const [pagina, setPagina] = useState(1);
  const [mostrarModal, setMostrarModal] = useState(false);

  return (
    <div>
      <h1 className="display-6">{t('guia.titulo')}</h1>
      <p className="text-secondary mb-5">{t('guia.descripcion')}</p>

      <Seccion titulo={t('guia.paleta')}>
        <div className="d-flex flex-wrap gap-3">
          {COLORES.map(([variable, nombre]) => (
            <div key={variable} style={{ width: '9rem' }}>
              <div
                style={{ background: `var(${variable})`, height: '4rem', border: '1px solid var(--tema-borde)' }}
                className="rounded"
              />
              <div className="small fw-semibold mt-1">{nombre}</div>
              <code className="small">{variable}</code>
            </div>
          ))}
        </div>
      </Seccion>

      <Seccion titulo={t('guia.tipografia')}>
        <p className="display-4 mb-0">Barlow Semi Condensed</p>
        <h2 className="h1">Títulos y encabezados 600</h2>
        <p className="mb-1">{t('guia.muestraTexto')}</p>
        <p className="num fs-3 mb-0">{formatearPrecio('38000.00')} &nbsp; 14:00 &nbsp; 1.234.567</p>
      </Seccion>

      <Seccion titulo={t('guia.botones')}>
        <div className="d-flex flex-wrap gap-2 mb-3">
          <Button variant="primary">Primario</Button>
          <Button variant="outline-primary">Contorno</Button>
          <Button variant="outline-secondary">Secundario</Button>
          <Button variant="link">Enlace</Button>
          <Button variant="primary" disabled>Deshabilitado</Button>
        </div>
        <Form className="row g-3" onSubmit={(evento) => evento.preventDefault()}>
          <Form.Group className="col-md-4" controlId="guia-texto">
            <Form.Label>Nombre</Form.Label>
            <Form.Control placeholder="Complejo El Yacaré" />
          </Form.Group>
          <Form.Group className="col-md-4" controlId="guia-select">
            <Form.Label>Cobertura</Form.Label>
            <Form.Select defaultValue="2">
              {Object.entries(COBERTURA).map(([codigo, { etiqueta }]) => (
                <option key={codigo} value={codigo}>{etiqueta}</option>
              ))}
            </Form.Select>
          </Form.Group>
          <div className="col-md-4 d-flex flex-column justify-content-end gap-2">
            <Form.Check type="checkbox" id="guia-check" label="Acepto la política de privacidad" defaultChecked />
            <Form.Check type="switch" id="guia-switch" label="Notificaciones urgentes" defaultChecked />
          </div>
        </Form>
        <ul className="nav nav-tabs mt-4">
          <li className="nav-item"><button type="button" className="nav-link active">Reservas</button></li>
          <li className="nav-item"><button type="button" className="nav-link">Operatoria</button></li>
          <li className="nav-item"><button type="button" className="nav-link">Sistema</button></li>
        </ul>
        <ul className="nav nav-pills mt-3">
          <li className="nav-item"><button type="button" className="nav-link active">Próximas</button></li>
          <li className="nav-item"><button type="button" className="nav-link">Pasadas</button></li>
        </ul>
      </Seccion>

      <Seccion titulo={t('guia.badges')}>
        <div className="d-flex flex-wrap gap-2">
          {['badge-ok', 'badge-aviso', 'badge-peligro', 'badge-neutro', 'badge-info'].map((clase) => (
            <span key={clase} className={`badge ${clase}`}>{clase}</span>
          ))}
        </div>
        <div className="d-flex flex-wrap gap-2 mt-3">
          {Object.keys(ESTADO_RESERVA).map((codigo) => {
            const { etiqueta, badge } = describir(ESTADO_RESERVA, codigo);
            return <span key={codigo} className={`badge ${badge}`}>{etiqueta}</span>;
          })}
          {[2, 3].map((codigo) => {
            const { etiqueta, badge } = describir(ESTADO_CONTRATO, codigo);
            return <span key={`c${codigo}`} className={`badge ${badge}`}>Contrato {etiqueta.toLowerCase()}</span>;
          })}
          <span className={`badge ${describir(PRIORIDAD_NOTIFICACION, 2).badge}`}>Urgente</span>
        </div>
      </Seccion>

      <Seccion titulo={t('guia.grilla')}>
        <div className="d-flex flex-wrap gap-2">
          {BLOQUES.map((bloque) => (
            <Casillero
              key={bloque.hora}
              bloque={bloque}
              seleccionado={elegido === bloque.hora}
              onElegir={(hora) => setElegido(elegido === hora ? null : hora)}
            />
          ))}
          <Casillero bloque={{ estado: 'LIBRE', hora: '18:00:00', detalle: 38000 }} seleccionado onElegir={() => {}} />
        </div>
        <p className="small text-secondary mt-2 mb-0">
          Libre, ocupado, excepción, no disponible y seleccionado. El primero es interactivo: pulsalo para seleccionarlo.
        </p>
      </Seccion>

      <Seccion titulo={t('guia.cargando')}>
        <div className="d-flex flex-wrap gap-4 align-items-center">
          <div className="superficie p-2"><Cargando variante="seccion" /></div>
          <div className="superficie p-3"><Cargando variante="inline" texto="Buscando turnos" /></div>
          <BotonAccion onClick={() => esperar(2000)}>{t('guia.probarAccion')}</BotonAccion>
          <BotonAccion variant="outline-primary" cargando textoCargando="Guardando">Guardar</BotonAccion>
        </div>
        <div className="superficie mt-3" style={{ height: '10rem', overflow: 'hidden' }}>
          <Cargando variante="pantalla" texto="Cargando la aplicación" className="cargando-contenido" />
        </div>
      </Seccion>

      <Seccion titulo={t('guia.paginador')}>
        <div className="d-grid gap-3">
          <Paginador pagina={pagina} total={12} onCambiar={setPagina} />
          <Paginador pagina={1} total={3} onCambiar={() => {}} alineacion="izquierda" />
          <Paginador pagina={4} total={4} onCambiar={() => {}} />
          <Paginador pagina={2} total={2} onCambiar={() => {}} />
        </div>
      </Seccion>

      <Seccion titulo={t('guia.tabla')}>
        <div className="panel-admin superficie p-2">
          <div className="table-responsive">
            <table className="table table-hover align-middle mb-0">
              <thead>
                <tr><th>Cancha</th><th>Horario</th><th className="text-end">Precio</th><th>Estado</th><th /></tr>
              </thead>
              <tbody>
                {FILAS.map((fila) => {
                  const { etiqueta, badge } = describir(ESTADO_RESERVA, fila.estado);
                  return (
                    <tr key={fila.id}>
                      <td>{fila.cancha}</td>
                      <td className="num">{formatearHora(fila.horario)}</td>
                      <td className="num text-end">{formatearPrecio(fila.precio)}</td>
                      <td><span className={`badge ${badge}`}>{etiqueta}</span></td>
                      <td className="text-end"><Button size="sm" variant="outline-primary">Ver</Button></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
        <p className="small text-secondary mt-2 mb-0">
          Densidad de escritorio: se compacta a partir de 992 px de ancho. En móvil los controles mantienen 44 px.
        </p>
      </Seccion>

      <Seccion titulo={t('guia.tarjeta')}>
        <article className="card" style={{ maxWidth: '24rem' }}>
          <div className="card-body">
            <h3 className="h4 card-title mb-1">Complejo El Yacaré</h3>
            <p className="text-secondary mb-2 d-flex align-items-center gap-1">
              <Icono nombre="ubicacion" tamano={16} /> Av. del Ombú 1250, Goya
            </p>
            <div className="d-flex flex-wrap gap-2 mb-3">
              <span className="badge badge-neutro">{describir(COBERTURA, 2).etiqueta}</span>
              <span className="badge badge-neutro">Fútbol 5</span>
              <span className="badge badge-neutro">Estacionamiento</span>
            </div>
            <p className="mb-3">{t('guia.desde', { precio: formatearPrecio('38000.00') })}</p>
            <Button variant="primary" className="w-100">Ver turnos</Button>
          </div>
        </article>
      </Seccion>

      <Seccion titulo={t('guia.alertas')}>
        <div className="d-grid gap-2 mb-3">
          <Alerta variante="success">Reserva confirmada.</Alerta>
          <Alerta variante="warning">El turno ya empezó.</Alerta>
          <Alerta variante="danger" titulo="No se pudo reservar">El turno ya está ocupado.</Alerta>
          <Alerta variante="info">Pronóstico de Open-Meteo.com.</Alerta>
        </div>
        <Button variant="outline-primary" onClick={() => setMostrarModal(true)}>{t('guia.abrirConfirmacion')}</Button>
        <ModalConfirmar
          mostrar={mostrarModal}
          titulo={t('guia.confirmacionTitulo')}
          onCancelar={() => setMostrarModal(false)}
          onConfirmar={async () => {
            await esperar(1200);
            setMostrarModal(false);
          }}
        >
          {t('guia.confirmacionCuerpo', { cantidad: 3 })}
        </ModalConfirmar>
      </Seccion>
    </div>
  );
}
