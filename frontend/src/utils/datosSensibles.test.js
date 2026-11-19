import { describe, expect, test } from 'vitest';
import { esValorEnmascarable } from './datosSensibles.js';

describe('esValorEnmascarable', () => {
  test.each(['190.0.2.14', '2001:db8::1', ' 10.0.0.1 '])('un dato real (%s) se puede ocultar', (valor) => {
    expect(esValorEnmascarable(valor)).toBe(true);
  });

  test.each([null, undefined, '', '   ', '-', '—', '–', ' - '])('la ausencia de dato (%j) no se oculta', (valor) => {
    expect(esValorEnmascarable(valor)).toBe(false);
  });
});
