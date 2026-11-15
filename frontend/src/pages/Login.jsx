import { useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import Cargando from '../components/Cargando.jsx';
import FormularioLogin from '../components/FormularioLogin.jsx';
import { RUTA_INICIAL_POR_ROL } from '../config/catalogos.js';
import useSesion from '../hooks/useSesion.js';
import { t } from '../i18n/index.js';
import { login } from '../services/authService.js';
import { rutaDeRetorno } from '../utils/retornoReserva.js';
import { validarLogin } from '../utils/validacionesCuenta.js';

export default function Login() {
  const { autenticado, cargandoSesion, rol } = useSesion();
  const ubicacion = useLocation();
  const [valores, setValores] = useState({ email: '', password: '' });
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState(null);
  const [errores, setErrores] = useState({});

  if (cargandoSesion) return <Cargando variante="pantalla" />;
  // Con sesión (recién iniciada o previa) se vuelve a la ruta de origen o a la pantalla inicial del rol.
  if (autenticado) return <Navigate to={rutaDeRetorno(ubicacion.state?.desde) ?? RUTA_INICIAL_POR_ROL[rol] ?? '/'} replace />;

  const enviar = async (evento) => {
    evento.preventDefault();
    setError(null);
    const invalidos = validarLogin(valores);
    setErrores(invalidos);
    if (Object.keys(invalidos).length > 0) return;
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
      errores={errores}
      onCambiar={(campo, valor) => {
        setValores((actuales) => ({ ...actuales, [campo]: valor }));
        setErrores(({ [campo]: _corregido, ...resto }) => resto);
      }}
      onEnviar={enviar}
      enviando={enviando}
      error={error}
      aviso={ubicacion.state?.aviso ?? (ubicacion.state?.desde ? t('login.sesionVencida') : null)}
      estadoRegistro={ubicacion.state?.desde ? { desde: ubicacion.state.desde } : undefined}
    />
  );
}
