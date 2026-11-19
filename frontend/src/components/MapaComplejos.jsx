import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { useEffect, useRef, useState } from 'react';
import { PARAMETROS } from '../config/parametros.js';
import { t } from '../i18n/index.js';
import { formatearPrecio } from '../utils/formatos.js';
import { esClicSimple, htmlAtribuciones, limitesDe, rutaDeComplejo } from '../utils/mapa.js';
import BotonCentrarMapa from './BotonCentrarMapa.jsx';
import ControlCapasMapa from './ControlCapasMapa.jsx';

const elemento = (etiqueta, clase, texto) => {
  const nodo = document.createElement(etiqueta);
  if (clase) nodo.className = clase;
  if (texto !== undefined) nodo.textContent = texto;
  return nodo;
};

/**
 * Ícono del marcador: el pin y una etiqueta con el nombre y el precio mínimo, que `tema.css` muestra siempre cuando el
 * mapa está lo bastante cerca (`.mapa-zoom-cercano`). Se arma con nodos del DOM y `textContent`: el nombre viene de la API.
 */
const iconoDe = (marcador) => {
  const raiz = elemento('span', 'marcador-complejo-raiz');
  const cuerpo = elemento('span', 'marcador-complejo-cuerpo');
  cuerpo.append(elemento('span', 'marcador-complejo-pin'));

  // El nombre ya está en el `title` del marcador: la etiqueta es solo visual.
  const etiqueta = elemento('span', 'marcador-complejo-etiqueta');
  etiqueta.setAttribute('aria-hidden', 'true');
  etiqueta.append(elemento('strong', 'marcador-complejo-nombre', marcador.nombre));
  if (marcador.precioDesde !== null) {
    const precio = t('mapa.desdePrecio', { precio: formatearPrecio(marcador.precioDesde) });
    etiqueta.append(elemento('span', 'marcador-complejo-precio num', precio));
  }

  raiz.append(cuerpo, etiqueta);
  return L.divIcon({
    className: 'marcador-complejo',
    html: raiz,
    iconSize: [44, 44],
    iconAnchor: [22, 42],
    popupAnchor: [0, -36],
  });
};

/**
 * Contenido del popup, con nodos del DOM y `textContent` (nunca HTML). El enlace tiene `href` real, así funciona el
 * clic con tecla modificadora o el botón del medio; un clic simple se resuelve con la navegación de la aplicación.
 */
const armarPopup = (marcador, alAbrir) => {
  const raiz = elemento('div', 'mapa-popup');
  raiz.append(elemento('strong', 'mapa-popup-nombre', marcador.nombre));

  const precio = elemento('p', 'mapa-popup-precio');
  if (marcador.precioDesde === null) {
    precio.append(elemento('span', 'mapa-popup-sin-precio', t('mapa.sinPrecio')));
  } else {
    precio.append(
      elemento('span', undefined, t('mapa.desde')),
      elemento('span', 'mapa-popup-importe num', formatearPrecio(marcador.precioDesde)),
      elemento('span', undefined, t('mapa.porTurno')),
    );
  }
  raiz.append(precio);

  const ruta = rutaDeComplejo(marcador.id);
  const enlace = elemento('a', 'mapa-popup-enlace', t('mapa.verTurnos'));
  enlace.href = ruta;
  enlace.addEventListener('click', (evento) => {
    if (!esClicSimple(evento)) return;
    evento.preventDefault();
    alAbrir(ruta);
  });
  raiz.append(enlace);
  return raiz;
};

const marcarActivo = (marcador, activo) => {
  marcador.getElement()?.classList.toggle('marcador-activo', activo);
  marcador.setZIndexOffset(activo ? 1000 : 0);
};

/**
 * Mapa de los complejos con Leaflet directo (sin `react-leaflet`, por licencia: ver PROJECT.md §16). Es un
 * envoltorio de React: una instancia por montaje, que se destruye al desmontar, una pila de teselas que cambia con la
 * capa elegida (`Mapa` o `Satélite`) y una capa de marcadores que se rehace cuando cambia la lista. Queda limitado a
 * Goya (`limites` y `zoomMinimo`). Se carga diferido (`React.lazy`) junto con el CSS de Leaflet.
 * `marcadores` sale de `armarMarcadores` y `alAbrir(ruta)` navega al detalle del complejo.
 */
export default function MapaComplejos({ marcadores, alAbrir }) {
  const contenedor = useRef(null);
  const mapa = useRef(null);
  const teselas = useRef(null);
  const capaMarcadores = useRef(null);
  const ultimoAlAbrir = useRef(alAbrir);
  const [capa, setCapa] = useState(PARAMETROS.mapa.capaInicial);

  useEffect(() => {
    ultimoAlAbrir.current = alAbrir;
  });

  useEffect(() => {
    const { centro, zoom, zoomMinimo, zoomMaximo, limites, viscosidadLimites, zoomEtiquetasVisibles } = PARAMETROS.mapa;
    const instancia = L.map(contenedor.current, {
      center: centro,
      zoom,
      minZoom: zoomMinimo,
      maxZoom: zoomMaximo,
      maxBounds: L.latLngBounds(limites),
      maxBoundsViscosity: viscosidadLimites,
      attributionControl: false,
    });
    L.control.attribution({ prefix: false }).addTo(instancia);
    teselas.current = L.layerGroup().addTo(instancia);
    capaMarcadores.current = L.layerGroup().addTo(instancia);
    mapa.current = instancia;

    // Las etiquetas permanentes dependen del zoom: se alterna una clase en el contenedor, sin volver a dibujar.
    const sincronizarEtiquetas = () => {
      contenedor.current?.classList.toggle('mapa-zoom-cercano', instancia.getZoom() >= zoomEtiquetasVisibles);
    };
    instancia.on('zoomend', sincronizarEtiquetas);
    sincronizarEtiquetas();

    return () => {
      instancia.off('zoomend', sincronizarEtiquetas);
      instancia.remove();
      mapa.current = null;
      teselas.current = null;
      capaMarcadores.current = null;
    };
  }, []);

  // Cambiar de capa reemplaza la pila de teselas; Leaflet ajusta solo la atribución según las capas presentes.
  useEffect(() => {
    const grupo = teselas.current;
    if (!grupo) return;
    const { zoomMaximo, capas } = PARAMETROS.mapa;
    const definicion = capas[capa];
    grupo.clearLayers();
    definicion.teselas.forEach((pila, indice) => {
      grupo.addLayer(L.tileLayer(pila.url, {
        maxZoom: zoomMaximo,
        maxNativeZoom: pila.zoomNativoMaximo,
        updateWhenZooming: false,
        attribution: indice === 0 ? htmlAtribuciones(definicion.atribuciones) : '',
      }));
    });
  }, [capa]);

  useEffect(() => {
    const instancia = mapa.current;
    const grupo = capaMarcadores.current;
    if (!instancia || !grupo) return;

    grupo.clearLayers();
    marcadores.forEach((marcador) => {
      const puntero = L.marker(marcador.posicion, { icon: iconoDe(marcador), title: marcador.nombre })
        .bindPopup(
          () => armarPopup(marcador, (ruta) => ultimoAlAbrir.current(ruta)),
          { minWidth: PARAMETROS.mapa.anchoPopupPx, maxWidth: PARAMETROS.mapa.anchoPopupPx },
        )
        .on('popupopen', () => marcarActivo(puntero, true))
        .on('popupclose', () => marcarActivo(puntero, false));
      puntero.addTo(grupo);
    });

    const limites = limitesDe(marcadores);
    if (limites) {
      instancia.fitBounds(limites, {
        padding: [PARAMETROS.mapa.margenAjustePx, PARAMETROS.mapa.margenAjustePx],
        maxZoom: PARAMETROS.mapa.zoomAjusteMaximo,
      });
    }
  }, [marcadores]);

  const centrarEnLaCiudad = () => {
    mapa.current?.closePopup();
    mapa.current?.setView(PARAMETROS.mapa.centro, PARAMETROS.mapa.zoom);
  };

  return (
    <div className={`mapa-contenedor mapa-capa-${capa}`}>
      <div ref={contenedor} className="mapa-complejos" role="region" aria-label={t('mapa.descripcion')} />
      <ControlCapasMapa capas={PARAMETROS.mapa.capas} activa={capa} onCambiar={setCapa} />
      <BotonCentrarMapa onClick={centrarEnLaCiudad} />
    </div>
  );
}
