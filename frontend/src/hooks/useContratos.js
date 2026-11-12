import { useState } from 'react';
import { t } from '../i18n/index.js';
import { buscarDuenos } from '../services/usuarioService.js';
import { cambiarEstadoContrato, crearComplejoConContrato, listarContratos } from '../services/contratoService.js';
import {
  cuerpoComplejoNuevo,
  FILTROS_CONTRATOS_INICIALES,
  validarComplejoNuevo,
  VALORES_COMPLEJO_NUEVO_INICIALES,
} from '../utils/sistema.js';
import useConsulta from './useConsulta.js';
import useEnvio from './useEnvio.js';
import useFiltrosAplicables from './useFiltrosAplicables.js';
import useListaPaginada from './useListaPaginada.js';
import useValorConDemora from './useValorConDemora.js';

const MINIMO_BUSQUEDA_DUENO = 2;

/**
 * Contratos de los complejos (superadmin): lista paginada con filtros, alta de un complejo con su contrato y su
 * propietario, y cambio de estado del contrato. Activar un contrato exige un dueño activo: si no, el backend lo
 * rechaza con el motivo y el mensaje se muestra dentro del diálogo.
 */
export default function useContratos() {
  const filtros = useFiltrosAplicables(FILTROS_CONTRATOS_INICIALES);
  const lista = useListaPaginada(
    (pagina, signal) => listarContratos(filtros.aplicados, pagina, signal),
    [filtros.aplicados],
  );

  const [aviso, setAviso] = useState(null);

  const [altaAbierta, setAltaAbierta] = useState(false);
  const [valores, setValores] = useState(VALORES_COMPLEJO_NUEVO_INICIALES);
  const [intentado, setIntentado] = useState(false);
  const [busquedaDueno, setBusquedaDueno] = useState('');
  const alta = useEnvio();
  const erroresLocales = validarComplejoNuevo(valores);
  const errores = { ...(intentado ? erroresLocales : {}), ...(alta.error?.campos ?? {}) };

  const textoDueno = useValorConDemora(busquedaDueno.trim());
  const duenos = useConsulta(
    (signal) => (altaAbierta && textoDueno.length >= MINIMO_BUSQUEDA_DUENO ? buscarDuenos(textoDueno, signal) : []),
    [altaAbierta, textoDueno],
  );

  const abrirAlta = () => {
    alta.limpiar();
    setIntentado(false);
    setBusquedaDueno('');
    setValores(VALORES_COMPLEJO_NUEVO_INICIALES);
    setAltaAbierta(true);
  };

  const cerrarAlta = () => {
    alta.limpiar();
    setAltaAbierta(false);
  };

  const cambiarValor = (campo, valor) => {
    alta.limpiar();
    setValores((actuales) => ({ ...actuales, [campo]: valor }));
  };

  const registrar = async (evento) => {
    evento.preventDefault();
    setIntentado(true);
    if (Object.keys(erroresLocales).length > 0) return;
    const resultado = await alta.enviar(() => crearComplejoConContrato(cuerpoComplejoNuevo(valores)));
    if (!resultado.ok) return;
    setAltaAbierta(false);
    setAviso(t('contratos.avisoAlta'));
    lista.recargar();
  };

  const [edicion, setEdicion] = useState({ contrato: null, estado: '' });
  const cambio = useEnvio();

  const pedirCambio = (contrato) => {
    cambio.limpiar();
    setAviso(null);
    setEdicion({ contrato, estado: String(contrato.estado_contrato) });
  };

  const cerrarCambio = () => {
    cambio.limpiar();
    setEdicion({ contrato: null, estado: '' });
  };

  const guardarCambio = async () => {
    const { contrato, estado } = edicion;
    if (Number(estado) === contrato.estado_contrato) {
      cerrarCambio();
      return;
    }
    const resultado = await cambio.enviar(() => cambiarEstadoContrato(contrato.id, Number(estado)));
    if (!resultado.ok) {
      if (resultado.error.status === 404) lista.recargar();
      return;
    }
    cerrarCambio();
    setAviso(t('contratos.avisoEstado'));
    lista.recargar();
  };

  return {
    lista,
    filtros,
    aviso,
    descartarAviso: () => setAviso(null),
    alta: {
      abierta: altaAbierta,
      valores,
      errores,
      error: alta.error,
      enviando: alta.enviando,
      busquedaDueno,
      duenos: { items: duenos.datos ?? [], cargando: duenos.cargando, error: duenos.error, minimo: MINIMO_BUSQUEDA_DUENO },
      buscarDueno: setBusquedaDueno,
      abrir: abrirAlta,
      cerrar: cerrarAlta,
      cambiar: cambiarValor,
      enviar: registrar,
    },
    cambio: {
      ...edicion,
      error: cambio.error,
      enviando: cambio.enviando,
      pedir: pedirCambio,
      cerrar: cerrarCambio,
      cambiarEstado: (estado) => {
        cambio.limpiar();
        setEdicion((actual) => ({ ...actual, estado }));
      },
      guardar: guardarCambio,
    },
  };
}
