import { useCallback, useMemo, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import Alerta from '../components/Alerta.jsx';
import BannerParaComplejos from '../components/BannerParaComplejos.jsx';
import ClimaCard from '../components/ClimaCard.jsx';
import FiltrosCatalogo from '../components/FiltrosCatalogo.jsx';
import HeroPresentacion from '../components/HeroPresentacion.jsx';
import ListaComplejos from '../components/ListaComplejos.jsx';
import PasosComoFunciona from '../components/PasosComoFunciona.jsx';
import SelectorVistaCatalogo from '../components/SelectorVistaCatalogo.jsx';
import VistaMapa from '../components/VistaMapa.jsx';
import { puedeVer, VISTA_MAPA } from '../config/catalogos.js';
import useAvisoDeNavegacion from '../hooks/useAvisoDeNavegacion.js';
import useClima from '../hooks/useClima.js';
import useConsulta from '../hooks/useConsulta.js';
import useListaIncremental from '../hooks/useListaIncremental.js';
import useSesion from '../hooks/useSesion.js';
import { listarComplejos, listarDeportes, listarMarcadores, listarServicios } from '../services/complejoService.js';
import { desplazarA } from '../utils/desplazamiento.js';
import {
  aParametros, conVista, FILTROS_VACIOS, hayFiltros, leerFiltros, leerVista, mostrarGuiaDeUso,
} from '../utils/filtrosCatalogo.js';

const LISTA_VACIA = Object.freeze([]);

/**
 * Portada pública: presentación del servicio y buscador de complejos, sin necesidad de cuenta. Los filtros viven en la URL (enlace compartible) y cada cambio
 * reemplaza la entrada del historial, así "Atrás" vuelve a la pantalla anterior y no filtro por filtro. La vista
 * (lista o mapa) también vive en la URL y comparte los mismos filtros; los puntos del mapa solo se piden en esa vista.
 */
export default function Catalogo() {
  const { aviso, descartar: descartarAviso } = useAvisoDeNavegacion();
  const { autenticado, rol } = useSesion();
  const bloqueResultados = useRef(null);
  const navegar = useNavigate();
  const [parametros, setParametros] = useSearchParams();
  const consulta = parametros.toString();
  const filtros = useMemo(() => leerFiltros(new URLSearchParams(consulta)), [consulta]);
  const vista = leerVista(parametros);
  const enMapa = vista === VISTA_MAPA;

  // Los catálogos de filtros son opcionales: si fallan, el catálogo sigue funcionando sin esos controles.
  const deportes = useConsulta((signal) => listarDeportes(signal), []);
  const servicios = useConsulta((signal) => listarServicios(signal), []);

  const lista = useListaIncremental(
    (pagina, signal) => listarComplejos(filtros, pagina, signal),
    [aParametros(filtros).toString()],
  );

  const marcadores = useConsulta(
    (signal) => (enMapa ? listarMarcadores(filtros, signal) : Promise.resolve(null)),
    [aParametros(filtros).toString(), enMapa],
  );

  // El clima general de Goya se toma del primer complejo que carga el catálogo y no cambia con los filtros.
  const [referencia, setReferencia] = useState(null);
  if (referencia === null && lista.items.length > 0) setReferencia(lista.items[0].id);
  const clima = useClima(referencia);

  // Cada cambio parte de lo que hay en la URL en ese momento, así dos cambios seguidos no se pisan.
  const cambiarFiltros = useCallback((cambios) => {
    setParametros(
      (actuales) => conVista(aParametros({ ...leerFiltros(actuales), ...cambios }), leerVista(actuales)),
      { replace: true },
    );
  }, [setParametros]);

  const limpiarFiltros = useCallback(() => {
    setParametros((actuales) => conVista(aParametros(FILTROS_VACIOS), leerVista(actuales)), { replace: true });
  }, [setParametros]);

  const cambiarVista = useCallback((nueva) => {
    setParametros((actuales) => conVista(aParametros(leerFiltros(actuales)), nueva), { replace: true });
  }, [setParametros]);

  const irAResultados = useCallback(() => desplazarA(bloqueResultados.current), []);

  const abrirMapa = useCallback(() => {
    cambiarVista(VISTA_MAPA);
    irAResultados();
  }, [cambiarVista, irAResultados]);

  const esperandoReferencia = referencia === null && lista.cargando;

  return (
    <div>
      {aviso && <Alerta variante="success" onCerrar={descartarAviso}>{aviso}</Alerta>}
      <HeroPresentacion onExplorar={irAResultados} onAbrirMapa={abrirMapa}>
        <ClimaCard
          {...clima}
          cargando={clima.cargando || esperandoReferencia}
          recargar={referencia === null ? lista.recargar : clima.recargar}
          variante="compacto"
        />
      </HeroPresentacion>

      {mostrarGuiaDeUso(filtros, vista) && <PasosComoFunciona />}

      <div ref={bloqueResultados} id="resultados-catalogo" className="bloque-resultados" tabIndex={-1}>
        <FiltrosCatalogo
          filtros={filtros}
          deportes={deportes.datos ?? LISTA_VACIA}
          servicios={servicios.datos ?? LISTA_VACIA}
          onCambiar={cambiarFiltros}
          onLimpiar={limpiarFiltros}
        />

        <SelectorVistaCatalogo vista={vista} onCambiar={cambiarVista} />

        {enMapa ? (
          <VistaMapa
            consulta={marcadores}
            hayFiltros={hayFiltros(filtros)}
            onLimpiar={limpiarFiltros}
            onAbrirComplejo={navegar}
          />
        ) : (
          <ListaComplejos lista={lista} hayFiltros={hayFiltros(filtros)} onLimpiar={limpiarFiltros} />
        )}
      </div>

      <BannerParaComplejos tienePanel={autenticado && puedeVer('panel', rol)} />
    </div>
  );
}
