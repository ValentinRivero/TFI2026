/**
 * Registro en memoria de las fallas de servicios de los que depende backend-node (Django, MongoDB, Open-Meteo). Solo
 * guarda el momento de cada una, con un tope, para que `/api/interno/estado` informe si hubo varias seguidas.
 */
const MAXIMO_REGISTRADAS = 500;

let momentos = [];

export const registrarFallaExterna = (ahora = Date.now()) => {
  momentos.push(ahora);
  if (momentos.length > MAXIMO_REGISTRADAS) momentos = momentos.slice(-MAXIMO_REGISTRADAS);
};

export const contarFallasExternas = (ventanaMs, ahora = Date.now()) => (
  momentos.filter((momento) => ahora - momento <= ventanaMs).length
);

export const reiniciarFallasExternas = () => {
  momentos = [];
};
