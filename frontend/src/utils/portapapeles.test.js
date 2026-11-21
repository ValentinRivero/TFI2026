import { describe, expect, test, vi } from 'vitest';
import { copiarAlPortapapeles } from './portapapeles.js';

const documentoFalso = (copiar = () => true) => {
  const campo = { setAttribute: vi.fn(), select: vi.fn(), style: {}, value: '' };
  const documento = {
    body: { appendChild: vi.fn(), removeChild: vi.fn() },
    createElement: vi.fn(() => campo),
    execCommand: vi.fn(copiar),
  };
  return { documento, campo };
};

describe('copiarAlPortapapeles', () => {
  test('usa la API del portapapeles cuando existe', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);

    await expect(copiarAlPortapapeles('YACARE.SENA', { navigator: { clipboard: { writeText } } })).resolves.toBe(true);
    expect(writeText).toHaveBeenCalledWith('YACARE.SENA');
  });

  test('si la API rechaza (permiso o contexto inseguro) copia seleccionando un campo oculto', async () => {
    const writeText = vi.fn().mockRejectedValue(new Error('denegado'));
    const { documento, campo } = documentoFalso();

    await expect(copiarAlPortapapeles('YACARE.SENA', { navigator: { clipboard: { writeText } }, document: documento })).resolves.toBe(true);
    expect(campo.value).toBe('YACARE.SENA');
    expect(campo.select).toHaveBeenCalled();
    expect(documento.execCommand).toHaveBeenCalledWith('copy');
    expect(documento.body.removeChild).toHaveBeenCalledWith(campo);
  });

  test('sin API del portapapeles usa el respaldo', async () => {
    const { documento } = documentoFalso();

    await expect(copiarAlPortapapeles('ALIAS.UNO', { document: documento })).resolves.toBe(true);
    expect(documento.body.appendChild).toHaveBeenCalledTimes(1);
  });

  test('responde false si el respaldo falla o lanza, y limpia el campo temporal', async () => {
    const falla = documentoFalso(() => false);
    const lanza = documentoFalso(() => { throw new Error('no soportado'); });

    await expect(copiarAlPortapapeles('X', { document: falla.documento })).resolves.toBe(false);
    await expect(copiarAlPortapapeles('X', { document: lanza.documento })).resolves.toBe(false);
    expect(lanza.documento.body.removeChild).toHaveBeenCalled();
  });

  test('sin API ni documento responde false sin lanzar', async () => {
    await expect(copiarAlPortapapeles('X', {})).resolves.toBe(false);
  });
});
