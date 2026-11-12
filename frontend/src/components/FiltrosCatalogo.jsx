import { useEffect, useId, useState } from 'react';
import Button from 'react-bootstrap/Button';
import Form from 'react-bootstrap/Form';
import { COBERTURA, ORDENES_CATALOGO } from '../config/catalogos.js';
import { PARAMETROS } from '../config/parametros.js';
import { t } from '../i18n/index.js';
import { contarFiltros, hayFiltros } from '../utils/filtrosCatalogo.js';
import Icono from './Icono.jsx';

const ORDEN_PREDETERMINADO = ORDENES_CATALOGO[0].valor;

/**
 * Filtros del catálogo. El estado vive en la URL (lo administra `Catalogo`): este componente muestra los filtros
 * activos y avisa los cambios con `onCambiar(cambios)`. La búsqueda por texto espera una pausa al
 * escribir para no consultar en cada tecla. En pantallas chicas todo menos la búsqueda se pliega en un panel.
 */
export default function FiltrosCatalogo({ filtros, deportes, servicios, onCambiar, onLimpiar }) {
  const idPanel = useId();
  const [abierto, setAbierto] = useState(false);
  const [texto, setTexto] = useState(filtros.search);
  const [busquedaUrl, setBusquedaUrl] = useState(filtros.search);

  // Un cambio de la URL que no vino de este campo (limpiar, botón atrás) reemplaza el texto escrito.
  if (busquedaUrl !== filtros.search) {
    setBusquedaUrl(filtros.search);
    if (texto.trim() !== filtros.search) setTexto(filtros.search);
  }

  useEffect(() => {
    if (texto.trim() === filtros.search) return undefined;
    const espera = setTimeout(() => onCambiar({ search: texto.trim() }), PARAMETROS.catalogo.busquedaDemoraMs);
    return () => clearTimeout(espera);
  }, [texto, filtros.search, onCambiar]);

  const alternarServicio = (id) => {
    const clave = String(id);
    const elegidos = filtros.servicios.includes(clave)
      ? filtros.servicios.filter((elegido) => elegido !== clave)
      : [...filtros.servicios, clave];
    onCambiar({ servicios: elegidos });
  };

  const activos = contarFiltros(filtros);

  return (
    <form className="superficie p-3 mb-4" role="search" aria-label={t('filtros.panel')} onSubmit={(evento) => evento.preventDefault()}>
      <div className="d-flex flex-column flex-md-row gap-2">
        <Form.Group controlId={`${idPanel}-buscar`} className="flex-grow-1">
          <Form.Label className="visually-hidden">{t('filtros.buscar')}</Form.Label>
          <Form.Control
            type="search"
            enterKeyHint="search"
            autoComplete="off"
            maxLength={PARAMETROS.limitesCampos.busqueda}
            placeholder={t('filtros.buscarPlaceholder')}
            value={texto}
            onChange={(evento) => setTexto(evento.target.value)}
          />
        </Form.Group>
        <Button
          variant="outline-secondary"
          className="d-md-none"
          aria-expanded={abierto}
          aria-controls={`${idPanel}-panel`}
          onClick={() => setAbierto((actual) => !actual)}
        >
          <Icono nombre="menu" tamano={18} />
          {activos > 0 ? t('filtros.conCantidad', { cantidad: activos }) : t('filtros.titulo')}
        </Button>
      </div>

      <div id={`${idPanel}-panel`} className={`${abierto ? '' : 'd-none'} d-md-block mt-3`}>
        <div className="row g-3">
          <Form.Group className="col-md-4" controlId={`${idPanel}-deporte`}>
            <Form.Label>{t('filtros.deporte')}</Form.Label>
            <Form.Select value={filtros.deporte} onChange={(evento) => onCambiar({ deporte: evento.target.value })}>
              <option value="">{t('filtros.todosDeportes')}</option>
              {deportes.map(({ id, nombre }) => <option key={id} value={String(id)}>{nombre}</option>)}
            </Form.Select>
          </Form.Group>
          <Form.Group className="col-md-4" controlId={`${idPanel}-cobertura`}>
            <Form.Label>{t('filtros.cobertura')}</Form.Label>
            <Form.Select value={filtros.cobertura} onChange={(evento) => onCambiar({ cobertura: evento.target.value })}>
              <option value="">{t('filtros.todasCoberturas')}</option>
              {Object.entries(COBERTURA).map(([codigo, { etiqueta }]) => <option key={codigo} value={codigo}>{etiqueta}</option>)}
            </Form.Select>
          </Form.Group>
          <Form.Group className="col-md-4" controlId={`${idPanel}-orden`}>
            <Form.Label>{t('filtros.orden')}</Form.Label>
            <Form.Select
              value={filtros.ordering || ORDEN_PREDETERMINADO}
              onChange={(evento) => onCambiar({ ordering: evento.target.value === ORDEN_PREDETERMINADO ? '' : evento.target.value })}
            >
              {ORDENES_CATALOGO.map(({ valor, clave }) => <option key={valor} value={valor}>{t(clave)}</option>)}
            </Form.Select>
          </Form.Group>
        </div>

        {servicios.length > 0 && (
          <fieldset className="mt-3">
            <legend className="form-label fs-6 mb-2">{t('filtros.servicios')}</legend>
            <div className="d-flex flex-wrap gap-2">
              {servicios.map(({ id, nombre }) => {
                const elegido = filtros.servicios.includes(String(id));
                return (
                  <Button
                    key={id}
                    variant={elegido ? 'primary' : 'outline-primary'}
                    aria-pressed={elegido}
                    onClick={() => alternarServicio(id)}
                  >
                    {elegido && <Icono nombre="check" tamano={16} />}
                    {nombre}
                  </Button>
                );
              })}
            </div>
          </fieldset>
        )}

        {hayFiltros(filtros) && (
          <div className="mt-3">
            <Button variant="outline-secondary" onClick={onLimpiar}>{t('filtros.limpiar')}</Button>
          </div>
        )}
      </div>
    </form>
  );
}
