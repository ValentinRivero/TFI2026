import { useState } from 'react';
import Card from 'react-bootstrap/Card';
import Form from 'react-bootstrap/Form';
import { Link, Navigate, useLocation } from 'react-router-dom';
import Alerta from '../components/Alerta.jsx';
import BotonAccion from '../components/BotonAccion.jsx';
import Cargando from '../components/Cargando.jsx';
import { PARAMETROS } from '../config/parametros.js';
import { RUTA_INICIAL_POR_ROL } from '../config/catalogos.js';
import useSesion from '../hooks/useSesion.js';
import { t } from '../i18n/index.js';
import { login } from '../services/authService.js';

export default function Login() {
  const { autenticado, cargandoSesion, rol } = useSesion();
  const ubicacion = useLocation();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
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
      await login(email.trim(), password);
    } catch (falla) {
      setError(falla);
      setEnviando(false);
    }
  };

  const aviso = ubicacion.state?.aviso ?? (ubicacion.state?.desde ? t('login.sesionVencida') : null);

  return (
    <div className="mx-auto" style={{ maxWidth: '28rem' }}>
      <h1 className="h2">{t('login.titulo')}</h1>
      <p className="text-secondary">{t('login.descripcion')}</p>
      {aviso && <Alerta variante="info">{aviso}</Alerta>}
      <Card body>
        <Form onSubmit={enviar} noValidate>
          {error && <Alerta variante="danger">{error.mensaje}</Alerta>}
          <Form.Group className="mb-3" controlId="login-email">
            <Form.Label>{t('login.email')}</Form.Label>
            <Form.Control
              type="email"
              autoComplete="email"
              inputMode="email"
              required
              maxLength={PARAMETROS.limitesCampos.email}
              value={email}
              onChange={(evento) => setEmail(evento.target.value)}
            />
          </Form.Group>
          <Form.Group className="mb-4" controlId="login-password">
            <Form.Label>{t('login.password')}</Form.Label>
            <Form.Control
              type="password"
              autoComplete="current-password"
              required
              maxLength={PARAMETROS.limitesCampos.password}
              value={password}
              onChange={(evento) => setPassword(evento.target.value)}
            />
          </Form.Group>
          <BotonAccion type="submit" className="w-100" cargando={enviando} textoCargando={t('login.ingresando')}>
            {t('login.enviar')}
          </BotonAccion>
        </Form>
      </Card>
      <p className="mt-3 mb-0 text-center">
        {t('login.sinCuenta')} <Link to="/registro">{t('login.crearCuenta')}</Link>
      </p>
    </div>
  );
}
