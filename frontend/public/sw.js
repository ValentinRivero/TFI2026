/*
 * Service worker de TaLibre, escrito a mano y sin librerías.
 *
 * Qué guarda: la cáscara de la aplicación (index.html, manifiesto e íconos) y los recursos estáticos propios
 * (/assets/ con hash en el nombre, /fonts/ e /icons/). Nada más.
 *
 * Qué no toca nunca: /api/, /ws/, peticiones que no sean GET, peticiones con Authorization y cualquier origen
 * distinto del propio (teselas de OpenStreetMap, Open-Meteo, backend-node). Así ninguna respuesta autenticada ni
 * dato personal llega a Cache Storage: las peticiones que no se resuelven acá siguen su camino normal por la red.
 *
 * Al cambiar la estrategia o el contenido de la cáscara se incrementa VERSION: en `activate` se borran los cachés
 * de las versiones anteriores.
 */
const VERSION = 'v1';
const PREFIJO = 'talibre-';
const CACHE_CASCARA = `${PREFIJO}cascara-${VERSION}`;
const CACHE_ESTATICOS = `${PREFIJO}estaticos-${VERSION}`;
const CACHES_VIGENTES = [CACHE_CASCARA, CACHE_ESTATICOS];

const CASCARA = [
  '/',
  '/index.html',
  '/manifest.json',
  '/icons/favicon.svg',
  '/icons/logo.svg',
  '/icons/icon-192.png',
  '/icons/icon-512.png',
  '/icons/apple-touch-icon.png',
];

const RUTAS_EXCLUIDAS = /^\/(api|ws)(\/|$)/;
const RECURSOS_CON_HASH = /^\/assets\//;
const RECURSOS_PUBLICOS = /^\/(icons|fonts)\/|^\/manifest\.json$/;
const ENLACES_A_RECURSOS = /(?:src|href)="(\/assets\/[^"]+)"/g;

const respuestaGuardable = (respuesta) => (
  respuesta.status === 200
  && respuesta.type === 'basic'
  && !(respuesta.headers.get('content-type') ?? '').includes('text/html')
);

const recursosDelHtml = (html) => [...html.matchAll(ENLACES_A_RECURSOS)].map((coincidencia) => coincidencia[1]);

const guardarRecursos = async (rutas) => {
  const cache = await caches.open(CACHE_ESTATICOS);
  await Promise.all(rutas.map(async (ruta) => {
    if (await cache.match(ruta)) return;
    try {
      const respuesta = await fetch(ruta);
      if (respuestaGuardable(respuesta)) await cache.put(ruta, respuesta);
    } catch {
      // Sin red en este momento: el recurso se guardará la primera vez que la página lo pida.
    }
  }));
};

// El HTML de la aplicación se identifica por su raíz de React: cualquier otra página HTML del mismo origen no se guarda.
const esCascaraDeLaAplicacion = (html) => html.includes('id="raiz"');

const instalar = async () => {
  const cascara = await caches.open(CACHE_CASCARA);
  await cascara.addAll(CASCARA.map((ruta) => new Request(ruta, { cache: 'reload' })));
  const index = await cascara.match('/index.html');
  await guardarRecursos(recursosDelHtml(await index.text()));
};

const actualizarCascara = async (respuesta) => {
  if (!respuesta.ok || !(respuesta.headers.get('content-type') ?? '').includes('text/html')) return;
  const html = await respuesta.text();
  if (!esCascaraDeLaAplicacion(html)) return;
  const cascara = await caches.open(CACHE_CASCARA);
  await cascara.put('/index.html', new Response(html, { headers: { 'Content-Type': 'text/html; charset=utf-8' } }));
  await guardarRecursos(recursosDelHtml(html));
};

// Navegación: red primero y, sin conexión, la cáscara guardada (la aplicación resuelve las rutas en el cliente).
const responderNavegacion = async (evento) => {
  try {
    const respuesta = await fetch(evento.request);
    evento.waitUntil(actualizarCascara(respuesta.clone()));
    return respuesta;
  } catch {
    const cascara = await caches.open(CACHE_CASCARA);
    return (await cascara.match('/index.html')) ?? Response.error();
  }
};

// Recursos con hash: nunca cambian bajo el mismo nombre, así que primero el caché.
const responderConHash = async (pedido) => {
  const cache = await caches.open(CACHE_ESTATICOS);
  const guardada = await cache.match(pedido);
  if (guardada) return guardada;
  const respuesta = await fetch(pedido);
  if (respuestaGuardable(respuesta)) await cache.put(pedido, respuesta.clone());
  return respuesta;
};

// Íconos, fuentes y manifiesto conservan el nombre aunque cambien: se sirve lo guardado y se renueva en segundo plano.
const responderYRenovar = async (evento) => {
  const cache = await caches.open(CACHE_ESTATICOS);
  const guardada = await cache.match(evento.request);
  const renovada = fetch(evento.request)
    .then(async (respuesta) => {
      if (respuestaGuardable(respuesta)) await cache.put(evento.request, respuesta.clone());
      return respuesta;
    })
    .catch(() => null);
  if (guardada) {
    evento.waitUntil(renovada);
    return guardada;
  }
  return (await renovada) ?? Response.error();
};

const limpiarVersionesAnteriores = async () => {
  const nombres = await caches.keys();
  await Promise.all(
    nombres
      .filter((nombre) => nombre.startsWith(PREFIJO) && !CACHES_VIGENTES.includes(nombre))
      .map((nombre) => caches.delete(nombre)),
  );
  await self.clients.claim();
};

self.addEventListener('install', (evento) => {
  evento.waitUntil(instalar().then(() => self.skipWaiting()));
});

self.addEventListener('activate', (evento) => {
  evento.waitUntil(limpiarVersionesAnteriores());
});

self.addEventListener('fetch', (evento) => {
  const { request: pedido } = evento;
  if (pedido.method !== 'GET') return;
  if (pedido.headers.has('authorization') || pedido.headers.has('range')) return;

  const url = new URL(pedido.url);
  if (url.origin !== self.location.origin) return;
  if (RUTAS_EXCLUIDAS.test(url.pathname)) return;

  if (pedido.mode === 'navigate') {
    evento.respondWith(responderNavegacion(evento));
  } else if (RECURSOS_CON_HASH.test(url.pathname)) {
    evento.respondWith(responderConHash(pedido));
  } else if (RECURSOS_PUBLICOS.test(url.pathname)) {
    evento.respondWith(responderYRenovar(evento));
  }
});
