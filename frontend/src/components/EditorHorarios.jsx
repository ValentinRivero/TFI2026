import Button from 'react-bootstrap/Button';
import { t } from '../i18n/index.js';
import { agruparPorDia } from '../utils/horarios.js';
import Alerta from './Alerta.jsx';
import AlertaReintento from './AlertaReintento.jsx';
import BotonAccion from './BotonAccion.jsx';
import Cargando from './Cargando.jsx';
import DiaHorarios from './DiaHorarios.jsx';
import EncabezadoPantalla from './EncabezadoPantalla.jsx';
import Icono from './Icono.jsx';

/**
 * Editor semanal de horarios de una cancha (presentación): siete días con uno o más rangos cada uno, tarifa
 * diferenciada opcional y acciones de guardado. `editor` es lo que devuelve `useEditorHorarios`. Con `soloLectura`
 * (operador) se consultan los rangos sin poder modificarlos.
 */
export default function EditorHorarios({ cancha, editor, soloLectura, onVolver }) {
  const { filas, errores, cargando, errorCarga, aplicando, error, guardado, hayCambios } = editor;

  return (
    <div>
      <div className="mb-3">
        <Button variant="outline-secondary" onClick={onVolver}>
          <Icono nombre="anterior" tamano={16} /> {t('horarios.volver')}
        </Button>
      </div>
      <EncabezadoPantalla titulo={t('horarios.titulo', { cancha: cancha.nombre })} descripcion={t('horarios.descripcion')} />

      {soloLectura && <Alerta variante="info">{t('horarios.soloLectura')}</Alerta>}
      {cargando && <Cargando variante="seccion" />}
      {!cargando && errorCarga && (
        <AlertaReintento titulo={t('horarios.errorCargaTitulo')} mensaje={errorCarga.mensaje} onReintentar={editor.recargar} />
      )}

      {!cargando && !errorCarga && (
        <>
          {error && (
            <Alerta variante="danger" titulo={t('horarios.errorGuardar')}>{error.mensaje}</Alerta>
          )}
          {guardado && <Alerta variante="success">{t('horarios.guardado')}</Alerta>}
          {!soloLectura && <p className="small text-secondary">{t('horarios.ayudaPrecio')}</p>}

          <div className={`grilla-dias mb-4${soloLectura ? ' solo-lectura' : ''}`}>
            {agruparPorDia(filas).map(({ dia, filas: delDia }) => (
              <DiaHorarios
                key={dia}
                dia={dia}
                filas={delDia}
                errores={errores}
                soloLectura={soloLectura}
                onAgregar={editor.agregar}
                onCambiar={editor.cambiar}
                onQuitar={editor.quitar}
              />
            ))}
          </div>

          {!soloLectura && (
            <div className="d-flex flex-wrap gap-2">
              <BotonAccion cargando={aplicando} disabled={!hayCambios} textoCargando={t('horarios.guardando')} onClick={editor.guardar}>
                {t('horarios.guardar')}
              </BotonAccion>
              <Button variant="outline-secondary" disabled={!hayCambios || aplicando} onClick={editor.descartar}>
                {t('horarios.descartar')}
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
