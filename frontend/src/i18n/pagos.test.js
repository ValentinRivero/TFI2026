import { describe, expect, test, vi } from 'vitest';
import { t } from './index.js';

const CLAVES_DE_SENAS_Y_PAGOS = [
  'complejo.senaPorcentaje',
  'complejo.sinSena',
  'reserva.creadaSena',
  'reserva.creadaSinSena',
  'reserva.desgloseTitulo',
  'reserva.desgloseSenaAviso',
  'pagos.precioTotal',
  'pagos.sena',
  'pagos.pagado',
  'pagos.saldo',
  'pagos.saldoRestante',
  'pagos.estadoPago',
  'pagos.tarjetaTitulo',
  'pagos.tarjetaAyuda',
  'pagos.alias',
  'pagos.titular',
  'pagos.copiarAlias',
  'pagos.aliasCopiado',
  'pagos.errorCopiar',
  'pagos.confirmarSena',
  'pagos.registrarPago',
  'pagos.confirmarSenaTitulo',
  'pagos.confirmarSenaTexto',
  'pagos.registrarPagoTitulo',
  'pagos.registrarPagoTexto',
  'pagos.avisoSena',
  'pagos.avisoPago',
  'pagos.accionesDe',
  'configuracion.senaTitulo',
  'configuracion.senaDescripcion',
  'configuracion.porcentajeSena',
  'configuracion.ayudaPorcentajeSena',
  'configuracion.aliasTransferencia',
  'configuracion.ayudaAlias',
  'configuracion.titularTransferencia',
  'configuracion.ayudaTitular',
  'configuracion.errorPorcentajeSena',
  'configuracion.errorAliasObligatorio',
  'configuracion.errorAlias',
  'configuracion.cbuTransferencia',
  'configuracion.ayudaCbu',
  'configuracion.errorCbuLargo',
  'configuracion.errorCbuVerificador',
  'pagos.cbu',
  'pagos.copiarCbu',
  'pagos.tarjetaAyudaConCbu',
  'agenda.editarObservaciones',
  'agenda.editarObservacionesDe',
  'agenda.observacionesTitulo',
  'agenda.observacionesTurno',
  'agenda.observacionesContador',
  'agenda.errorObservaciones',
  'agenda.avisoObservaciones',
  'agenda.periodoProximaSemana',
  'agenda.periodoProximoMes',
  'agenda.periodoProximoTrimestre',
  'transferencia.avisoReenviada',
  'transferencia.avisoRechazada',
  'transferencia.rechazada',
  'transferencia.rechazadaTitulo',
  'transferencia.rechazadaAyuda',
  'transferencia.volverAInformar',
  'transferencia.tituloReenviar',
  'transferencia.rechazar',
  'transferencia.rechazarTitulo',
  'transferencia.motivo',
  'transferencia.nota',
  'transferencia.ayudaNota',
  'transferencia.errorNota',
  'transferencia.avisoRechazo',
  'pagos.anularCobro',
  'pagos.anularTitulo',
  'pagos.anularTexto',
  'pagos.avisoAnulado',
  'transferencia.informar',
  'transferencia.corregir',
  'transferencia.informada',
  'transferencia.enRevision',
  'transferencia.confirmada',
  'transferencia.informadaEl',
  'transferencia.quien',
  'transferencia.operacion',
  'transferencia.invitacion',
  'transferencia.titulo',
  'transferencia.tituloCorregir',
  'transferencia.turno',
  'transferencia.texto',
  'transferencia.titular',
  'transferencia.ayudaTitular',
  'transferencia.referencia',
  'transferencia.ayudaReferencia',
  'transferencia.privacidad',
  'transferencia.enviar',
  'transferencia.guardarCorreccion',
  'transferencia.errorTitular',
  'transferencia.errorReferencia',
  'transferencia.avisoInformada',
  'transferencia.avisoCorregida',
  'transferencia.datosInformados',
  'transferencia.comparar',
  'transferencia.montoAVerificar',
  'transferencia.sinAviso',
];

describe('textos de señas y pagos', () => {
  test.each(CLAVES_DE_SENAS_Y_PAGOS)('existe la clave %s', (clave) => {
    const aviso = vi.spyOn(console, 'warn').mockImplementation(() => {});

    expect(t(clave)).not.toBe(clave);
    expect(aviso).not.toHaveBeenCalled();
    aviso.mockRestore();
  });

  test('el porcentaje de la ficha no deja el signo pegado a un marcador', () => {
    expect(t('complejo.senaPorcentaje', { porcentaje: 30 })).toBe('Seña del 30%, por transferencia.');
  });

  test('el texto de la tarjeta de alias nombra el monto a transferir', () => {
    expect(t('pagos.tarjetaAyuda', { monto: '$ 11.400' })).toContain('$ 11.400');
  });

  test('los textos de confirmación de cobro completan todos sus marcadores', () => {
    const datos = { monto: '$ 100', fecha: 'martes', hora: '14:00', cancha: 'Cancha 1' };

    expect(t('pagos.confirmarSenaTexto', datos)).not.toMatch(/%\w+%/);
    expect(t('pagos.registrarPagoTexto', datos)).not.toMatch(/%\w+%/);
  });
});
