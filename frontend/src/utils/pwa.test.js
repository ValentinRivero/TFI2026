import { describe, expect, test } from 'vitest';
import { esIOS, esIOSConInstalacionManual, estaInstalada, modoDelBanner } from './pwa.js';

const SAFARI_IPHONE = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1';
const CHROME_ANDROID = 'Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36';
const INSTAGRAM_IPHONE = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 Instagram 320.0';

describe('esIOS', () => {
  test('reconoce iPhone, iPad y iPod por el user agent', () => {
    expect(esIOS({ userAgent: SAFARI_IPHONE })).toBe(true);
    expect(esIOS({ userAgent: 'Mozilla/5.0 (iPad; CPU OS 17_4 like Mac OS X)' })).toBe(true);
    expect(esIOS({ userAgent: 'Mozilla/5.0 (iPod touch; CPU iPhone OS 15_0)' })).toBe(true);
  });

  test('un iPad que se presenta como Mac se reconoce por la pantalla táctil', () => {
    expect(esIOS({ userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)', platform: 'MacIntel', maxTouchPoints: 5 })).toBe(true);
  });

  test('una Mac de escritorio y Android no son iOS', () => {
    expect(esIOS({ userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)', platform: 'MacIntel', maxTouchPoints: 0 })).toBe(false);
    expect(esIOS({ userAgent: CHROME_ANDROID, platform: 'Linux armv8l', maxTouchPoints: 5 })).toBe(false);
  });

  test('sin datos del navegador no es iOS', () => {
    expect(esIOS()).toBe(false);
    expect(esIOS({})).toBe(false);
  });
});

describe('esIOSConInstalacionManual', () => {
  test('iOS en un navegador común permite la instalación manual', () => {
    expect(esIOSConInstalacionManual({ userAgent: SAFARI_IPHONE })).toBe(true);
  });

  test('el navegador incrustado de otra app no la ofrece', () => {
    expect(esIOSConInstalacionManual({ userAgent: INSTAGRAM_IPHONE })).toBe(false);
  });

  test('fuera de iOS no corresponde', () => {
    expect(esIOSConInstalacionManual({ userAgent: CHROME_ANDROID })).toBe(false);
    expect(esIOSConInstalacionManual()).toBe(false);
  });
});

describe('estaInstalada', () => {
  test('modo standalone o navigator.standalone en iOS', () => {
    expect(estaInstalada({ modoStandalone: true })).toBe(true);
    expect(estaInstalada({ standaloneIOS: true })).toBe(true);
  });

  test('en una pestaña común no está instalada', () => {
    expect(estaInstalada({ modoStandalone: false, standaloneIOS: false })).toBe(false);
    expect(estaInstalada({ standaloneIOS: undefined })).toBe(false);
    expect(estaInstalada()).toBe(false);
  });
});

describe('modoDelBanner', () => {
  const base = { instalada: false, cerrado: false, hayAviso: false, ios: false };

  test('con el aviso del navegador ofrece instalar', () => {
    expect(modoDelBanner({ ...base, hayAviso: true })).toBe('instalar');
  });

  test('en iOS sin aviso muestra la indicación manual', () => {
    expect(modoDelBanner({ ...base, ios: true })).toBe('ios');
  });

  test('si hay aviso, prevalece sobre la indicación de iOS', () => {
    expect(modoDelBanner({ ...base, ios: true, hayAviso: true })).toBe('instalar');
  });

  test('no se muestra si ya está instalada o el usuario lo cerró', () => {
    expect(modoDelBanner({ ...base, hayAviso: true, instalada: true })).toBeNull();
    expect(modoDelBanner({ ...base, ios: true, instalada: true })).toBeNull();
    expect(modoDelBanner({ ...base, hayAviso: true, cerrado: true })).toBeNull();
    expect(modoDelBanner({ ...base, ios: true, cerrado: true })).toBeNull();
  });

  test('en un navegador sin soporte no muestra nada', () => {
    expect(modoDelBanner(base)).toBeNull();
  });
});
