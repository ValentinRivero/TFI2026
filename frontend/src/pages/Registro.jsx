import { useState } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import Cargando from '../components/Cargando.jsx';
import FormularioRegistro from '../components/FormularioRegistro.jsx';
import { RUTA_INICIAL_POR_ROL } from '../config/catalogos.js';
import useSesion from '../hooks/useSesion.js';
import { t } from '../i18n/index.js';
import { login, registrar } from '../services/authService.js';

const VACIO = { nombre_completo: '', email: '', telefono: '', password: '' };

export default function Registro() {
  const { autenticado, cargandoSesion, rol } = useSesion();
  const navegar = useNavigate();
  const [valores, setValores] = useState(VACIO);
  const [aceptaPolitica, setAceptaPolitica] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState(null);
  const [intentoSinAceptar, setIntentoSinAceptar] = useState(false);

  if (cargandoSesion) return <Cargando variante="pantalla" />;
  if (autenticado) return <Navigate to={RUTA_INICIAL_POR_ROL[rol] ?? '/'} replace />;

  const enviar = async (evento) => {
    evento.preventDefault();
    setError(null);
    if (!aceptaPolitica) {
      setIntentoSinAceptar(true);
      return;
    }
    setEnviando(true);
    try {
      await registrar({
        nombre_completo: valores.nombre_completo.trim(),
        email: valores.email.trim(),
        telefono: valores.telefono.trim(),
        password: valores.password,
        acepta_politica_privacidad: true,
      });
    } catch (falla) {
      setError(falla);
      setEnviando(false);
      return;
    }
    try {
      await login(valores.email.trim(), valores.password);
    } catch {
      navegar('/login', { replace: true, state: { aviso: t('registro.cuentaCreada') } });
    }
  };

  return (
    <FormularioRegistro
      valores={valores}
      onCambiar={(campo, valor) => setValores((actuales) => ({ ...actuales, [campo]: valor }))}
      aceptaPolitica={aceptaPolitica}
      onAceptarPolitica={setAceptaPolitica}
      intentoSinAceptar={intentoSinAceptar}
      onEnviar={enviar}
      enviando={enviando}
      error={error}
    />
  );
}
