import { useEffect, useRef, useState } from 'react';
import Button from 'react-bootstrap/Button';
import Cargando from './Cargando.jsx';

/**
 * Botón de una acción asíncrona. Si `onClick` devuelve una promesa, muestra `Cargando` y se deshabilita hasta que
 * termina: evita el doble envío (reservas, altas, cancelaciones). `onClick` debe atrapar sus propios errores.
 * `cargando` permite que la pantalla controle el estado cuando la acción no pasa por `onClick`.
 */
export default function BotonAccion({
  children,
  onClick,
  cargando = false,
  disabled = false,
  textoCargando,
  variant = 'primary',
  type = 'button',
  ...resto
}) {
  const [ejecutando, setEjecutando] = useState(false);
  const montado = useRef(true);

  useEffect(() => {
    montado.current = true;
    return () => {
      montado.current = false;
    };
  }, []);

  const ocupado = cargando || ejecutando;

  const manejar = async (evento) => {
    if (ocupado || !onClick) return;
    const resultado = onClick(evento);
    if (resultado && typeof resultado.then === 'function') {
      setEjecutando(true);
      try {
        await resultado;
      } finally {
        if (montado.current) setEjecutando(false);
      }
    }
  };

  return (
    <Button variant={variant} type={type} disabled={disabled || ocupado} aria-busy={ocupado} onClick={manejar} {...resto}>
      {ocupado && <Cargando variante="boton" texto={textoCargando} />}
      {children}
    </Button>
  );
}
