import { DIA_SEMANA } from '../config/catalogos.js';
import { t } from '../i18n/index.js';
import { formatearHora } from './formatos.js';

const DIAS = Object.freeze(Object.keys(DIA_SEMANA).map(Number));
const HORA = /^([01]\d|2[0-3]):[0-5]\d$/;

/** Fila del borrador del editor a partir de un rango del servidor (`id` conserva el vínculo para editar o dar de baja). */
export const aFilaBorrador = (horario) => ({
  clave: `h-${horario.id}`,
  id: horario.id,
  dia_semana: horario.dia_semana,
  hora_apertura: formatearHora(horario.hora_apertura),
  hora_cierre: formatearHora(horario.hora_cierre),
  precio_diferenciado: horario.precio_diferenciado === null || horario.precio_diferenciado === undefined
    ? ''
    : String(Number(horario.precio_diferenciado)),
});

/** Fila vacía para un día; `clave` identifica la fila en pantalla hasta que el servidor le asigne un `id`. */
export const filaNueva = (diaSemana, clave) => ({
  clave,
  id: null,
  dia_semana: diaSemana,
  hora_apertura: '',
  hora_cierre: '',
  precio_diferenciado: '',
});

/** Filas agrupadas por día de la semana (lunes a domingo), cada día ordenado por hora de apertura. */
export const agruparPorDia = (filas) => DIAS.map((dia) => ({
  dia,
  filas: filas
    .filter((fila) => fila.dia_semana === dia)
    .sort((a, b) => a.hora_apertura.localeCompare(b.hora_apertura)),
}));

const precioValido = (texto) => texto === '' || (Number.isFinite(Number(texto)) && Number(texto) >= 0);

/**
 * Errores del borrador por fila (`{ [clave]: { hora_apertura?, hora_cierre?, precio_diferenciado? } }`). Un objeto
 * vacío significa que se puede guardar. El servidor repite estas reglas; acá se evita un viaje con datos incompletos.
 */
export const validarBorrador = (filas) => {
  const errores = {};
  const marcar = (clave, campo, mensaje) => {
    errores[clave] = { ...errores[clave], [campo]: mensaje };
  };

  filas.forEach((fila) => {
    if (!HORA.test(fila.hora_apertura)) marcar(fila.clave, 'hora_apertura', t('horarios.errorHora'));
    if (!HORA.test(fila.hora_cierre)) marcar(fila.clave, 'hora_cierre', t('horarios.errorHora'));
    if (HORA.test(fila.hora_apertura) && HORA.test(fila.hora_cierre) && fila.hora_cierre <= fila.hora_apertura) {
      marcar(fila.clave, 'hora_cierre', t('horarios.errorCierre'));
    }
    if (!precioValido(fila.precio_diferenciado)) marcar(fila.clave, 'precio_diferenciado', t('horarios.errorPrecio'));
  });

  agruparPorDia(filas).forEach(({ filas: delDia }) => {
    const completas = delDia.filter((fila) => HORA.test(fila.hora_apertura) && HORA.test(fila.hora_cierre));
    completas.forEach((fila, indice) => {
      const previa = completas[indice - 1];
      if (previa && previa.hora_cierre > fila.hora_apertura && !errores[fila.clave]?.hora_apertura) {
        marcar(fila.clave, 'hora_apertura', t('horarios.errorSolape'));
      }
    });
  });

  return errores;
};

const aCuerpo = (fila) => ({
  dia_semana: fila.dia_semana,
  hora_apertura: fila.hora_apertura,
  hora_cierre: fila.hora_cierre,
  precio_diferenciado: fila.precio_diferenciado === '' ? null : fila.precio_diferenciado,
});

const mismoPrecio = (a, b) => (a === '' || b === '' ? a === b : Number(a) === Number(b));

/**
 * Diferencia entre lo guardado (`base`) y el borrador: `bajas` (ids), `modificaciones` (id y solo los campos que
 * cambiaron) y `altas` (cuerpos completos). Se aplican en ese orden para liberar horario antes de ocuparlo.
 */
export const calcularCambios = (base, borrador) => {
  const idsBorrador = new Set(borrador.filter((fila) => fila.id !== null).map((fila) => fila.id));
  const porId = new Map(base.map((fila) => [fila.id, fila]));

  const bajas = base.filter((fila) => !idsBorrador.has(fila.id)).map((fila) => fila.id);
  const modificaciones = [];
  borrador.filter((fila) => fila.id !== null && porId.has(fila.id)).forEach((fila) => {
    const original = porId.get(fila.id);
    const cuerpo = aCuerpo(fila);
    const cambios = {};
    ['dia_semana', 'hora_apertura', 'hora_cierre'].forEach((campo) => {
      if (fila[campo] !== original[campo]) cambios[campo] = cuerpo[campo];
    });
    if (!mismoPrecio(fila.precio_diferenciado, original.precio_diferenciado)) {
      cambios.precio_diferenciado = cuerpo.precio_diferenciado;
    }
    if (Object.keys(cambios).length > 0) modificaciones.push({ id: fila.id, cambios });
  });
  const altas = borrador.filter((fila) => fila.id === null).map((fila) => {
    const cuerpo = aCuerpo(fila);
    if (cuerpo.precio_diferenciado === null) delete cuerpo.precio_diferenciado;
    return cuerpo;
  });

  return { bajas, modificaciones, altas };
};

export const hayCambios = ({ bajas, modificaciones, altas }) => bajas.length + modificaciones.length + altas.length > 0;
