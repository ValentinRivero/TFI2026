import { t } from '../i18n/index.js';
import ContratoRow from './ContratoRow.jsx';
import ListaAdmin from './ListaAdmin.jsx';

const COLUMNAS = [
  { clave: 'id', etiqueta: t('contratos.columnas.id') },
  { clave: 'complejo', etiqueta: t('contratos.columnas.complejo') },
  { clave: 'propietario', etiqueta: t('contratos.columnas.propietario') },
  { clave: 'estado', etiqueta: t('contratos.columnas.estado') },
  { clave: 'alta', etiqueta: t('contratos.columnas.alta') },
  { clave: 'acciones', etiqueta: t('contratos.columnas.acciones'), className: 'text-lg-end' },
];

/** Contratos en una tabla paginada con sus estados (carga, error, vacío). `lista` viene de `useListaPaginada`. */
export default function TablaContratos({ lista, onCambiarEstado }) {
  return (
    <ListaAdmin
      lista={lista}
      columnas={COLUMNAS}
      etiqueta={t('contratos.titulo')}
      resumen={t('contratos.resumen', { total: lista.total })}
      errorTitulo={t('contratos.errorTitulo')}
      vacio={{ titulo: t('contratos.vacioTitulo'), descripcion: t('contratos.vacioDescripcion') }}
      renderFila={(contrato) => <ContratoRow key={contrato.id} contrato={contrato} onCambiarEstado={onCambiarEstado} />}
    />
  );
}
