import { beforeEach, describe, expect, test, vi } from 'vitest';

const apiDjango = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() }));
vi.mock('./api.js', () => ({ apiDjango }));

const { actualizarRol, crearRol, darDeBajaRol, listarPermisos, listarRoles, reactivarRol } = await import('./rolService.js');

beforeEach(() => {
  Object.values(apiDjango).forEach((funcion) => funcion.mockReset());
});

describe('roles', () => {
  test('lista todos los roles sin paginar', async () => {
    const senal = new AbortController().signal;
    apiDjango.get.mockResolvedValue({ data: [{ id: 1, nombre: 'SUPERADMIN', es_base: true }] });

    await expect(listarRoles(senal)).resolves.toEqual([{ id: 1, nombre: 'SUPERADMIN', es_base: true }]);
    expect(apiDjango.get).toHaveBeenCalledWith('/api/sistema/roles/', { signal: senal });
  });

  test('crea un rol con su cuerpo', async () => {
    const cuerpo = { nombre: 'Cajero', permisos: [1, 2] };
    apiDjango.post.mockResolvedValue({ data: { id: 8, ...cuerpo } });

    await expect(crearRol(cuerpo)).resolves.toEqual({ id: 8, ...cuerpo });
    expect(apiDjango.post).toHaveBeenCalledWith('/api/sistema/roles/', cuerpo);
  });

  test('edita solo lo enviado; los permisos reemplazan la lista', async () => {
    apiDjango.patch.mockResolvedValue({ data: { id: 8 } });

    await actualizarRol(8, { permisos: [3] });

    expect(apiDjango.patch).toHaveBeenCalledWith('/api/sistema/roles/8/', { permisos: [3] });
  });

  test('reactivar envía estado 1', async () => {
    apiDjango.patch.mockResolvedValue({ data: { id: 8, estado: 1 } });

    await reactivarRol(8);

    expect(apiDjango.patch).toHaveBeenCalledWith('/api/sistema/roles/8/', { estado: 1 });
  });

  test('la baja es un DELETE y no devuelve cuerpo', async () => {
    apiDjango.delete.mockResolvedValue({ status: 204 });

    await expect(darDeBajaRol(8)).resolves.toBeUndefined();
    expect(apiDjango.delete).toHaveBeenCalledWith('/api/sistema/roles/8/');
  });

  test('un rechazo (rol base o en uso) se propaga tal cual', async () => {
    const error = new Error('protegido');
    apiDjango.patch.mockRejectedValue(error);

    await expect(actualizarRol(1, { nombre: 'X' })).rejects.toBe(error);
  });
});

describe('permisos', () => {
  test('trae el catálogo completo con la marca de asignable', async () => {
    const permisos = [
      { id: 1, codigo: 'ver_agenda', nombre: 'Ver la agenda', modulo: 'agenda', asignable: true },
      { id: 2, codigo: 'administrar_roles', nombre: 'Administrar roles', modulo: 'sistema', asignable: false },
    ];
    apiDjango.get.mockResolvedValue({ data: permisos });

    await expect(listarPermisos()).resolves.toEqual(permisos);
    expect(apiDjango.get).toHaveBeenCalledWith('/api/sistema/permisos/', { signal: undefined });
  });
});
