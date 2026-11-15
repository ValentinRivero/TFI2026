import { useState } from 'react';
import { BLOQUE_LIBRE } from '../config/catalogos.js';
import { formatearHora } from '../utils/formatos.js';

// El horario se compara como `HH:MM`: la API lo devuelve con segundos y la URL de retorno, sin ellos.
const mismaHora = (a, b) => formatearHora(a) === formatearHora(b);

/**
 * Turno elegido en la grilla del día `fecha`. La elección guarda su fecha y se valida contra la grilla vigente
 * (`canchas`): si una actualización lo ocupa, deja de estar `vigente` y `perdida` avisa que hay que elegir otro.
 * `inicial` (`{ fecha, canchaId, horaInicio }`) permite retomar una elección, por ejemplo al volver del login.
 * Devuelve `{ seleccion, cancha, bloque, vigente, perdida, elegir, quitar }`; `seleccion` es `null` si no es vigente.
 */
export default function useSeleccionTurno(fecha, canchas, inicial = null) {
  const [elegido, setElegido] = useState(inicial);

  const delDia = elegido?.fecha === fecha && canchas ? elegido : null;
  const cancha = delDia ? canchas.find((candidata) => candidata.id === delDia.canchaId) ?? null : null;
  const bloque = cancha?.bloques.find((candidato) => mismaHora(candidato.hora_inicio, delDia.horaInicio)) ?? null;
  const vigente = bloque?.estado === BLOQUE_LIBRE;

  const elegir = (canchaElegida, bloqueElegido) => {
    const yaElegido = delDia?.canchaId === canchaElegida.id && mismaHora(delDia.horaInicio, bloqueElegido.hora_inicio);
    setElegido(yaElegido ? null : { fecha, canchaId: canchaElegida.id, horaInicio: bloqueElegido.hora_inicio });
  };

  return {
    seleccion: vigente ? { ...delDia, horaInicio: bloque.hora_inicio } : null,
    cancha,
    bloque,
    vigente,
    perdida: Boolean(delDia) && !vigente,
    elegir,
    quitar: () => setElegido(null),
  };
}
