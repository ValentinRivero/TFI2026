import { useMemo } from 'react';
import { puedeVer } from '../config/catalogos.js';
import { listarAdministrados } from '../services/complejoAdminService.js';
import useConsulta from './useConsulta.js';
import useSesion from './useSesion.js';

/**
 * Complejos cuyos avisos recibe el usuario, para distinguirlos en la bandeja y filtrar por uno. Solo los pide quien
 * recibe avisos por complejo (dueño y operador); con un solo complejo no hay nada que distinguir y devuelve la lista
 * igual, para que quien la usa decida si la muestra. Si la consulta falla, la bandeja sigue sin ese detalle.
 */
export default function useComplejosDeNotificaciones() {
  const { rol } = useSesion();
  const aplica = puedeVer('avisosPorComplejo', rol);
  const consulta = useConsulta(
    (signal) => (aplica ? listarAdministrados(signal) : Promise.resolve([])),
    [aplica],
  );

  const complejos = useMemo(
    () => (consulta.datos ?? []).map(({ id, nombre }) => ({ id, nombre })),
    [consulta.datos],
  );
  const nombres = useMemo(
    () => (complejos.length > 1 ? Object.fromEntries(complejos.map(({ id, nombre }) => [id, nombre])) : {}),
    [complejos],
  );

  return { complejos, nombres, variosComplejos: complejos.length > 1 };
}
