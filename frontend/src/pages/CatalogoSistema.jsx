import Button from 'react-bootstrap/Button';
import Alerta from '../components/Alerta.jsx';
import EncabezadoPantalla from '../components/EncabezadoPantalla.jsx';
import ModalConfirmarAccion from '../components/ModalConfirmarAccion.jsx';
import ModalNombreCatalogo from '../components/ModalNombreCatalogo.jsx';
import TablaCatalogoSistema from '../components/TablaCatalogoSistema.jsx';
import useCatalogoSistema from '../hooks/useCatalogoSistema.js';
import { t } from '../i18n/index.js';
import { CATALOGOS_SISTEMA, textoDeUsos } from '../utils/catalogoSistema.js';

/**
 * Administración de un catálogo maestro (deportes o servicios) del superadmin. Es la misma pantalla para ambos: el
 * recurso (`deportes` o `servicios`) decide la ruta de la API, los límites del nombre y los textos.
 */
export default function CatalogoSistema({ recurso }) {
  const { textos } = CATALOGOS_SISTEMA[recurso];
  const catalogo = useCatalogoSistema(recurso);
  const { baja, formulario } = catalogo;
  const enUso = baja.objetivo && baja.objetivo.usos > 0;

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
      <TablaCatalogoSistema recurso={recurso} catalogo={catalogo} />
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
      />
    </div>
  );
}
