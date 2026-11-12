import { t } from '../i18n/index.js';
import ListaAdmin from './ListaAdmin.jsx';
import ReservaAgendaRow from './ReservaAgendaRow.jsx';

const COLUMNAS = [
  { clave: 'horario', etiqueta: t('agenda.columnas.horario') },
  { clave: 'cancha', etiqueta: t('agenda.columnas.cancha') },
  { clave: 'cliente', etiqueta: t('agenda.columnas.cliente') },
  { clave: 'origen', etiqueta: t('agenda.columnas.origen') },
  { clave: 'precio', etiqueta: t('agenda.columnas.precio') },
  { clave: 'estado', etiqueta: t('agenda.columnas.estado') },
  { clave: 'observaciones', etiqueta: t('agenda.columnas.observaciones') },
  { clave: 'acciones', etiqueta: t('agenda.columnas.acciones'), className: 'text-lg-end' },
];

/** Reservas de la agenda en una tabla paginada con sus estados (carga, error, vacío). `lista` viene de `useListaPaginada`. */
export default function TablaAgenda({ lista, cambiando, onCambiarEstado, onCancelar, onReabrir }) {
  return (
    <ListaAdmin
      lista={lista}
      columnas={COLUMNAS}
      etiqueta={t('agenda.titulo')}
      resumen={t('agenda.resumen', { total: lista.total })}
      errorTitulo={t('agenda.errorTitulo')}
      vacio={{ titulo: t('agenda.vacioTitulo'), descripcion: t('agenda.vacioDescripcion') }}
      renderFila={(reserva) => (
        <ReservaAgendaRow
          key={reserva.id}
          reserva={reserva}
          ocupada={cambiando === reserva.id}
          onCambiarEstado={onCambiarEstado}
          onCancelar={onCancelar}
          onReabrir={onReabrir}
        />
      )}
    />
  );
}
