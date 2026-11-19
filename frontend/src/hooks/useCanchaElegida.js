import { useState } from 'react';

/**
 * Cancha elegida en el paso previo a la grilla. `canchas` son las canchas activas del complejo (o `null` mientras
 * carga) e `inicialId`, la que se retoma al volver del login. Con una sola cancha activa queda elegida por defecto; una
 * elección que ya no existe entre las canchas se descarta. Devuelve `{ cancha, elegir }`.
 */
export default function useCanchaElegida(canchas, inicialId = null) {
  const [elegidaId, setElegidaId] = useState(inicialId);

  const elegida = canchas?.find((candidata) => candidata.id === elegidaId) ?? null;
  const unica = canchas?.length === 1 ? canchas[0] : null;

  return { cancha: elegida ?? unica, elegir: setElegidaId };
}
