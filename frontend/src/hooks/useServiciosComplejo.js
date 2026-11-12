import { useState } from 'react';
import { sincronizarServicios } from '../services/complejoAdminService.js';
import { listarServicios } from '../services/complejoService.js';
import { serviciosModificados } from '../utils/complejo.js';
import useConsulta from './useConsulta.js';
import useEnvio from './useEnvio.js';

const idsDe = (complejo) => complejo.servicios.map((servicio) => servicio.id);

/**
 * Servicios que ofrece el complejo: catálogo completo, selección en edición y guardado. La selección se reinicia
 * cuando cambia el complejo activo o su versión guardada. `alGuardar` recibe la lista nueva `[{ id, nombre }]`.
 */
export default function useServiciosComplejo(complejo, { alGuardar }) {
  const catalogo = useConsulta((signal) => listarServicios(signal), []);
  const [elegidos, setElegidos] = useState(() => idsDe(complejo));
  const [origen, setOrigen] = useState({ id: complejo.id, version: complejo.fecha_modificacion });
  const envio = useEnvio();

  if (origen.id !== complejo.id || origen.version !== complejo.fecha_modificacion) {
    setOrigen({ id: complejo.id, version: complejo.fecha_modificacion });
    setElegidos(idsDe(complejo));
  }

  const alternar = (id) => {
    envio.limpiar();
    setElegidos((actuales) => (actuales.includes(id) ? actuales.filter((otro) => otro !== id) : [...actuales, id]));
  };

  const guardar = async () => {
    const resultado = await envio.enviar(() => sincronizarServicios(complejo.id, elegidos));
    if (resultado.ok) alGuardar(resultado.resultado.servicios);
  };

  return {
    catalogo: catalogo.datos ?? [],
    cargando: catalogo.cargando && !catalogo.datos,
    errorCatalogo: catalogo.error,
    recargarCatalogo: catalogo.recargar,
    elegidos,
    alternar,
    guardar,
    enviando: envio.enviando,
    error: envio.error,
    guardado: envio.exito,
    hayCambios: serviciosModificados(idsDe(complejo), elegidos),
  };
}
