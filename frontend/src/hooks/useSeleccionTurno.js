import { useState } from 'react';
import { BLOQUE_LIBRE } from '../config/catalogos.js';

/**
 * Turno elegido en la grilla del día `fecha`. La elección guarda su fecha y se valida contra la grilla vigente
 * (`canchas`): si una actualización lo ocupa, deja de estar `vigente` y `perdida` avisa que hay que elegir otro.
 * Devuelve `{ seleccion, cancha, bloque, vigente, perdida, elegir, quitar }`; `seleccion` es `null` si no es vigente.
 */
export default function useSeleccionTurno(fecha, canchas) {
  const [elegido, setElegido] = useState(null);

  const delDia = elegido?.fecha === fecha && canchas ? elegido : null;
  const cancha = delDia ? canchas.find((candidata) => candidata.id === delDia.canchaId) ?? null : null;
  const bloque = cancha?.bloques.find((candidato) => candidato.hora_inicio === delDia.horaInicio) ?? null;
  const vigente = bloque?.estado === BLOQUE_LIBRE;

  const elegir = (canchaElegida, bloqueElegido) => {
    const yaElegido = delDia?.canchaId === canchaElegida.id && delDia.horaInicio === bloqueElegido.hora_inicio;
    setElegido(yaElegido ? null : { fecha, canchaId: canchaElegida.id, horaInicio: bloqueElegido.hora_inicio });
  };

  return {
    seleccion: vigente ? delDia : null,
    cancha,
    bloque,
    vigente,
    perdida: Boolean(delDia) && !vigente,
    elegir,
    quitar: () => setElegido(null),
  };
}
