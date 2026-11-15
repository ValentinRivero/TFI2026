/**
 * Genera el logo provisorio de TaLibre: una "T" geométrica blanca sobre el verde de marca, con un punto que alude
 * al turno libre. Es obra propia, sin fuentes ni imágenes de terceros.
 *
 * Uso: `npm run iconos`. Escribe en `public/icons/`:
 *   logo.svg, favicon.svg, icon-192.png, icon-512.png, icon-maskable-512.png y apple-touch-icon.png.
 *
 * Para reemplazar el logo por el definitivo alcanza con sobrescribir esos archivos (mismos nombres y tamaños);
 * nada más en la app depende de este script. Las medidas del dibujo están en `DISENO`, en una grilla de 100 x 100.
 */
import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { deflateSync } from 'node:zlib';

const CARPETA = join(dirname(fileURLToPath(import.meta.url)), '..', 'public', 'icons');

const VERDE = [0x15, 0x80, 0x3d];
const BLANCO = [0xff, 0xff, 0xff];

// Coordenadas sobre una grilla de 100 x 100. `radio` redondea las esquinas del fondo.
const DISENO = {
  radio: 22,
  barra: { x: 24, y: 28, ancho: 52, alto: 14 },
  tronco: { x: 43, y: 28, ancho: 14, alto: 46 },
  punto: { cx: 71, cy: 69, r: 7 },
};

const rectangulos = (d, escala = 1, desplazamiento = 0) => [d.barra, d.tronco].map((r) => ({
  x: r.x * escala + desplazamiento,
  y: r.y * escala + desplazamiento,
  ancho: r.ancho * escala,
  alto: r.alto * escala,
}));

// --- SVG -------------------------------------------------------------------------------------------------------
const colorCss = (c) => `#${c.map((v) => v.toString(16).padStart(2, '0')).join('')}`;

const svg = ({ redondeado = true } = {}) => `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" role="img" aria-label="TaLibre">
  <rect width="100" height="100"${redondeado ? ` rx="${DISENO.radio}"` : ''} fill="${colorCss(VERDE)}"/>
  <rect x="${DISENO.barra.x}" y="${DISENO.barra.y}" width="${DISENO.barra.ancho}" height="${DISENO.barra.alto}" fill="#fff"/>
  <rect x="${DISENO.tronco.x}" y="${DISENO.tronco.y}" width="${DISENO.tronco.ancho}" height="${DISENO.tronco.alto}" fill="#fff"/>
  <circle cx="${DISENO.punto.cx}" cy="${DISENO.punto.cy}" r="${DISENO.punto.r}" fill="#fff"/>
</svg>
`;

// --- PNG (rasterizado propio con suavizado por supermuestreo) ---------------------------------------------------
const SUPERMUESTRAS = 4;

const dentroDeRedondeado = (x, y, lado, radio) => {
  const cx = Math.min(Math.max(x, radio), lado - radio);
  const cy = Math.min(Math.max(y, radio), lado - radio);
  return (x - cx) ** 2 + (y - cy) ** 2 <= radio ** 2;
};

const rasterizar = (lado, { redondeado, escala, desplazamiento }) => {
  const unidad = lado / 100;
  const rects = rectangulos(DISENO, unidad * escala, desplazamiento * unidad);
  const punto = {
    cx: DISENO.punto.cx * unidad * escala + desplazamiento * unidad,
    cy: DISENO.punto.cy * unidad * escala + desplazamiento * unidad,
    r: DISENO.punto.r * unidad * escala,
  };
  const radioFondo = DISENO.radio * unidad;
  const pixeles = Buffer.alloc(lado * lado * 4);

  for (let py = 0; py < lado; py += 1) {
    for (let px = 0; px < lado; px += 1) {
      let fondo = 0;
      let figura = 0;
      for (let sy = 0; sy < SUPERMUESTRAS; sy += 1) {
        for (let sx = 0; sx < SUPERMUESTRAS; sx += 1) {
          const x = px + (sx + 0.5) / SUPERMUESTRAS;
          const y = py + (sy + 0.5) / SUPERMUESTRAS;
          if (!redondeado || dentroDeRedondeado(x, y, lado, radioFondo)) fondo += 1;
          const enRect = rects.some((r) => x >= r.x && x <= r.x + r.ancho && y >= r.y && y <= r.y + r.alto);
          if (enRect || (x - punto.cx) ** 2 + (y - punto.cy) ** 2 <= punto.r ** 2) figura += 1;
        }
      }
      const muestras = SUPERMUESTRAS ** 2;
      const cobertura = fondo / muestras;
      const mezcla = fondo === 0 ? 0 : figura / fondo;
      const desplazar = (py * lado + px) * 4;
      for (let canal = 0; canal < 3; canal += 1) {
        pixeles[desplazar + canal] = Math.round(VERDE[canal] * (1 - mezcla) + BLANCO[canal] * mezcla);
      }
      pixeles[desplazar + 3] = Math.round(cobertura * 255);
    }
  }
  return pixeles;
};

const TABLA_CRC = Array.from({ length: 256 }, (_, n) => {
  let c = n;
  for (let k = 0; k < 8; k += 1) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
  return c >>> 0;
});

const crc32 = (datos) => {
  let c = 0xffffffff;
  for (const byte of datos) c = TABLA_CRC[(c ^ byte) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
};

const fragmento = (tipo, datos) => {
  const cuerpo = Buffer.concat([Buffer.from(tipo, 'ascii'), datos]);
  const largo = Buffer.alloc(4);
  largo.writeUInt32BE(datos.length);
  const crc = Buffer.alloc(4);
  crc.writeUInt32BE(crc32(cuerpo));
  return Buffer.concat([largo, cuerpo, crc]);
};

const png = (lado, pixeles) => {
  const cabecera = Buffer.alloc(13);
  cabecera.writeUInt32BE(lado, 0);
  cabecera.writeUInt32BE(lado, 4);
  cabecera.set([8, 6, 0, 0, 0], 8); // 8 bits, RGBA, sin entrelazado
  const filas = Buffer.alloc((lado * 4 + 1) * lado);
  for (let y = 0; y < lado; y += 1) {
    filas[y * (lado * 4 + 1)] = 0;
    pixeles.copy(filas, y * (lado * 4 + 1) + 1, y * lado * 4, (y + 1) * lado * 4);
  }
  return Buffer.concat([
    Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
    fragmento('IHDR', cabecera),
    fragmento('IDAT', deflateSync(filas, { level: 9 })),
    fragmento('IEND', Buffer.alloc(0)),
  ]);
};

// El ícono "maskable" ocupa todo el lienzo y reduce la figura al 70 % para que el sistema pueda recortarlo.
const VARIANTES = [
  { archivo: 'icon-192.png', lado: 192, redondeado: true, escala: 1, desplazamiento: 0 },
  { archivo: 'icon-512.png', lado: 512, redondeado: true, escala: 1, desplazamiento: 0 },
  { archivo: 'icon-maskable-512.png', lado: 512, redondeado: false, escala: 0.7, desplazamiento: 15 },
  { archivo: 'apple-touch-icon.png', lado: 180, redondeado: false, escala: 1, desplazamiento: 0 },
];

mkdirSync(CARPETA, { recursive: true });
writeFileSync(join(CARPETA, 'logo.svg'), svg());
writeFileSync(join(CARPETA, 'favicon.svg'), svg());
for (const { archivo, lado, ...opciones } of VARIANTES) {
  writeFileSync(join(CARPETA, archivo), png(lado, rasterizar(lado, opciones)));
}
console.log(`Íconos generados en ${CARPETA}`);
