import { useSearchParams } from 'react-router-dom';
import Alerta from '../components/Alerta.jsx';
import EncabezadoPantalla from '../components/EncabezadoPantalla.jsx';
import FiltrosUsuarios from '../components/FiltrosUsuarios.jsx';
import ModalFichaUsuario from '../components/ModalFichaUsuario.jsx';
import TablaUsuarios from '../components/TablaUsuarios.jsx';
import useUsuarios from '../hooks/useUsuarios.js';
import { t } from '../i18n/index.js';
import { idDeUsuarioEnRuta } from '../utils/sistema.js';

/**
 * Pantalla inicial del sistema (superadmin): cuentas de usuario con filtros por rol, estado y búsqueda. Cada cuenta se
 * abre en una ficha de solo lectura que recién permite editar al habilitar la edición. La auditoría enlaza con
 * `?verUsuario=<id>` para abrir directamente la ficha de una cuenta; al cerrarla, el parámetro se quita de la ruta.
 */
export default function PanelSistema() {
  const [params, setParams] = useSearchParams();
  const idInicial = idDeUsuarioEnRuta(params.get('verUsuario'));
  const usuarios = useUsuarios({ idInicial });

  const cerrarFicha = () => {
    usuarios.ficha.cerrar();
    if (params.has('verUsuario')) setParams({}, { replace: true });
  };

  return (
    <div>
      <EncabezadoPantalla titulo={t('usuarios.titulo')} descripcion={t('usuarios.descripcion')} />
      {usuarios.aviso && <Alerta variante="success" onCerrar={usuarios.descartarAviso}>{usuarios.aviso}</Alerta>}
      {usuarios.errorFicha && (
        <Alerta variante="danger" titulo={t('usuarios.errorFichaTitulo')} onCerrar={() => setParams({}, { replace: true })}>
          {usuarios.errorFicha.mensaje}
        </Alerta>
      )}
      <FiltrosUsuarios filtros={usuarios.filtros} />
      <TablaUsuarios lista={usuarios.lista} onAbrir={usuarios.ficha.abrir} />
      <ModalFichaUsuario ficha={{ ...usuarios.ficha, cerrar: cerrarFicha }} />
    </div>
  );
}
