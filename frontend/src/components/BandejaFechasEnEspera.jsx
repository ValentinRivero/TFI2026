import { ACCION_FECHA_TURNO_FIJO } from '../config/catalogos.js';
import { t } from '../i18n/index.js';
import { formatearFechaLarga } from '../utils/formatos.js';
import Alerta from './Alerta.jsx';
import FilaFechaEnEspera from './FilaFechaEnEspera.jsx';
import ListaAdmin from './ListaAdmin.jsx';
import ModalConfirmar from './ModalConfirmar.jsx';

const COLUMNAS = [
  { clave: 'turno', etiqueta: t('turnosFijos.espera.columnas.turno') },
  { clave: 'cliente', etiqueta: t('turnosFijos.espera.columnas.cliente') },
  { clave: 'fecha', etiqueta: t('turnosFijos.espera.columnas.fecha') },
  { clave: 'motivo', etiqueta: t('turnosFijos.espera.columnas.motivo') },
  { clave: 'acciones', etiqueta: t('turnosFijos.espera.columnas.acciones'), className: 'text-lg-end' },
];

/**
 * Bandeja de fechas de turnos fijos que una excepción horaria dejó en espera (presentación). Mientras esperan siguen
 * ocupadas en la grilla: el complejo decide si cada una se mantiene (queda confirmada) o se cancela (el cierre de la
 * excepción vuelve a regir). No se muestra si no hay nada pendiente. `espera` es lo que devuelve `useTurnosFijos`.
 */
export default function BandejaFechasEnEspera({ espera }) {
  const { lista, resolucion } = espera;
  const pedido = resolucion.objetivo;
  const cancelar = pedido?.accion === ACCION_FECHA_TURNO_FIJO.CANCELAR;

  // Sin nada pendiente (o mientras llega la primera respuesta) la bandeja no ocupa lugar en la pantalla.
  if (!lista.error && lista.items.length === 0) return null;

  return (
    <section className="mb-4" aria-labelledby="titulo-espera">
      <h2 id="titulo-espera" className="h5">{t('turnosFijos.espera.titulo')}</h2>
      <p className="text-secondary">{t('turnosFijos.espera.descripcion')}</p>
      <ListaAdmin
        lista={lista}
        columnas={COLUMNAS}
        etiqueta={t('turnosFijos.espera.titulo')}
        resumen={t('turnosFijos.espera.resumen', { total: lista.total })}
        errorTitulo={t('turnosFijos.espera.errorTitulo')}
        vacio={{ titulo: t('turnosFijos.espera.vacioTitulo') }}
        renderFila={(fila) => (
          <FilaFechaEnEspera key={fila.clave} fila={fila} onMantener={espera.pedirMantener} onCancelar={espera.pedirCancelar} />
        )}
      />

      <ModalConfirmar
        mostrar={Boolean(pedido)}
        titulo={cancelar ? t('turnosFijos.espera.cancelarTitulo') : t('turnosFijos.espera.mantenerTitulo')}
        textoConfirmar={cancelar ? t('turnosFijos.espera.cancelar') : t('turnosFijos.espera.mantener')}
        variante={cancelar ? 'danger' : 'primary'}
        onConfirmar={resolucion.confirmar}
        onCancelar={resolucion.cerrar}
      >
        {pedido && (
          <>
            {resolucion.error && <Alerta variante="danger">{resolucion.error.mensaje}</Alerta>}
            <p className="mb-0">
              {t(cancelar ? 'turnosFijos.espera.cancelarTexto' : 'turnosFijos.espera.mantenerTexto', {
                fecha: formatearFechaLarga(pedido.fila.fecha),
                cancha: pedido.fila.turno.cancha_nombre,
              })}
            </p>
          </>
        )}
      </ModalConfirmar>
    </section>
  );
}
