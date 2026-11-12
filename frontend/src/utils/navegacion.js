/**
 * Único enlace de la barra que corresponde a la ruta actual, o `null` si ninguno. La portada (`/`) coincide solo de
 * forma exacta; el resto, por ruta exacta o de subruta (`/panel/agenda` pertenece a `/panel`). Si varios coinciden
 * (`/panel` y `/panel/reportes` para `/panel/reportes`), gana el más específico: nunca hay dos activos a la vez.
 */
export const enlaceActivo = (pathname, rutas) => {
  const coincidencias = rutas.filter((ruta) => (
    ruta === '/' ? pathname === '/' : pathname === ruta || pathname.startsWith(`${ruta}/`)
  ));
  return coincidencias.reduce((mejor, ruta) => (mejor === null || ruta.length > mejor.length ? ruta : mejor), null);
};
