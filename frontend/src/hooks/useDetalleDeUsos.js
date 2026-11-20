import { useState } from 'react';
import { listarUsosCatalogo } from '../services/catalogoSistemaService.js';
import { listarUsosRol } from '../services/rolService.js';
import useListaIncremental from './useListaIncremental.js';

const SIN_USOS = Object.freeze({ count: 0, next: null, results: [] });

/**
 * Dónde está en uso un ítem de `deportes`, `servicios` o `roles`, cargado bajo demanda y de a páginas ("Mostrar más").
 * Sirve a dos diálogos: el de detalle (`abrir(item)` / `cerrar`, con `objetivo` el ítem abierto) y el de baja, al que se
 * le pasa `objetivoDeBaja` para listar lo que impide la baja de un ítem en uso. Mientras ninguno esté abierto no pide nada.
 * `lista` es lo que devuelve `useListaIncremental`.
 */
export default function useDetalleDeUsos(tipo, objetivoDeBaja = null) {
  const [objetivo, setObjetivo] = useState(null);
  const enBaja = objetivoDeBaja && objetivoDeBaja.usos > 0 ? objetivoDeBaja : null;
  const consultado = objetivo ?? enBaja;
  const id = consultado?.id ?? null;

  const lista = useListaIncremental((pagina, signal) => {
    if (id === null) return SIN_USOS;
    return tipo === 'roles' ? listarUsosRol(id, pagina, signal) : listarUsosCatalogo(tipo, id, pagina, signal);
  }, [tipo, id]);

  return { objetivo, abrir: setObjetivo, cerrar: () => setObjetivo(null), lista };
}
