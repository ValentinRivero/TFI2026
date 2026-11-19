import { useRef, useState } from 'react';
import {
  actualizarHorario,
  crearHorario,
  darDeBajaHorario,
  listarHorarios,
} from '../services/canchaService.js';
import { conConfirmacion, leerConflictos } from '../utils/conflictos.js';
import { aFilaBorrador, calcularCambios, filaNueva, hayCambios, validarBorrador } from '../utils/horarios.js';
import useConsulta from './useConsulta.js';

/** Cola de operaciones en el orden que libera horario antes de ocuparlo: bajas, modificaciones y altas. */
const armarCola = ({ bajas, modificaciones, altas }) => [
  ...bajas.map((id) => ({ tipo: 'baja', id })),
  ...modificaciones.map(({ id, cambios }) => ({ tipo: 'modificacion', id, cambios })),
  ...altas.map((cuerpo) => ({ tipo: 'alta', cuerpo })),
];

/**
 * Editor semanal de los rangos de apertura de una cancha. Mantiene un borrador local y, al guardar, aplica la
 * diferencia con las llamadas granulares de la API (el backend valida cada una y no hay un reemplazo en bloque).
 *
 * Si un cambio deja reservas o turnos fijos fuera de la grilla, el servidor responde 409: la cola se pausa, `conflicto`
 * muestra el detalle y `confirmarConflicto` reintenta esa operación con `confirmar: true` y sigue con el resto. Si el
 * usuario cancela, lo ya aplicado se conserva y el borrador sigue con lo que falta. Ante cualquier otro error, el
 * borrador se descarta y se recarga lo guardado, para no repetir altas ya aplicadas.
 *
 * `cancha` puede ser `null` (no hay editor abierto).
 */
export default function useEditorHorarios(cancha) {
  const canchaId = cancha?.id ?? null;
  const consulta = useConsulta(
    async (signal) => (canchaId === null ? [] : (await listarHorarios(canchaId, signal)).map(aFilaBorrador)),
    [canchaId],
  );
  const base = consulta.datos ?? [];

  // `null` significa "sin ediciones": el borrador refleja lo guardado.
  const [borrador, setBorrador] = useState(null);
  const [origen, setOrigen] = useState(canchaId);
  const [intentado, setIntentado] = useState(false);
  const [aplicando, setAplicando] = useState(false);
  const [error, setError] = useState(null);
  const [guardado, setGuardado] = useState(false);
  const [pendiente, setPendiente] = useState(null);
  const contador = useRef(0);

  if (origen !== canchaId) {
    setOrigen(canchaId);
    setBorrador(null);
    setIntentado(false);
    setError(null);
    setGuardado(false);
    setPendiente(null);
  }

  const filas = borrador ?? base;
  const errores = validarBorrador(filas);
  const cambios = calcularCambios(base, filas);

  const editar = (actualizar) => {
    setGuardado(false);
    setError(null);
    setBorrador((actual) => actualizar(actual ?? base));
  };

  const agregar = (dia) => {
    contador.current += 1;
    editar((actuales) => [...actuales, filaNueva(dia, `nuevo-${contador.current}`)]);
  };

  const cambiar = (clave, campo, valor) => editar((actuales) => (
    actuales.map((fila) => (fila.clave === clave ? { ...fila, [campo]: valor } : fila))
  ));

  const quitar = (clave) => editar((actuales) => actuales.filter((fila) => fila.clave !== clave));

  const descartar = () => {
    setBorrador(null);
    setIntentado(false);
    setError(null);
    setGuardado(false);
  };

  const ejecutar = (operacion, confirmar) => {
    if (operacion.tipo === 'baja') return darDeBajaHorario(operacion.id, { confirmar });
    if (operacion.tipo === 'modificacion') {
      return actualizarHorario(operacion.id, confirmar ? conConfirmacion(operacion.cambios) : operacion.cambios);
    }
    return crearHorario(canchaId, operacion.cuerpo);
  };

  const aplicarCola = async (cola, confirmarPrimera) => {
    setAplicando(true);
    setError(null);
    try {
      for (let indice = 0; indice < cola.length; indice += 1) {
        try {
          // En serie a propósito: cada paso libera o toma el horario del siguiente.
          await ejecutar(cola[indice], confirmarPrimera && indice === 0);
        } catch (falla) {
          const detalle = leerConflictos(falla);
          if (detalle) {
            setPendiente({ cola: cola.slice(indice), conflictos: detalle });
            return;
          }
          setError(falla);
          setBorrador(null);
          setPendiente(null);
          consulta.recargar();
          return;
        }
      }
      setBorrador(null);
      setPendiente(null);
      setIntentado(false);
      setGuardado(true);
      consulta.recargar();
    } finally {
      setAplicando(false);
    }
  };

  const guardar = async () => {
    setIntentado(true);
    if (Object.keys(errores).length > 0 || !hayCambios(cambios)) return;
    await aplicarCola(armarCola(cambios), false);
  };

  const cancelarConflicto = () => {
    setPendiente(null);
    // Lo aplicado antes del conflicto ya es lo guardado: se recarga y el borrador conserva el resto.
    consulta.recargar();
  };

  return {
    filas,
    errores: intentado ? errores : {},
    cargando: consulta.cargando && !consulta.datos,
    errorCarga: consulta.error,
    recargar: consulta.recargar,
    agregar,
    cambiar,
    quitar,
    descartar,
    guardar,
    aplicando,
    error,
    guardado,
    hayCambios: hayCambios(cambios),
    conflicto: pendiente?.conflictos ?? null,
    confirmarConflicto: () => aplicarCola(pendiente.cola, true),
    cancelarConflicto,
  };
}
