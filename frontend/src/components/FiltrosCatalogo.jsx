import { useEffect, useId, useState } from 'react';
import Button from 'react-bootstrap/Button';
import Form from 'react-bootstrap/Form';
import { COBERTURA, ORDENES_CATALOGO } from '../config/catalogos.js';
import { PARAMETROS } from '../config/parametros.js';
import { t } from '../i18n/index.js';
import { alternarElegido, contarFiltros, hayFiltros } from '../utils/filtrosCatalogo.js';
import FiltroSelect from './FiltroSelect.jsx';
import FiltroServicios from './FiltroServicios.jsx';
import Icono from './Icono.jsx';

const ORDEN_PREDETERMINADO = ORDENES_CATALOGO[0].valor;

const opcionesCobertura = [
  { valor: '', etiqueta: t('filtros.todasCoberturas') },
  ...Object.entries(COBERTURA).map(([codigo, { etiqueta }]) => ({ valor: codigo, etiqueta })),
];
const opcionesOrden = ORDENES_CATALOGO.map(({ valor, clave }) => ({ valor, etiqueta: t(clave) }));

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

  const alternarServicio = (id) => onCambiar({ servicios: alternarElegido(filtros.servicios, id) });

  const opcionesDeporte = [
    { valor: '', etiqueta: t('filtros.todosDeportes') },
    ...deportes.map(({ id, nombre }) => ({ valor: String(id), etiqueta: nombre })),
  ];
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
          <FiltroSelect
            className="col-md-6 col-lg-3"
            etiqueta={t('filtros.deporte')}
            valor={filtros.deporte}
            opciones={opcionesDeporte}
            onCambiar={(deporte) => onCambiar({ deporte })}
          />
          <FiltroSelect
            className="col-md-6 col-lg-3"
            etiqueta={t('filtros.cobertura')}
            valor={filtros.cobertura}
            opciones={opcionesCobertura}
            onCambiar={(cobertura) => onCambiar({ cobertura })}
          />
          {servicios.length > 0 && (
            <FiltroServicios
              className="col-md-6 col-lg-3"
              servicios={servicios}
              elegidos={filtros.servicios}
              onAlternar={alternarServicio}
              onLimpiar={() => onCambiar({ servicios: [] })}
            />
          )}
          <FiltroSelect
            className="col-md-6 col-lg-3"
            etiqueta={t('filtros.orden')}
            valor={filtros.ordering || ORDEN_PREDETERMINADO}
            opciones={opcionesOrden}
            onCambiar={(orden) => onCambiar({ ordering: orden === ORDEN_PREDETERMINADO ? '' : orden })}
          />
        </div>

        {hayFiltros(filtros) && (
          <div className="mt-3">
            <Button variant="outline-secondary" onClick={onLimpiar}>{t('filtros.limpiar')}</Button>
          </div>
        )}
      </div>
    </form>
  );
}
