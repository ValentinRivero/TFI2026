import { useState } from 'react';
import { t } from '../i18n/index.js';
import { listarTodasLasCanchas } from '../services/canchaService.js';
import { crearExcepcion, darDeBajaExcepcion, listarExcepciones } from '../services/excepcionService.js';
import {
  cuerpoExcepcion,
  FILTROS_EXCEPCIONES_INICIALES,
  validarExcepcion,
  VALORES_EXCEPCION_INICIALES,
} from '../utils/excepciones.js';
import { aFechaIso } from '../utils/formatos.js';
import useConsulta from './useConsulta.js';
import useEnvio from './useEnvio.js';
import useListaPaginada from './useListaPaginada.js';

/**
 * Excepciones horarias del complejo activo: lista paginada con filtros, alta (día completo o franja, sobre todo el
 * complejo o una cancha) y baja lógica con confirmación. Las excepciones no se editan: se dan de baja y se cargan de
 * nuevo. Tras un alta, `avisoAlta` recuerda cómo se resuelven los turnos fijos que la excepción deja en espera.
 */
export default function useExcepciones(complejoId) {
  const [filtros, setFiltros] = useState(FILTROS_EXCEPCIONES_INICIALES);
  const lista = useListaPaginada(
    (pagina, signal) => listarExcepciones(complejoId, filtros, pagina, signal),
    [complejoId, filtros],
  );
  const canchas = useConsulta((signal) => listarTodasLasCanchas(complejoId, signal), [complejoId]);

  const [valores, setValores] = useState(VALORES_EXCEPCION_INICIALES);
  const [intentado, setIntentado] = useState(false);
  const [avisoAlta, setAvisoAlta] = useState(false);
  const [aBaja, setABaja] = useState(null);
  const [avisoBaja, setAvisoBaja] = useState(false);
  const alta = useEnvio();
  const baja = useEnvio();

  const hoy = aFechaIso(new Date());
  const erroresLocales = validarExcepcion(valores, hoy);
  const errores = { ...(intentado ? erroresLocales : {}), ...(alta.error?.campos ?? {}) };

  const cambiarFiltro = (campo, valor) => setFiltros((actuales) => ({ ...actuales, [campo]: valor }));

  const cambiarValor = (campo, valor) => {
    alta.limpiar();
    setAvisoAlta(false);
    setValores((actuales) => ({ ...actuales, [campo]: valor }));
  };

  const registrar = async (evento) => {
    evento.preventDefault();
    setIntentado(true);
    setAvisoBaja(false);
    if (Object.keys(erroresLocales).length > 0) return;
    const resultado = await alta.enviar(() => crearExcepcion(cuerpoExcepcion(complejoId, valores)));
    if (!resultado.ok) return;
    setValores(VALORES_EXCEPCION_INICIALES);
    setIntentado(false);
    setAvisoAlta(true);
    lista.recargar();
  };

  const pedirBaja = (excepcion) => {
    baja.limpiar();
    setAvisoAlta(false);
    setAvisoBaja(false);
    setABaja(excepcion);
  };

  const cerrarBaja = () => {
    baja.limpiar();
    setABaja(null);
  };

  const confirmarBaja = async () => {
    if (!aBaja) return;
    const resultado = await baja.enviar(() => darDeBajaExcepcion(aBaja.id));
    if (!resultado.ok) {
      if (resultado.error.status === 404) lista.recargar();
      return;
    }
    setABaja(null);
    setAvisoBaja(true);
    lista.recargar();
  };

  return {
    lista,
    canchas: canchas.datos ?? [],
    filtros,
    cambiarFiltro,
    limpiarFiltros: () => setFiltros(FILTROS_EXCEPCIONES_INICIALES),
    formulario: {
      valores,
      errores,
      error: alta.error,
      enviando: alta.enviando,
      hoy,
      cambiar: cambiarValor,
      enviar: registrar,
    },
    avisoAlta: avisoAlta ? t('excepciones.avisoAlta') : null,
    descartarAvisoAlta: () => setAvisoAlta(false),
    avisoBaja: avisoBaja ? t('excepciones.avisoBaja') : null,
    descartarAvisoBaja: () => setAvisoBaja(false),
    baja: { excepcion: aBaja, error: baja.error, pedir: pedirBaja, cerrar: cerrarBaja, confirmar: confirmarBaja },
  };
}
