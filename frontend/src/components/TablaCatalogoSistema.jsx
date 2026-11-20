import Button from 'react-bootstrap/Button';
import { t } from '../i18n/index.js';
import { CATALOGOS_SISTEMA } from '../utils/catalogoSistema.js';
import CatalogoItemRow from './CatalogoItemRow.jsx';
import ListaAdmin from './ListaAdmin.jsx';

const COLUMNAS = [
  { clave: 'nombre', etiqueta: t('catalogoSistema.columnas.nombre') },
  { clave: 'estado', etiqueta: t('catalogoSistema.columnas.estado') },
  { clave: 'usos', etiqueta: t('catalogoSistema.columnas.usos') },
  { clave: 'acciones', etiqueta: t('catalogoSistema.columnas.acciones'), className: 'text-lg-end' },
];

/**
 * Ítems de un catálogo maestro (deportes o servicios) con sus estados de carga, error y vacío. `catalogo` es lo que
 * devuelve `useCatalogoSistema`; `recurso`, una clave de `CATALOGOS_SISTEMA`; `onVerUsos(item)` abre dónde está en uso.
 * Con la búsqueda sin coincidencias ofrece limpiar los filtros.
 */
export default function TablaCatalogoSistema({ recurso, catalogo, onVerUsos }) {
  const { textos } = CATALOGOS_SISTEMA[recurso];
  const { lista, formulario, baja, filtros } = catalogo;
  const sinCoincidencias = catalogo.hayItems && filtros.activos;

  return (
    <ListaAdmin
      lista={lista}
      columnas={COLUMNAS}
      etiqueta={t(`${textos}.titulo`)}
      resumen={t(`${textos}.resumen`, { total: lista.total })}
      errorTitulo={t(`${textos}.errorTitulo`)}
      vacio={sinCoincidencias ? {
        titulo: t('catalogoSistema.filtros.sinResultadosTitulo'),
        descripcion: t('catalogoSistema.filtros.sinResultados'),
        children: <Button variant="outline-primary" onClick={filtros.limpiar}>{t('comun.limpiarFiltros')}</Button>,
      } : {
        titulo: t(`${textos}.vacioTitulo`),
        descripcion: t(`${textos}.vacioDescripcion`),
        children: <Button onClick={() => formulario.abrir(null)}>{t(`${textos}.nuevo`)}</Button>,
      }}
      renderFila={(item) => (
        <CatalogoItemRow
          key={item.id}
          recurso={recurso}
          item={item}
          onVerUsos={onVerUsos}
          onEditar={formulario.abrir}
          onDarDeBaja={baja.pedir}
          onReactivar={catalogo.reactivar}
        />
      )}
    />
  );
}
