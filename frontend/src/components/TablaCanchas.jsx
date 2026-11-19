import Button from 'react-bootstrap/Button';
import { t } from '../i18n/index.js';
import CanchaRow from './CanchaRow.jsx';
import ListaAdmin from './ListaAdmin.jsx';

const COLUMNAS = [
  { clave: 'nombre', etiqueta: t('gestionCanchas.columnas.nombre') },
  { clave: 'deporte', etiqueta: t('gestionCanchas.columnas.deporte') },
  { clave: 'caracteristicas', etiqueta: t('gestionCanchas.columnas.caracteristicas') },
  { clave: 'turno', etiqueta: t('gestionCanchas.columnas.turno') },
  { clave: 'precio', etiqueta: t('gestionCanchas.columnas.precio') },
  { clave: 'estado', etiqueta: t('gestionCanchas.columnas.estado') },
  { clave: 'acciones', etiqueta: t('gestionCanchas.columnas.acciones'), className: 'text-lg-end' },
];

/** Canchas del complejo en una tabla paginada con sus estados (carga, error, vacío). `lista` viene de `useListaPaginada`. */
export default function TablaCanchas({ lista, puedeAdministrar, onNueva, onHorarios, onEditar, onBaja }) {
  return (
    <ListaAdmin
      lista={lista}
      columnas={COLUMNAS}
      etiqueta={t('gestionCanchas.titulo')}
      resumen={t('gestionCanchas.resumen', { total: lista.total })}
      errorTitulo={t('gestionCanchas.errorTitulo')}
      vacio={{
        titulo: t('gestionCanchas.vacioTitulo'),
        descripcion: t(puedeAdministrar ? 'gestionCanchas.vacioDescripcion' : 'gestionCanchas.vacioConsulta'),
        children: puedeAdministrar && <Button onClick={onNueva}>{t('gestionCanchas.nueva')}</Button>,
      }}
      renderFila={(cancha) => (
        <CanchaRow
          key={cancha.id}
          cancha={cancha}
          puedeAdministrar={puedeAdministrar}
          onHorarios={onHorarios}
          onEditar={onEditar}
          onBaja={onBaja}
        />
      )}
    />
  );
}
