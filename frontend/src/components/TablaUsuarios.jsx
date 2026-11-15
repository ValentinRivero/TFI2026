import { t } from '../i18n/index.js';
import ListaAdmin from './ListaAdmin.jsx';
import UsuarioRow from './UsuarioRow.jsx';

const COLUMNAS = [
  { clave: 'id', etiqueta: t('usuarios.columnas.id') },
  { clave: 'cuenta', etiqueta: t('usuarios.columnas.cuenta') },
  { clave: 'rol', etiqueta: t('usuarios.columnas.rol') },
  { clave: 'complejo', etiqueta: t('usuarios.columnas.complejo') },
  { clave: 'estado', etiqueta: t('usuarios.columnas.estado') },
  { clave: 'alta', etiqueta: t('usuarios.columnas.alta') },
  { clave: 'acciones', etiqueta: t('usuarios.columnas.acciones'), className: 'text-lg-end' },
];

/** Cuentas en una tabla paginada con sus estados (carga, error, vacío). `lista` viene de `useListaPaginada`. */
export default function TablaUsuarios({ lista, onAbrir }) {
  return (
    <ListaAdmin
      lista={lista}
      columnas={COLUMNAS}
      etiqueta={t('usuarios.titulo')}
      resumen={t('usuarios.resumen', { total: lista.total })}
      errorTitulo={t('usuarios.errorTitulo')}
      vacio={{ titulo: t('usuarios.vacioTitulo'), descripcion: t('usuarios.vacioDescripcion') }}
      renderFila={(usuario) => <UsuarioRow key={usuario.id} usuario={usuario} onAbrir={onAbrir} />}
    />
  );
}
