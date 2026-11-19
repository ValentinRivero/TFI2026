import { t } from '../i18n/index.js';
import ListaAdmin from './ListaAdmin.jsx';
import TurnoFijoRow from './TurnoFijoRow.jsx';

const COLUMNAS = [
  { clave: 'cancha', etiqueta: t('turnosFijos.columnas.cancha') },
  { clave: 'horario', etiqueta: t('turnosFijos.columnas.horario') },
  { clave: 'vigencia', etiqueta: t('turnosFijos.columnas.vigencia') },
  { clave: 'cliente', etiqueta: t('turnosFijos.columnas.cliente') },
  { clave: 'estado', etiqueta: t('turnosFijos.columnas.estado') },
  { clave: 'acciones', etiqueta: t('turnosFijos.columnas.acciones'), className: 'text-lg-end' },
];

/** Turnos fijos del complejo en una tabla paginada con sus estados (carga, error, vacío). `lista` viene de `useListaPaginada`. */
export default function TablaTurnosFijos({ lista, cambiando, onEditar, onRegistrarFechas, onAlternarPausa, onBaja }) {
  return (
    <ListaAdmin
      lista={lista}
      columnas={COLUMNAS}
      etiqueta={t('turnosFijos.titulo')}
      resumen={t('turnosFijos.resumen', { total: lista.total })}
      errorTitulo={t('turnosFijos.errorTitulo')}
      vacio={{ titulo: t('turnosFijos.vacioTitulo'), descripcion: t('turnosFijos.vacioDescripcion') }}
      renderFila={(turno) => (
        <TurnoFijoRow
          key={turno.id}
          turno={turno}
          ocupado={cambiando === turno.id}
          onEditar={onEditar}
          onRegistrarFechas={onRegistrarFechas}
          onAlternarPausa={onAlternarPausa}
          onBaja={onBaja}
        />
      )}
    />
  );
}
