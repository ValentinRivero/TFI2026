import { t } from '../i18n/index.js';
import ExcepcionRow from './ExcepcionRow.jsx';
import ListaAdmin from './ListaAdmin.jsx';

const COLUMNAS = [
  { clave: 'alcance', etiqueta: t('excepciones.columnas.alcance') },
  { clave: 'fechas', etiqueta: t('excepciones.columnas.fechas') },
  { clave: 'horario', etiqueta: t('excepciones.columnas.horario') },
  { clave: 'motivo', etiqueta: t('excepciones.columnas.motivo') },
  { clave: 'descripcion', etiqueta: t('excepciones.columnas.descripcion') },
  { clave: 'acciones', etiqueta: t('excepciones.columnas.acciones'), className: 'text-lg-end' },
];

/** Excepciones del complejo en una tabla paginada con sus estados (carga, error, vacío). `lista` viene de `useListaPaginada`. */
export default function TablaExcepciones({ lista, onBaja }) {
  return (
    <ListaAdmin
      lista={lista}
      columnas={COLUMNAS}
      etiqueta={t('excepciones.titulo')}
      resumen={t('excepciones.resumen', { total: lista.total })}
      errorTitulo={t('excepciones.errorTitulo')}
      vacio={{ titulo: t('excepciones.vacioTitulo'), descripcion: t('excepciones.vacioDescripcion') }}
      renderFila={(excepcion) => <ExcepcionRow key={excepcion.id} excepcion={excepcion} onBaja={onBaja} />}
    />
  );
}
