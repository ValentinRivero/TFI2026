import {
  ESTADO_PAGO,
  ESTADO_PENDIENTE_SIN_SENA,
  ESTADO_RESERVA,
  ESTADOS_RESERVA_CANCELADOS,
  RESERVA_PENDIENTE,
  RESERVA_SENADA,
} from '../config/catalogos.js';
import { PARAMETROS } from '../config/parametros.js';
import { t } from '../i18n/index.js';

const {
  porcentajeSenaMaximo,
  aliasLargoMinimo,
  aliasLargoMaximo,
  cbuLargo,
  transferenciaTitularMinimo,
  transferenciaTitularMaximo,
  referenciaMinimo,
  referenciaMaximo,
} = PARAMETROS.pagos;

/** Alias de CBU/CVU: letras, números, puntos y guiones, sin espacios, en mayúsculas (espejo de `PATRON_ALIAS` de Django). */
const PATRON_ALIAS = new RegExp(`^[A-Z0-9.-]{${aliasLargoMinimo},${aliasLargoMaximo}}$`);

/** El backend guarda el alias en mayúsculas y sin espacios en los extremos. */
export const normalizarAlias = (texto) => String(texto ?? '').trim().toUpperCase();

/** Error del alias o `undefined`. Vacío es válido salvo que se pida (`obligatorio`), por ejemplo si el complejo exige seña. */
export const errorDeAlias = (texto, { obligatorio = false } = {}) => {
  const alias = normalizarAlias(texto);
  if (alias === '') return obligatorio ? t('configuracion.errorAliasObligatorio') : undefined;
  return PATRON_ALIAS.test(alias)
    ? undefined
    : t('configuracion.errorAlias', { minimo: aliasLargoMinimo, maximo: aliasLargoMaximo });
};

/** Un CBU o CVU se pega con espacios o guiones: se guarda solo con dígitos, como el servidor. */
export const normalizarCbu = (texto) => String(texto ?? '').replace(/[\s-]/g, '');

const PATRON_CBU = new RegExp(`^\\d{${cbuLargo}}$`);

const dvCbu = (digitos, pesos) => (10 - ([...digitos].reduce((suma, digito, i) => suma + Number(digito) * pesos[i], 0) % 10)) % 10;

/** Un CBU o CVU tiene 22 dígitos y sus dos dígitos verificadores correctos (mismo cálculo que el servidor). */
export const esCbuValido = (texto) => {
  const cbu = normalizarCbu(texto);
  return PATRON_CBU.test(cbu)
    && dvCbu(cbu.slice(0, 7), [7, 1, 3, 9, 7, 1, 3]) === Number(cbu[7])
    && dvCbu(cbu.slice(8, 21), [3, 9, 7, 1, 3, 9, 7, 1, 3, 9, 7, 1, 3]) === Number(cbu[21]);
};

/** Error del CBU o CVU (opcional: vacío es válido) o `undefined`. Distingue un largo incorrecto de un dígito mal tipeado. */
export const errorDeCbu = (texto) => {
  const cbu = normalizarCbu(texto);
  if (cbu === '') return undefined;
  if (!PATRON_CBU.test(cbu)) return t('configuracion.errorCbuLargo', { largo: cbuLargo });
  return esCbuValido(cbu) ? undefined : t('configuracion.errorCbuVerificador');
};

/** Un porcentaje de seña es un entero entre 0 (el complejo no exige seña) y 100. */
export const esPorcentajeSenaValido = (texto) => {
  const valor = String(texto ?? '').trim();
  return /^\d+$/.test(valor) && Number(valor) <= porcentajeSenaMaximo;
};

/** Errores por campo de la sección de seña; `{}` significa que se puede enviar. */
export const validarSena = (valores) => {
  const errores = {};
  if (!esPorcentajeSenaValido(valores.porcentaje_sena)) {
    errores.porcentaje_sena = t('configuracion.errorPorcentajeSena', { maximo: porcentajeSenaMaximo });
  }
  const exigeSena = esPorcentajeSenaValido(valores.porcentaje_sena) && Number(valores.porcentaje_sena) > 0;
  const errorAlias = errorDeAlias(valores.alias_transferencia, { obligatorio: exigeSena });
  if (errorAlias) errores.alias_transferencia = errorAlias;
  const errorDelCbu = errorDeCbu(valores.cbu_cvu_transferencia);
  if (errorDelCbu) errores.cbu_cvu_transferencia = errorDelCbu;
  return errores;
};

/** Quien transfirió puede ser una persona o una razón social (espejo de `PATRON_PAGADOR` de Django). */
const PATRON_TITULAR = /^[\p{L}\p{N}_ .,&'’-]+$/u;
/** Número de operación: letras, números y `. _ / -` sin espacios (espejo de `PATRON_REFERENCIA` de Django). */
const PATRON_REFERENCIA = /^[A-Za-z0-9][A-Za-z0-9._/-]*$/;

/** Quita los espacios de los extremos y deja uno solo entre palabras, como el servidor. */
export const colapsarEspacios = (texto) => String(texto ?? '').trim().split(/\s+/).filter(Boolean).join(' ');

/** Error del nombre de quien transfirió o `undefined`. Pide al menos dos letras y solo caracteres de un nombre. */
export const errorDeTitularTransferencia = (texto) => {
  const titular = colapsarEspacios(texto);
  const letras = (titular.match(/\p{L}/gu) ?? []).length;
  const valido = letras >= transferenciaTitularMinimo
    && titular.length <= transferenciaTitularMaximo
    && PATRON_TITULAR.test(titular);
  return valido
    ? undefined
    : t('transferencia.errorTitular', { minimo: transferenciaTitularMinimo, maximo: transferenciaTitularMaximo });
};

/** Error del número de operación o `undefined`. */
export const errorDeReferenciaTransferencia = (texto) => {
  const referencia = colapsarEspacios(texto);
  const valida = referencia.length >= referenciaMinimo
    && referencia.length <= referenciaMaximo
    && PATRON_REFERENCIA.test(referencia);
  return valida ? undefined : t('transferencia.errorReferencia', { minimo: referenciaMinimo, maximo: referenciaMaximo });
};

/** Errores por campo del aviso de transferencia; `{}` significa que se puede enviar. */
export const validarTransferencia = (valores) => {
  const errores = {};
  const errorTitular = errorDeTitularTransferencia(valores.titular);
  if (errorTitular) errores.titular = errorTitular;
  const errorReferencia = errorDeReferenciaTransferencia(valores.referencia);
  if (errorReferencia) errores.referencia = errorReferencia;
  return errores;
};

/** Cuerpo de `POST /api/reservas/<id>/informar-transferencia/`, con los espacios colapsados. */
export const cuerpoTransferencia = (valores) => ({
  titular: colapsarEspacios(valores.titular),
  referencia: colapsarEspacios(valores.referencia),
});

/** El complejo rechazó la transferencia informada y le pidió al jugador que la informe de nuevo. */
export const transferenciaRechazada = (reserva) => Boolean(reserva.transferencia_informada && reserva.transferencia_rechazada);

/** El personal tiene una transferencia informada por verificar: la seña sigue sin confirmarse y no se rechazó. */
export const transferenciaParaRevisar = (reserva) => (
  Boolean(reserva.transferencia_informada && reserva.puede_confirmar_sena && !reserva.transferencia_rechazada)
);

/** Error de la nota del rechazo (largo máximo, igual que el servidor) o `undefined`. Vacío es válido. */
export const errorDeNotaRechazo = (texto) => {
  const maximo = PARAMETROS.pagos.notaRechazoMaximo;
  return String(texto ?? '').trim().length > maximo ? t('transferencia.errorNota', { maximo }) : undefined;
};

/** Importe (número o texto decimal como `"38000.00"`) en centavos enteros, para operar sin errores de coma flotante. */
export const aCentavos = (valor) => Math.round(Number(valor) * 100);

const dePesos = (centavos) => centavos / 100;

/**
 * Precio, seña y saldo de un turno antes de reservarlo. Mismo criterio que el servidor: la seña es el porcentaje del
 * precio redondeado al centavo (mitad hacia arriba) y el saldo es lo que se abona en el complejo. Con un porcentaje
 * inválido o sin seña, la seña es cero. El servidor es la fuente de verdad: al reservar congela sus propios montos.
 */
export const calcularDesglose = (precio, porcentaje) => {
  const total = aCentavos(precio);
  const pct = Number(porcentaje);
  const sena = Number.isFinite(total) && Number.isInteger(pct) && pct > 0
    ? Math.floor((total * Math.min(pct, porcentajeSenaMaximo) + 50) / 100)
    : 0;
  return { total: dePesos(total), sena: dePesos(sena), saldo: dePesos(total - sena) };
};

/** Filas de "Montos del turno" antes de reservar: precio, seña a transferir y saldo a abonar en el complejo. */
export const filasDeDesglose = ({ total, sena, saldo }) => [
  { clave: 'total', etiqueta: t('pagos.precioTotal'), importe: total },
  { clave: 'sena', etiqueta: t('pagos.sena'), importe: sena, destacada: true },
  { clave: 'saldo', etiqueta: t('pagos.saldo'), importe: saldo },
];

/** Filas de los montos congelados de una reserva: precio, seña, abonado y saldo (la seña solo si se acordó una). */
export const filasDeReserva = (reserva) => [
  { clave: 'total', etiqueta: t('pagos.precioTotal'), importe: reserva.precio_acordado },
  ...(Number(reserva.monto_sena) > 0 ? [{ clave: 'sena', etiqueta: t('pagos.sena'), importe: reserva.monto_sena }] : []),
  { clave: 'pagado', etiqueta: t('pagos.pagado'), importe: reserva.monto_pagado },
  { clave: 'saldo', etiqueta: t('pagos.saldoRestante'), importe: reserva.saldo_restante, destacada: true },
];

/** El complejo exige seña si su porcentaje es mayor a cero. */
export const exigeSena = (complejo) => Number(complejo?.porcentaje_sena) > 0;

/** Estado de pago de una reserva con su etiqueta y badge. */
export const estadoDePago = (reserva) => ESTADO_PAGO[reserva.estado_pago] ?? ESTADO_PAGO[1];

/** La reserva tiene una seña acordada. Sin ella no admite el estado «Señada»: se confirma o se registra el pago total. */
export const tieneSena = (reserva) => Number(reserva.monto_sena) > 0;

const PAGOS_QUE_REFLEJA_SENADA = Object.freeze([3, 4]); // seña abonada y pagada

/** En estado «Señada» el badge del estado ya dice cómo está el pago (seña abonada o pagada): no se repite otro. */
export const estadoReflejaElPago = (reserva) => (
  reserva.estado === RESERVA_SENADA && PAGOS_QUE_REFLEJA_SENADA.includes(reserva.estado_pago)
);

/** Hay una seña acordada que todavía no se abonó completa. */
const senaSinAbonar = (reserva) => tieneSena(reserva) && Number(reserva.monto_pagado ?? 0) < Number(reserva.monto_sena);

/**
 * Etiqueta y badge del estado de la reserva. Una señada muestra su estado de pago (seña abonada o pagada) en lugar
 * de «Señada o pagada», y una pendiente se llama «Pendiente de seña» solo mientras haya una seña por abonar: sin
 * seña, o con la seña ya abonada, es simplemente «Pendiente».
 */
export const estadoDeReserva = (reserva) => {
  if (estadoReflejaElPago(reserva)) return estadoDePago(reserva);
  if (reserva.estado === RESERVA_PENDIENTE && !senaSinAbonar(reserva)) return ESTADO_PENDIENTE_SIN_SENA;
  return ESTADO_RESERVA[reserva.estado] ?? ESTADO_RESERVA[0];
};

/** La seña ya se abonó (el personal la confirmó o se saldó la reserva): seña abonada o pagada. */
export const senaConfirmada = (reserva) => PAGOS_QUE_REFLEJA_SENADA.includes(reserva.estado_pago);

/** Etiqueta con la que se ofrece `estado` como destino de un cambio de estado de la reserva (misma regla que el badge). */
export const etiquetaDeEstadoDestino = (reserva, estado) => (
  estadoDeReserva({ ...reserva, estado, estado_pago: undefined }).etiqueta
);

/**
 * Si la reserva muestra seguimiento de pago: hay seña acordada o algo abonado. Una cancelada sin nada abonado no
 * tiene nada que seguir; con algo abonado se muestra, porque hay que resolverlo con el jugador.
 */
export const muestraSeguimientoDePago = (reserva) => {
  const pagado = Number(reserva.monto_pagado) > 0;
  if (ESTADOS_RESERVA_CANCELADOS.includes(reserva.estado)) return pagado;
  return Number(reserva.monto_sena) > 0 || pagado;
};

/** El jugador debe abonar la seña mientras el servidor le entrega los datos de transferencia. */
export const debeAbonarSena = (reserva) => Boolean(reserva.datos_transferencia?.alias);

/** Acciones de cobro que el servidor admite hoy sobre la reserva (el servidor valida igual al aplicarlas). */
export const ACCION_COBRO = Object.freeze({ SENA: 'sena', PAGO_TOTAL: 'pago_total' });

export const accionesDeCobro = (reserva) => [
  ...(reserva.puede_confirmar_sena ? [ACCION_COBRO.SENA] : []),
  ...(reserva.puede_registrar_pago ? [ACCION_COBRO.PAGO_TOTAL] : []),
];
