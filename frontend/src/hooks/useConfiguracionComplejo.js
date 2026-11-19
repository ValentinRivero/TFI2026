import { useState } from 'react';
import { actualizarConfiguracion } from '../services/complejoAdminService.js';
import { cuerpoConfiguracion, validarConfiguracion, valoresDeComplejo } from '../utils/complejo.js';
import useEnvio from './useEnvio.js';

/**
 * Edición del perfil comercial del complejo. Los valores se reinician cuando cambia el complejo activo o su versión
 * guardada. Solo se envían los campos que cambiaron; los errores por campo combinan la validación local (tras el
 * primer intento de envío) con los del servidor. `alGuardar` recibe el complejo ya actualizado.
 */
export default function useConfiguracionComplejo(complejo, { alGuardar }) {
  const [valores, setValores] = useState(() => valoresDeComplejo(complejo));
  const [origen, setOrigen] = useState({ id: complejo.id, version: complejo.fecha_modificacion });
  const [intentado, setIntentado] = useState(false);
  const envio = useEnvio();

  if (origen.id !== complejo.id || origen.version !== complejo.fecha_modificacion) {
    setOrigen({ id: complejo.id, version: complejo.fecha_modificacion });
    setValores(valoresDeComplejo(complejo));
    setIntentado(false);
  }

  const cuerpo = cuerpoConfiguracion(valores, complejo);
  const erroresLocales = validarConfiguracion(valores);
  const errores = { ...(intentado ? erroresLocales : {}), ...(envio.error?.campos ?? {}) };

  const cambiar = (campo, valor) => {
    envio.limpiar();
    setValores((actuales) => ({ ...actuales, [campo]: valor }));
  };

  const descartar = () => {
    envio.limpiar();
    setIntentado(false);
    setValores(valoresDeComplejo(complejo));
  };

  const enviar = async (evento) => {
    evento.preventDefault();
    setIntentado(true);
    if (Object.keys(erroresLocales).length > 0 || Object.keys(cuerpo).length === 0) return;
    const resultado = await envio.enviar(() => actualizarConfiguracion(complejo.id, cuerpo));
    if (resultado.ok) {
      setIntentado(false);
      alGuardar(resultado.resultado);
    }
  };

  return {
    valores,
    errores,
    cambiar,
    descartar,
    enviar,
    enviando: envio.enviando,
    error: envio.error,
    guardado: envio.exito,
    hayCambios: Object.keys(cuerpo).length > 0,
  };
}
