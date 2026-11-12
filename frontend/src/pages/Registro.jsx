import { useState } from 'react';
import Card from 'react-bootstrap/Card';
import Form from 'react-bootstrap/Form';
import { Link, Navigate, useNavigate } from 'react-router-dom';
import Alerta from '../components/Alerta.jsx';
import BotonAccion from '../components/BotonAccion.jsx';
import Cargando from '../components/Cargando.jsx';
import { RUTA_INICIAL_POR_ROL } from '../config/catalogos.js';
import { PARAMETROS } from '../config/parametros.js';
import useSesion from '../hooks/useSesion.js';
import { t } from '../i18n/index.js';
import { login, registrar } from '../services/authService.js';

const VACIO = { nombre_completo: '', email: '', telefono: '', password: '' };

export default function Registro() {
  const { autenticado, cargandoSesion, rol } = useSesion();
  const navegar = useNavigate();
  const [datos, setDatos] = useState(VACIO);
  // La casilla nunca viene marcada: el consentimiento tiene que ser expreso.
  const [aceptaPolitica, setAceptaPolitica] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState(null);
  const [intentoSinAceptar, setIntentoSinAceptar] = useState(false);

  if (cargandoSesion) return <Cargando variante="pantalla" />;
  if (autenticado) return <Navigate to={RUTA_INICIAL_POR_ROL[rol] ?? '/'} replace />;

  const cambiar = (campo) => (evento) => setDatos((actual) => ({ ...actual, [campo]: evento.target.value }));
  const campos = error?.campos ?? {};
  const { limitesCampos } = PARAMETROS;

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
        nombre_completo: datos.nombre_completo.trim(),
        email: datos.email.trim(),
        telefono: datos.telefono.trim(),
        password: datos.password,
        acepta_politica_privacidad: true,
      });
    } catch (falla) {
      setError(falla);
      setEnviando(false);
      return;
    }
    try {
      await login(datos.email.trim(), datos.password);
    } catch {
      navegar('/login', { replace: true, state: { aviso: t('registro.cuentaCreada') } });
    }
  };

  const campoDeTexto = (id, etiqueta, nombre, { ayuda, ...propiedades }) => (
    <Form.Group className="mb-3" controlId={`registro-${id}`}>
      <Form.Label>{etiqueta}</Form.Label>
      <Form.Control
        value={datos[nombre]}
        onChange={cambiar(nombre)}
        isInvalid={Boolean(campos[nombre])}
        {...propiedades}
      />
      <Form.Control.Feedback type="invalid">{campos[nombre]}</Form.Control.Feedback>
      {ayuda && <Form.Text muted>{ayuda}</Form.Text>}
    </Form.Group>
  );

  return (
    <div className="mx-auto" style={{ maxWidth: '32rem' }}>
      <h1 className="h2">{t('registro.titulo')}</h1>
      <p className="text-secondary">{t('registro.descripcion')}</p>
      <Card body>
        <Form onSubmit={enviar} noValidate>
          {error && <Alerta variante="danger">{error.mensaje}</Alerta>}
          {campoDeTexto('nombre', t('registro.nombre'), 'nombre_completo', {
            autoComplete: 'name', required: true, maxLength: limitesCampos.nombre,
          })}
          {campoDeTexto('email', t('registro.email'), 'email', {
            type: 'email', autoComplete: 'email', inputMode: 'email', required: true, maxLength: limitesCampos.email,
          })}
          {campoDeTexto('telefono', t('registro.telefono'), 'telefono', {
            type: 'tel', autoComplete: 'tel', inputMode: 'tel', maxLength: limitesCampos.telefono,
            ayuda: t('registro.ayudaTelefono'),
          })}
          {campoDeTexto('password', t('registro.password'), 'password', {
            type: 'password', autoComplete: 'new-password', required: true, minLength: PARAMETROS.password.largoMinimo,
            maxLength: limitesCampos.password, ayuda: t('registro.ayudaPassword', { largo: PARAMETROS.password.largoMinimo }),
          })}
          <Form.Group className="mb-4" controlId="registro-politica">
            <Form.Check
              type="checkbox"
              checked={aceptaPolitica}
              onChange={(evento) => setAceptaPolitica(evento.target.checked)}
              isInvalid={Boolean(campos.acepta_politica_privacidad) || (intentoSinAceptar && !aceptaPolitica)}
              feedback={campos.acepta_politica_privacidad ?? t('registro.debeAceptar')}
              feedbackType="invalid"
              label={(
                <>
                  {t('registro.aceptoPoliticaAntes')}
                  <Link to="/privacidad" target="_blank" rel="noopener">{t('registro.aceptoPoliticaLink')}</Link>
                </>
              )}
            />
          </Form.Group>
          <BotonAccion type="submit" className="w-100" cargando={enviando} textoCargando={t('registro.creando')}>
            {t('registro.enviar')}
          </BotonAccion>
        </Form>
      </Card>
      <p className="mt-3 mb-0 text-center">
        {t('registro.conCuenta')} <Link to="/login">{t('registro.iniciarSesion')}</Link>
      </p>
    </div>
  );
}
