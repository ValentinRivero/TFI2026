import { useState } from 'react';
import { desvincularOperador, listarOperadores, vincularOperador } from '../services/complejoAdminService.js';
import useEnvio from './useEnvio.js';
import useListaPaginada from './useListaPaginada.js';

/**
 * Operadores del complejo: lista paginada, vinculación por email exacto y desvinculación con confirmación.
 * El mensaje de "no disponible" del backend es unificado a propósito (no revela si la cuenta existe) y se muestra
 * tal cual en el campo del email.
 */
export default function useOperadores(complejoId, { habilitado = true } = {}) {
  // Sin permiso para verlos (operador) no se pide la lista: el backend respondería 403.
  const lista = useListaPaginada(
    async (pagina, signal) => (habilitado ? listarOperadores(complejoId, pagina, signal) : { count: 0, results: [] }),
    [complejoId, habilitado],
  );
  const [email, setEmail] = useState('');
  const [aviso, setAviso] = useState(null);
  const [aDesvincular, setADesvincular] = useState(null);
  const alta = useEnvio();
  const baja = useEnvio();

  const cambiarEmail = (valor) => {
    alta.limpiar();
    setEmail(valor);
  };

  const vincular = async (evento) => {
    evento.preventDefault();
    const correo = email.trim();
    if (correo === '') return;
    setAviso(null);
    const resultado = await alta.enviar(() => vincularOperador(complejoId, correo));
    if (!resultado.ok) return;
    setEmail('');
    setAviso('vinculado');
    lista.recargar();
  };

  const pedirDesvincular = (operador) => {
    baja.limpiar();
    setAviso(null);
    setADesvincular(operador);
  };

  const cerrarDesvincular = () => {
    baja.limpiar();
    setADesvincular(null);
  };

  const confirmarDesvincular = async () => {
    if (!aDesvincular) return;
    const resultado = await baja.enviar(() => desvincularOperador(complejoId, aDesvincular.id));
    if (!resultado.ok) {
      // Si ya no estaba vinculado (404) la lista se actualiza para reflejar lo real.
      if (resultado.error.status === 404) lista.recargar();
      return;
    }
    setADesvincular(null);
    setAviso('desvinculado');
    lista.recargar();
  };

  return {
    lista,
    email,
    cambiarEmail,
    vincular,
    vinculando: alta.enviando,
    errorVincular: alta.error,
    aviso,
    descartarAviso: () => setAviso(null),
    aDesvincular,
    errorDesvincular: baja.error,
    pedirDesvincular,
    cerrarDesvincular,
    confirmarDesvincular,
  };
}
