import { useCallback, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import Alerta from '../components/Alerta.jsx';
import ClimaCard from '../components/ClimaCard.jsx';
import EncabezadoCatalogo from '../components/EncabezadoCatalogo.jsx';
import FiltrosCatalogo from '../components/FiltrosCatalogo.jsx';
import ListaComplejos from '../components/ListaComplejos.jsx';
import useAvisoDeNavegacion from '../hooks/useAvisoDeNavegacion.js';
import useClima from '../hooks/useClima.js';
import useConsulta from '../hooks/useConsulta.js';
import useListaIncremental from '../hooks/useListaIncremental.js';
import { listarComplejos, listarDeportes, listarServicios } from '../services/complejoService.js';
import { aParametros, FILTROS_VACIOS, hayFiltros, leerFiltros } from '../utils/filtrosCatalogo.js';

const LISTA_VACIA = Object.freeze([]);

/**
 * Portada pública: explora los complejos sin cuenta. Los filtros viven en la URL (enlace compartible) y cada cambio
 * reemplaza la entrada del historial, así "Atrás" vuelve a la pantalla anterior y no filtro por filtro.
 */
export default function Catalogo() {
  const { aviso, descartar: descartarAviso } = useAvisoDeNavegacion();
  const [parametros, setParametros] = useSearchParams();
  const consulta = parametros.toString();
  const filtros = useMemo(() => leerFiltros(new URLSearchParams(consulta)), [consulta]);

  // Los catálogos de filtros son opcionales: si fallan, el catálogo sigue funcionando sin esos controles.
  const deportes = useConsulta((signal) => listarDeportes(signal), []);
  const servicios = useConsulta((signal) => listarServicios(signal), []);

  const lista = useListaIncremental(
    (pagina, signal) => listarComplejos(filtros, pagina, signal),
    [aParametros(filtros).toString()],
  );

  // El clima general de Goya se toma del primer complejo que carga el catálogo y no cambia con los filtros.
  const [referencia, setReferencia] = useState(null);
  if (referencia === null && lista.items.length > 0) setReferencia(lista.items[0].id);
  const clima = useClima(referencia);

  // Cada cambio parte de lo que hay en la URL en ese momento, así dos cambios seguidos no se pisan.
  const cambiarFiltros = useCallback((cambios) => {
    setParametros((actuales) => aParametros({ ...leerFiltros(actuales), ...cambios }), { replace: true });
  }, [setParametros]);

  const limpiarFiltros = useCallback(() => {
    setParametros(aParametros(FILTROS_VACIOS), { replace: true });
  }, [setParametros]);

  const esperandoReferencia = referencia === null && lista.cargando;

  return (
    <div>
      {aviso && <Alerta variante="success" onCerrar={descartarAviso}>{aviso}</Alerta>}
      <EncabezadoCatalogo>
        <ClimaCard
          {...clima}
          cargando={clima.cargando || esperandoReferencia}
          recargar={referencia === null ? lista.recargar : clima.recargar}
          variante="compacto"
        />
      </EncabezadoCatalogo>

      <FiltrosCatalogo
        filtros={filtros}
        deportes={deportes.datos ?? LISTA_VACIA}
        servicios={servicios.datos ?? LISTA_VACIA}
        onCambiar={cambiarFiltros}
        onLimpiar={limpiarFiltros}
      />

      <ListaComplejos lista={lista} hayFiltros={hayFiltros(filtros)} onLimpiar={limpiarFiltros} />
    </div>
  );
}
