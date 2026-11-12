// Argentina no aplica horario de verano desde 2009: el desplazamiento fijo coincide con el `TIME_ZONE` de Django
// y sirve tanto para armar los límites del rango como para agrupar por día en MongoDB.
export const ZONA_HORARIA = '-03:00';

const FECHA = /^\d{4}-\d{2}-\d{2}$/;
const MS_POR_DIA = 86_400_000;

const enUtc = (texto) => new Date(`${texto}T00:00:00Z`);

/** `AAAA-MM-DD` de un día que existe en el calendario (rechaza, por ejemplo, el 30 de febrero). */
export const esFecha = (texto) => typeof texto === 'string'
  && FECHA.test(texto)
  && !Number.isNaN(enUtc(texto).getTime())
  && enUtc(texto).toISOString().startsWith(texto);

/** Instante en que empieza el día en hora de Argentina. */
export const inicioDelDia = (texto) => new Date(`${texto}T00:00:00${ZONA_HORARIA}`);

export const sumarDias = (texto, dias) => new Date(enUtc(texto).getTime() + dias * MS_POR_DIA).toISOString().slice(0, 10);

/** Cantidad de días del rango, ambos extremos incluidos. */
export const diasEntre = (desde, hasta) => (enUtc(hasta) - enUtc(desde)) / MS_POR_DIA + 1;

export const diasDelRango = (desde, hasta) => Array.from({ length: diasEntre(desde, hasta) }, (_, i) => sumarDias(desde, i));
