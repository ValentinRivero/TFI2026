import { useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import Cargando from '../components/Cargando.jsx';
import FormularioLogin from '../components/FormularioLogin.jsx';
import { RUTA_INICIAL_POR_ROL } from '../config/catalogos.js';
import useSesion from '../hooks/useSesion.js';
import { t } from '../i18n/index.js';
import { login } from '../services/authService.js';

export default function Login() {
  const { autenticado, cargandoSesion, rol } = useSesion();
  const ubicacion = useLocation();
  const [valores, setValores] = useState({ email: '', password: '' });
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState(null);

  if (cargandoSesion) return <Cargando variante="pantalla" />;
  // Con sesión (recién iniciada o previa) se vuelve a la ruta de origen o a la pantalla inicial del rol.
  if (autenticado) return <Navigate to={ubicacion.state?.desde?.pathname ?? RUTA_INICIAL_POR_ROL[rol] ?? '/'} replace />;

  const enviar = async (evento) => {
    evento.preventDefault();
    setError(null);
    setEnviando(true);
    try {
      await login(valores.email.trim(), valores.password);
    } catch (falla) {
      setError(falla);
      setEnviando(false);
    }
  };

  return (
    <FormularioLogin
      valores={valores}
      onCambiar={(campo, valor) => setValores((actuales) => ({ ...actuales, [campo]: valor }))}
      onEnviar={enviar}
      enviando={enviando}
      error={error}
      aviso={ubicacion.state?.aviso ?? (ubicacion.state?.desde ? t('login.sesionVencida') : null)}
    />
  );
}
