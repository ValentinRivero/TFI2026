/**
 * Funciones puras del mapa de complejos: validación de los marcadores que llegan del backend, encuadre de la vista y
 * armado de la atribución. Leaflet y el DOM quedan en `MapaComplejos.jsx`.
 */
import { PARAMETROS } from '../config/parametros.js';

const dentroDe = ([sudoeste, noreste], latitud, longitud) => (
  latitud >= sudoeste[0] && latitud <= noreste[0] && longitud >= sudoeste[1] && longitud <= noreste[1]
);

const coordenada = (valor, maximo) => {
  if (valor === null || valor === undefined || valor === '') return null;
  const numero = Number(valor);
  return Number.isFinite(numero) && Math.abs(numero) <= maximo ? numero : null;
};

/**
 * Marcadores dibujables a partir de la respuesta de `GET /api/complejos/marcadores/`. Un complejo sin coordenadas
 * válidas, o fuera del área de Goya a la que se limita el mapa (no se podría alcanzar), se descarta en lugar de romper
 * la vista; las coordenadas llegan como texto decimal y se pasan a número.
 */
export const armarMarcadores = (lista) => (Array.isArray(lista) ? lista : []).flatMap((item) => {
  const latitud = coordenada(item?.latitud, PARAMETROS.panel.latitudMaxima);
  const longitud = coordenada(item?.longitud, PARAMETROS.panel.longitudMaxima);
  if (latitud === null || longitud === null || item.id === undefined || item.id === null) return [];
  if (!dentroDe(PARAMETROS.mapa.limites, latitud, longitud)) return [];
  return [{
    id: item.id,
    nombre: String(item.nombre ?? ''),
    posicion: [latitud, longitud],
    precioDesde: item.precio_desde ?? null,
  }];
});

/** Esquinas `[[sur, oeste], [norte, este]]` que contienen todos los marcadores, o `null` si no hay ninguno. */
export const limitesDe = (marcadores) => {
  if (marcadores.length === 0) return null;
  const latitudes = marcadores.map(({ posicion }) => posicion[0]);
  const longitudes = marcadores.map(({ posicion }) => posicion[1]);
  return [
    [Math.min(...latitudes), Math.min(...longitudes)],
    [Math.max(...latitudes), Math.max(...longitudes)],
  ];
};

const escaparAtributo = (texto) => String(texto)
  .replaceAll('&', '&amp;')
  .replaceAll('"', '&quot;')
  .replaceAll('<', '&lt;')
  .replaceAll('>', '&gt;');

/**
 * HTML de la atribución de un proveedor de teselas: el texto visible enlaza a sus condiciones de uso y la licencia
 * queda en el `title`, igual que la del clima. Solo usa constantes de `parametros.js`, con los atributos escapados.
 */
export const htmlAtribucion = ({ texto, url, licencia }) => (
  `<a href="${escaparAtributo(url)}" target="_blank" rel="noopener noreferrer" title="${escaparAtributo(licencia)}">${escaparAtributo(texto)}</a>`
);

/** Atribuciones de una capa del mapa, una junto a otra. */
export const htmlAtribuciones = (atribuciones) => atribuciones.map(htmlAtribucion).join(' | ');

/** Ruta interna del detalle de un complejo. */
export const rutaDeComplejo = (id) => `/complejos/${encodeURIComponent(id)}`;

/** Clic "común" de un enlace: botón principal y sin teclas modificadoras; el resto lo resuelve el navegador. */
export const esClicSimple = (evento) => (
  evento.button === 0 && !evento.metaKey && !evento.ctrlKey && !evento.shiftKey && !evento.altKey
);
