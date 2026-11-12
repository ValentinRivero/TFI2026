import { LIMITES, leerParametros, obtenerParametros } from '../config/parametros.js';

const POR_DEFECTO = {
  puerto: 3000,
  numProxies: 0,
  limitadores: {
    global: { ventanaMs: 60_000, maximo: 120 },
    actividad: { ventanaMs: 60_000, maximo: 30 },
    interno: { ventanaMs: 60_000, maximo: 600 },
  },
  clima: { url: 'https://api.open-meteo.com/v1/forecast', ttlMs: 900_000, cacheMaximo: 500 },
  http: { timeoutDjangoMs: 5_000, timeoutClimaMs: 5_000 },
  bodyMaximoBytes: 10_240,
  mongo: { timeoutSeleccionMs: 10_000, maxPoolSize: 100 },
  rangoMaximoDias: 366,
};

describe('Valores por defecto', () => {
  test('sin variables de entorno rigen los valores de producción', () => {
    expect(leerParametros({})).toEqual(POR_DEFECTO);
  });

  test('una variable vacía o con espacios usa el valor por defecto', () => {
    expect(leerParametros({ PORT: '', RATE_LIMIT_MAXIMO: '   ', CLIMA_URL: '' })).toEqual(POR_DEFECTO);
  });

  test('el resultado no se puede modificar', () => {
    const parametros = leerParametros({});

    expect(Object.isFrozen(parametros)).toBe(true);
    expect(Object.isFrozen(parametros.limitadores)).toBe(true);
    expect(Object.isFrozen(parametros.limitadores.global)).toBe(true);
    expect(Object.isFrozen(parametros.clima)).toBe(true);
    expect(Object.isFrozen(parametros.mongo)).toBe(true);
  });

  test('las reglas fijas del servicio no dependen del entorno', () => {
    expect(LIMITES).toEqual({
      paginacion: { tamanoDePagina: 20, maximoPorPagina: 50 },
      diasDePronostico: 3,
      maximoMensaje: 280,
      maximoBytesMetadata: 2048,
      largoMinimoClaveInterna: 32,
    });
    expect(Object.isFrozen(LIMITES)).toBe(true);
    expect(Object.isFrozen(LIMITES.paginacion)).toBe(true);
  });
});

describe('Lectura del entorno', () => {
  test.each([
    ['PORT', '8080', (p) => p.puerto, 8080],
    ['NUM_PROXIES', '1', (p) => p.numProxies, 1],
    ['RATE_LIMIT_VENTANA_MS', '30000', (p) => p.limitadores.global.ventanaMs, 30_000],
    ['RATE_LIMIT_MAXIMO', '500', (p) => p.limitadores.global.maximo, 500],
    ['RATE_LIMIT_ACTIVIDAD_VENTANA_MS', '10000', (p) => p.limitadores.actividad.ventanaMs, 10_000],
    ['RATE_LIMIT_ACTIVIDAD_MAXIMO', '5', (p) => p.limitadores.actividad.maximo, 5],
    ['RATE_LIMIT_INTERNO_VENTANA_MS', '120000', (p) => p.limitadores.interno.ventanaMs, 120_000],
    ['RATE_LIMIT_INTERNO_MAXIMO', '900', (p) => p.limitadores.interno.maximo, 900],
    ['CLIMA_TTL_MS', '60000', (p) => p.clima.ttlMs, 60_000],
    ['CLIMA_CACHE_MAXIMO', '50', (p) => p.clima.cacheMaximo, 50],
    ['HTTP_TIMEOUT_DJANGO_MS', '2500', (p) => p.http.timeoutDjangoMs, 2_500],
    ['HTTP_TIMEOUT_CLIMA_MS', '8000', (p) => p.http.timeoutClimaMs, 8_000],
    ['BODY_MAXIMO_BYTES', '2048', (p) => p.bodyMaximoBytes, 2_048],
    ['MONGO_TIMEOUT_SELECCION_MS', '5000', (p) => p.mongo.timeoutSeleccionMs, 5_000],
    ['MONGO_MAX_POOL', '20', (p) => p.mongo.maxPoolSize, 20],
    ['RANGO_MAXIMO_DIAS', '90', (p) => p.rangoMaximoDias, 90],
  ])('%s=%s se aplica', (variable, valor, leer, esperado) => {
    expect(leer(leerParametros({ [variable]: valor }))).toBe(esperado);
  });

  test('una variable no altera a las demás', () => {
    const parametros = leerParametros({ RATE_LIMIT_MAXIMO: '500' });

    expect(parametros.limitadores.actividad).toEqual(POR_DEFECTO.limitadores.actividad);
    expect(parametros.limitadores.interno).toEqual(POR_DEFECTO.limitadores.interno);
    expect(parametros.puerto).toBe(3000);
  });

  test('tolera espacios alrededor del número', () => {
    expect(leerParametros({ PORT: ' 8080 ' }).puerto).toBe(8080);
  });

  test('acepta una dirección propia para el proveedor del clima', () => {
    const parametros = leerParametros({ CLIMA_URL: 'http://clima-interno:9000/v1/forecast' });

    expect(parametros.clima.url).toBe('http://clima-interno:9000/v1/forecast');
  });

  test('obtenerParametros lee el entorno del proceso en el momento de la llamada', () => {
    const anterior = process.env.RANGO_MAXIMO_DIAS;
    try {
      process.env.RANGO_MAXIMO_DIAS = '45';
      expect(obtenerParametros().rangoMaximoDias).toBe(45);
      delete process.env.RANGO_MAXIMO_DIAS;
      expect(obtenerParametros().rangoMaximoDias).toBe(366);
    } finally {
      if (anterior === undefined) delete process.env.RANGO_MAXIMO_DIAS;
      else process.env.RANGO_MAXIMO_DIAS = anterior;
    }
  });
});

describe('Valores inválidos', () => {
  test.each([
    ['PORT', 'abc'],
    ['PORT', '0'],
    ['PORT', '65536'],
    ['PORT', '80.5'],
    ['NUM_PROXIES', '-1'],
    ['NUM_PROXIES', '11'],
    ['RATE_LIMIT_VENTANA_MS', '999'],
    ['RATE_LIMIT_VENTANA_MS', '86400001'],
    ['RATE_LIMIT_MAXIMO', '0'],
    ['RATE_LIMIT_MAXIMO', 'mucho'],
    ['RATE_LIMIT_ACTIVIDAD_VENTANA_MS', '0'],
    ['RATE_LIMIT_ACTIVIDAD_MAXIMO', '-5'],
    ['RATE_LIMIT_INTERNO_VENTANA_MS', '1e3'],
    ['RATE_LIMIT_INTERNO_MAXIMO', '1000001'],
    ['CLIMA_TTL_MS', '10'],
    ['CLIMA_CACHE_MAXIMO', '0'],
    ['HTTP_TIMEOUT_DJANGO_MS', '99'],
    ['HTTP_TIMEOUT_CLIMA_MS', '60001'],
    ['BODY_MAXIMO_BYTES', '10kb'],
    ['BODY_MAXIMO_BYTES', '1023'],
    ['MONGO_TIMEOUT_SELECCION_MS', '999'],
    ['MONGO_MAX_POOL', '0'],
    ['MONGO_MAX_POOL', '501'],
    ['RANGO_MAXIMO_DIAS', '0'],
    ['RANGO_MAXIMO_DIAS', '3661'],
  ])('%s=%s corta el arranque y nombra la variable', (variable, valor) => {
    expect(() => leerParametros({ [variable]: valor })).toThrow(variable);
  });

  test.each([
    ['no es una dirección', 'api-del-clima'],
    ['usa otro protocolo', 'ftp://clima.test/v1/forecast'],
    ['lleva credenciales', 'https://usuario:clave@clima.test/v1/forecast'],
  ])('CLIMA_URL que %s corta el arranque', (_motivo, valor) => {
    expect(() => leerParametros({ CLIMA_URL: valor })).toThrow('CLIMA_URL');
  });

  test('el mensaje de error no repite el valor recibido', () => {
    const mensajeDe = (entorno) => {
      try {
        leerParametros(entorno);
      } catch (error) {
        return error.message;
      }
      return '';
    };

    const conCredenciales = mensajeDe({ CLIMA_URL: 'https://usuario:secreto@clima.test' });
    const noNumerico = mensajeDe({ PORT: 'clave-secreta' });

    expect(conCredenciales).toContain('CLIMA_URL');
    expect(conCredenciales).not.toContain('secreto');
    expect(noNumerico).toContain('PORT');
    expect(noNumerico).not.toContain('clave-secreta');
  });
});
