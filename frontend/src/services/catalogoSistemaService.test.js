import { beforeEach, describe, expect, test, vi } from 'vitest';

const apiDjango = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() }));
vi.mock('./api.js', () => ({ apiDjango }));

const {
  crearItemCatalogo,
  darDeBajaItemCatalogo,
  listarCatalogoSistema,
  listarUsosCatalogo,
  reactivarItemCatalogo,
  renombrarItemCatalogo,
} = await import('./catalogoSistemaService.js');

beforeEach(() => {
  Object.values(apiDjango).forEach((funcion) => funcion.mockReset());
});

describe.each([
  ['deportes', '/api/sistema/deportes/'],
  ['servicios', '/api/sistema/servicios/'],
])('catálogo de %s', (recurso, ruta) => {
  test('lista toda la colección sin paginar y devuelve el arreglo', async () => {
    const senal = new AbortController().signal;
    apiDjango.get.mockResolvedValue({ data: [{ id: 1, nombre: 'Pádel', estado: 1, usos: 2 }] });

    await expect(listarCatalogoSistema(recurso, senal)).resolves.toEqual([{ id: 1, nombre: 'Pádel', estado: 1, usos: 2 }]);
    expect(apiDjango.get).toHaveBeenCalledWith(ruta, { signal: senal });
  });

  test('crea un ítem con solo el nombre', async () => {
    apiDjango.post.mockResolvedValue({ data: { id: 9, nombre: 'Nuevo' } });

    await expect(crearItemCatalogo(recurso, 'Nuevo')).resolves.toEqual({ id: 9, nombre: 'Nuevo' });
    expect(apiDjango.post).toHaveBeenCalledWith(ruta, { nombre: 'Nuevo' });
  });

  test('renombra con un PATCH que lleva solo el nombre', async () => {
    apiDjango.patch.mockResolvedValue({ data: { id: 4, nombre: 'Otro' } });

    await renombrarItemCatalogo(recurso, 4, 'Otro');

    expect(apiDjango.patch).toHaveBeenCalledWith(`${ruta}4/`, { nombre: 'Otro' });
  });

  test('reactiva con estado 1', async () => {
    apiDjango.patch.mockResolvedValue({ data: { id: 4, estado: 1 } });

    await reactivarItemCatalogo(recurso, 4);

    expect(apiDjango.patch).toHaveBeenCalledWith(`${ruta}4/`, { estado: 1 });
  });

  test('la baja es un DELETE al ítem y no devuelve cuerpo', async () => {
    apiDjango.delete.mockResolvedValue({ status: 204 });

    await expect(darDeBajaItemCatalogo(recurso, 4)).resolves.toBeUndefined();
    expect(apiDjango.delete).toHaveBeenCalledWith(`${ruta}4/`);
  });

  test('pide una página de dónde está en uso el ítem', async () => {
    const senal = new AbortController().signal;
    const pagina = { count: 1, next: null, results: [{ complejo_id: 5, complejo_nombre: 'Complejo El Yacaré' }] };
    apiDjango.get.mockResolvedValue({ data: pagina });

    await expect(listarUsosCatalogo(recurso, 4, 2, senal)).resolves.toEqual(pagina);
    expect(apiDjango.get).toHaveBeenCalledWith(`${ruta}4/usos/`, { params: { page: 2 }, signal: senal });
  });

  test('un error al pedir los usos se propaga para que el diálogo lo muestre', async () => {
    const error = new Error('404');
    apiDjango.get.mockRejectedValue(error);

    await expect(listarUsosCatalogo(recurso, 4, 1)).rejects.toBe(error);
  });

  test('un rechazo del backend (por ejemplo, ítem en uso) se propaga tal cual', async () => {
    const error = new Error('en uso');
    apiDjango.delete.mockRejectedValue(error);

    await expect(darDeBajaItemCatalogo(recurso, 4)).rejects.toBe(error);
  });
});

test('un catálogo desconocido no llega a la red', async () => {
  await expect(listarCatalogoSistema('canchas')).rejects.toThrow('Catálogo desconocido');
  expect(apiDjango.get).not.toHaveBeenCalled();
});
