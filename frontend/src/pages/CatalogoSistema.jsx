import Button from 'react-bootstrap/Button';
import Alerta from '../components/Alerta.jsx';
import BarraBusquedaLocal from '../components/BarraBusquedaLocal.jsx';
import EncabezadoPantalla from '../components/EncabezadoPantalla.jsx';
import ListaUsos from '../components/ListaUsos.jsx';
import ModalConfirmarAccion from '../components/ModalConfirmarAccion.jsx';
import ModalNombreCatalogo from '../components/ModalNombreCatalogo.jsx';
import ModalUsos from '../components/ModalUsos.jsx';
import TablaCatalogoSistema from '../components/TablaCatalogoSistema.jsx';
import useAdministrarComplejo from '../hooks/useAdministrarComplejo.js';
import useCatalogoSistema from '../hooks/useCatalogoSistema.js';
import useDetalleDeUsos from '../hooks/useDetalleDeUsos.js';
import { t } from '../i18n/index.js';
import { CATALOGOS_SISTEMA, textoDeUsos } from '../utils/catalogoSistema.js';

/**
 * Administración de un catálogo maestro (deportes o servicios) del superadmin. Es la misma pantalla para ambos: el
 * recurso (`deportes` o `servicios`) decide la ruta de la API, los límites del nombre y los textos. Cada ítem en uso
 * muestra dónde (también al intentar darlo de baja) y lleva directo al complejo en `/panel`.
 */
export default function CatalogoSistema({ recurso }) {
  const { textos, rutaPanel } = CATALOGOS_SISTEMA[recurso];
  const catalogo = useCatalogoSistema(recurso);
  const { baja, formulario } = catalogo;
  const enUso = baja.objetivo && baja.objetivo.usos > 0;
  const detalle = useDetalleDeUsos(recurso, baja.objetivo);
  const administrar = useAdministrarComplejo();
  const irAlComplejo = (complejoId) => administrar({ id: complejoId }, rutaPanel);

  return (
    <div>
      <EncabezadoPantalla
        titulo={t(`${textos}.titulo`)}
        descripcion={t(`${textos}.descripcion`)}
        acciones={<Button onClick={() => formulario.abrir(null)}>{t(`${textos}.nuevo`)}</Button>}
      />
      {catalogo.aviso && <Alerta variante="success" onCerrar={catalogo.descartarAviso}>{catalogo.aviso}</Alerta>}
      {catalogo.errorReactivacion && (
        <Alerta variante="danger" onCerrar={catalogo.descartarErrorReactivacion}>{catalogo.errorReactivacion.mensaje}</Alerta>
      )}
      {catalogo.hayItems && (
        <BarraBusquedaLocal id={`catalogo-${recurso}`} etiquetaBusqueda={t(`${textos}.buscar`)} filtros={catalogo.filtros} />
      )}
      <TablaCatalogoSistema recurso={recurso} catalogo={catalogo} onVerUsos={detalle.abrir} />
      <ModalUsos tipo={recurso} detalle={detalle} onIrAlComplejo={irAlComplejo} />
      <ModalNombreCatalogo recurso={recurso} formulario={formulario} />
      <ModalConfirmarAccion
        abierto={baja.objetivo !== null}
        titulo={t(`${textos}.bajaTitulo`)}
        texto={baja.objetivo && (
          enUso
            ? t(`${textos}.bajaTextoEnUso`, { nombre: baja.objetivo.nombre, usos: textoDeUsos(recurso, baja.objetivo.usos) })
            : t(`${textos}.bajaTexto`, { nombre: baja.objetivo.nombre })
        )}
        error={baja.error}
        textoConfirmar={t('catalogoSistema.darDeBaja')}
        onConfirmar={baja.confirmar}
        onCancelar={baja.cerrar}
      >
        {enUso && <ListaUsos tipo={recurso} usos={detalle.lista} onIrAlComplejo={irAlComplejo} />}
      </ModalConfirmarAccion>
    </div>
  );
}
