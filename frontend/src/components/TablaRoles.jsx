import Button from 'react-bootstrap/Button';
import { t } from '../i18n/index.js';
import ListaAdmin from './ListaAdmin.jsx';
import RolRow from './RolRow.jsx';

const COLUMNAS = [
  { clave: 'nombre', etiqueta: t('roles.columnas.nombre') },
  { clave: 'descripcion', etiqueta: t('roles.columnas.descripcion') },
  { clave: 'estado', etiqueta: t('roles.columnas.estado') },
  { clave: 'usos', etiqueta: t('roles.columnas.usos') },
  { clave: 'permisos', etiqueta: t('roles.columnas.permisos') },
  { clave: 'acciones', etiqueta: t('roles.columnas.acciones'), className: 'text-lg-end' },
];

/**
 * Roles con sus estados de carga, error y vacío. `roles` es lo que devuelve `useRolesSistema`; `onVerUsos(rol)` abre las
 * cuentas que lo usan. Con la búsqueda sin coincidencias ofrece limpiar los filtros.
 */
export default function TablaRoles({ roles, onVerUsos }) {
  const { lista, ficha, formulario, baja, filtros } = roles;

  return (
    <ListaAdmin
      lista={lista}
      columnas={COLUMNAS}
      etiqueta={t('roles.titulo')}
      resumen={t('roles.resumen', { total: lista.total })}
      errorTitulo={t('roles.errorTitulo')}
      vacio={roles.hayItems && filtros.activos ? {
        titulo: t('catalogoSistema.filtros.sinResultadosTitulo'),
        descripcion: t('catalogoSistema.filtros.sinResultados'),
        children: <Button variant="outline-primary" onClick={filtros.limpiar}>{t('comun.limpiarFiltros')}</Button>,
      } : { titulo: t('roles.vacioTitulo'), descripcion: t('roles.vacioDescripcion') }}
      renderFila={(rol) => (
        <RolRow
          key={rol.id}
          rol={rol}
          onVerUsos={onVerUsos}
          onVerPermisos={ficha.abrir}
          onEditar={formulario.abrir}
          onDarDeBaja={baja.pedir}
          onReactivar={roles.reactivar}
        />
      )}
    />
  );
}
