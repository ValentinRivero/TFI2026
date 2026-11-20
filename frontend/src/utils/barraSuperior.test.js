import { readFileSync } from 'node:fs';
import { describe, expect, test } from 'vitest';

const layout = readFileSync(new URL('../components/Layout.jsx', import.meta.url), 'utf8');
const campana = readFileSync(new URL('../components/CampanaNotificaciones.jsx', import.meta.url), 'utf8');
const tema = readFileSync(new URL('../styles/tema.css', import.meta.url), 'utf8');

// Anchos mínimos de Bootstrap 5 por breakpoint.
const ANCHO_BREAKPOINT = { sm: 576, md: 768, lg: 992, xl: 1200, xxl: 1400 };

const breakpoint = layout.match(/expand="(\w+)"/)?.[1];

describe('barra superior', () => {
  test('el breakpoint de la barra es uno de los de Bootstrap', () => {
    expect(ANCHO_BREAKPOINT).toHaveProperty(breakpoint);
  });

  test('los controles que alternan entre móvil y escritorio usan el mismo breakpoint que la barra', () => {
    const utilidades = [...layout.matchAll(/\bd-(?:(\w+)-)?(?:none|inline-flex)\b/g), ...campana.matchAll(/\bd-(\w+)-none\b/g)]
      .map((m) => m[1])
      .filter(Boolean);

    expect(utilidades.length).toBeGreaterThan(0);
    expect(new Set(utilidades)).toEqual(new Set([breakpoint]));
  });

  test('las reglas de escritorio y de móvil del tema se parten en el ancho del breakpoint', () => {
    const ancho = ANCHO_BREAKPOINT[breakpoint];
    const seccionBarra = tema.slice(tema.indexOf('.barra-superior {'), tema.indexOf('.pie-pagina {'));

    expect(seccionBarra).toContain(`@media (min-width: ${ancho}px)`);
    expect(seccionBarra).toContain(`@media (max-width: ${ancho - 0.02}px)`);
  });

  test('el nombre de usuario se trunca con elipsis y muestra el texto completo en el title', () => {
    expect(layout).toMatch(/className="barra-usuario"\s+title=\{textoUsuario\}/);
    expect(tema).toMatch(/\.barra-superior \.barra-usuario \{[^}]*text-overflow: ellipsis;[^}]*white-space: nowrap;/);
  });

  test('los enlaces de secciones no se parten en dos líneas', () => {
    expect(layout).toMatch(/className="barra-secciones text-nowrap"/);
  });
});
