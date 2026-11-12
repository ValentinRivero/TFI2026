import Alerta from '../components/Alerta.jsx';
import EncabezadoPantalla from '../components/EncabezadoPantalla.jsx';
import FormularioComplejo from '../components/FormularioComplejo.jsx';
import SeccionOperadores from '../components/SeccionOperadores.jsx';
import SelectorServicios from '../components/SelectorServicios.jsx';
import useConfiguracionComplejo from '../hooks/useConfiguracionComplejo.js';
import useContextoPanel from '../hooks/useContextoPanel.js';
import useOperadores from '../hooks/useOperadores.js';
import useServiciosComplejo from '../hooks/useServiciosComplejo.js';
import { t } from '../i18n/index.js';

/**
 * Configuración del complejo activo: perfil comercial, servicios y operadores. El dueño y el superadmin lo editan;
 * el operador lo consulta sin poder modificarlo ni gestionar operadores.
 */
export default function PanelComplejo() {
  const { complejo, actualizarComplejo, permisos } = useContextoPanel();
  const configuracion = useConfiguracionComplejo(complejo, { alGuardar: actualizarComplejo });
  const operadores = useOperadores(complejo.id, { habilitado: permisos.operadores });
  const servicios = useServiciosComplejo(complejo, {
    alGuardar: (lista) => actualizarComplejo({ ...complejo, servicios: lista }),
  });

  return (
    <div>
      <EncabezadoPantalla titulo={t('configuracion.titulo')} descripcion={t('configuracion.descripcion')} />
      {!permisos.configurar && <Alerta variante="info">{t('panel.soloLectura')}</Alerta>}

      <FormularioComplejo
        valores={configuracion.valores}
        errores={configuracion.errores}
        onCambiar={configuracion.cambiar}
        onEnviar={configuracion.enviar}
        onDescartar={configuracion.descartar}
        enviando={configuracion.enviando}
        hayCambios={configuracion.hayCambios}
        error={configuracion.error}
        guardado={configuracion.guardado}
        soloLectura={!permisos.configurar}
      />

      <SelectorServicios
        catalogo={servicios.catalogo}
        elegidos={servicios.elegidos}
        cargando={servicios.cargando}
        errorCatalogo={servicios.errorCatalogo}
        onReintentar={servicios.recargarCatalogo}
        onAlternar={servicios.alternar}
        onGuardar={servicios.guardar}
        enviando={servicios.enviando}
        hayCambios={servicios.hayCambios}
        error={servicios.error}
        guardado={servicios.guardado}
        soloLectura={!permisos.configurar}
      />

      {permisos.operadores && <SeccionOperadores operadores={operadores} />}
    </div>
  );
}
