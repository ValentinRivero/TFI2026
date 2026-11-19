import { useCallback, useEffect, useRef, useState } from 'react';
import { t } from '../i18n/index.js';
import { darDeBajaCuenta, obtenerVistaPreviaBaja } from '../services/authService.js';

const CERRADA = Object.freeze({ abierta: false, cargando: false, vistaPrevia: null, error: null, errorBaja: null });

/**
 * Flujo de baja de la cuenta propia. `abrir` consulta primero la vista previa (qué se cancela, qué se conserva y si
 * hay un impedimento); solo `confirmar` ejecuta la baja, y al terminar llama a `alConfirmar` con la sesión ya limpia.
 * Devuelve `{ abierta, cargando, vistaPrevia, error, errorBaja, abrir, cerrar, confirmar }`: `error` es el de la
 * vista previa y `errorBaja`, el de la baja.
 */
export default function useBajaCuenta({ alConfirmar }) {
  const [estado, setEstado] = useState(CERRADA);
  const controlador = useRef(null);

  useEffect(() => () => controlador.current?.abort(), []);

  const abrir = useCallback(() => {
    controlador.current?.abort();
    const actual = new AbortController();
    controlador.current = actual;
    setEstado({ ...CERRADA, abierta: true, cargando: true });
    obtenerVistaPreviaBaja(actual.signal).then(
      (vistaPrevia) => {
        if (!actual.signal.aborted) setEstado((previo) => ({ ...previo, cargando: false, vistaPrevia }));
      },
      (error) => {
        if (!actual.signal.aborted) setEstado((previo) => ({ ...previo, cargando: false, error }));
      },
    );
  }, []);

  const cerrar = useCallback(() => {
    controlador.current?.abort();
    setEstado(CERRADA);
  }, []);

  const confirmar = async () => {
    setEstado((previo) => ({ ...previo, errorBaja: null }));
    try {
      await darDeBajaCuenta({ aviso: t('perfil.bajaRealizada') });
    } catch (falla) {
      setEstado((previo) => ({ ...previo, errorBaja: falla }));
      return;
    }
    alConfirmar();
  };

  return { ...estado, abrir, cerrar, confirmar };
}
