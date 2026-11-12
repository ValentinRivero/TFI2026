import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import EncabezadoPantalla from '../components/EncabezadoPantalla.jsx';
import FormularioPerfil from '../components/FormularioPerfil.jsx';
import ModalBajaCuenta from '../components/ModalBajaCuenta.jsx';
import SeccionBajaCuenta from '../components/SeccionBajaCuenta.jsx';
import useBajaCuenta from '../hooks/useBajaCuenta.js';
import useSesion from '../hooks/useSesion.js';
import { t } from '../i18n/index.js';
import { actualizarPerfil } from '../services/authService.js';

/** Perfil propio: edición de nombre y teléfono, y baja de la cuenta con vista previa y confirmación expresa. */
export default function Perfil() {
  const { usuario } = useSesion();
  const navegar = useNavigate();
  const [valores, setValores] = useState(() => ({
    nombre_completo: usuario.nombre_completo,
    telefono: usuario.telefono ?? '',
  }));
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState(null);
  const [guardado, setGuardado] = useState(false);

  const baja = useBajaCuenta({
    alConfirmar: () => navegar('/', { replace: true, state: { aviso: t('perfil.bajaRealizada') } }),
  });

  const nombre = valores.nombre_completo.trim();
  const telefono = valores.telefono.trim();
  const hayCambios = nombre !== '' && (nombre !== usuario?.nombre_completo || telefono !== (usuario?.telefono ?? ''));

  const cambiar = (campo, valor) => {
    setGuardado(false);
    setValores((actuales) => ({ ...actuales, [campo]: valor }));
  };

  const guardar = async (evento) => {
    evento.preventDefault();
    setError(null);
    setGuardado(false);
    setEnviando(true);
    try {
      const perfil = await actualizarPerfil({ nombre_completo: nombre, telefono });
      setValores({ nombre_completo: perfil.nombre_completo, telefono: perfil.telefono ?? '' });
      setGuardado(true);
    } catch (falla) {
      setError(falla);
    } finally {
      setEnviando(false);
    }
  };

  // Al confirmarse la baja la sesión se limpia un instante antes de salir de la pantalla.
  if (!usuario) return null;

  return (
    <div className="mx-auto" style={{ maxWidth: '36rem' }}>
      <EncabezadoPantalla titulo={t('perfil.titulo')} descripcion={t('perfil.descripcion')} />
      <FormularioPerfil
        email={usuario.email}
        valores={valores}
        onCambiar={cambiar}
        onEnviar={guardar}
        enviando={enviando}
        hayCambios={hayCambios}
        error={error}
        guardado={guardado}
      />
      <SeccionBajaCuenta onSolicitar={baja.abrir} />
      <ModalBajaCuenta
        mostrar={baja.abierta}
        cargando={baja.cargando}
        vistaPrevia={baja.vistaPrevia}
        error={baja.error}
        errorBaja={baja.errorBaja}
        onReintentar={baja.abrir}
        onConfirmar={baja.confirmar}
        onCancelar={baja.cerrar}
      />
    </div>
  );
}
