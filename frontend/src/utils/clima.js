/** Pronóstico del día `fecha` (`AAAA-MM-DD`) si cae dentro de los días que informa Node; si no, `null`. */
export const pronosticoDeFecha = (clima, fecha) => (
  clima?.pronostico?.find((dia) => dia.fecha === fecha) ?? null
);
