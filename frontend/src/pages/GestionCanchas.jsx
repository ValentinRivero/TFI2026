import { useState } from 'react';
import Button from 'react-bootstrap/Button';
import Alerta from '../components/Alerta.jsx';
import ConfirmarConflicto from '../components/ConfirmarConflicto.jsx';
import EditorHorarios from '../components/EditorHorarios.jsx';
import EncabezadoPantalla from '../components/EncabezadoPantalla.jsx';
import ModalCancha from '../components/ModalCancha.jsx';
import ModalConfirmarAccion from '../components/ModalConfirmarAccion.jsx';
import TablaCanchas from '../components/TablaCanchas.jsx';
import useContextoPanel from '../hooks/useContextoPanel.js';
import useEditorHorarios from '../hooks/useEditorHorarios.js';
import useGestionCanchas from '../hooks/useGestionCanchas.js';
import { t } from '../i18n/index.js';

/**
 * Canchas del complejo activo y, desde cada una, el editor de sus horarios. El dueño y el superadmin crean, editan y
 * dan de baja canchas y horarios; el operador solo los consulta. Los cambios que dejan reservas o turnos fijos
 * fuera de la grilla piden confirmación con el detalle de lo afectado.
 */
export default function GestionCanchas() {
  const { complejo, permisos } = useContextoPanel();
  const canchas = useGestionCanchas(complejo.id);
  const [canchaHorarios, setCanchaHorarios] = useState(null);
  const horarios = useEditorHorarios(canchaHorarios);

  if (canchaHorarios) {
    return (
      <>
        <EditorHorarios
          cancha={canchaHorarios}
          editor={horarios}
          soloLectura={!permisos.canchas}
          onVolver={() => setCanchaHorarios(null)}
        />
        <ConfirmarConflicto
          conflicto={horarios.conflicto}
          error={horarios.error}
          onConfirmar={horarios.confirmarConflicto}
          onCancelar={horarios.cancelarConflicto}
        />
      </>
    );
  }

  const { baja } = canchas;

  return (
    <div>
      <EncabezadoPantalla titulo={t('gestionCanchas.titulo')} descripcion={t('gestionCanchas.descripcion')} />
      {!permisos.canchas && <Alerta variante="info">{t('gestionCanchas.soloLectura')}</Alerta>}
      {canchas.aviso && <Alerta variante="success" onCerrar={canchas.descartarAviso}>{canchas.aviso}</Alerta>}

      {permisos.canchas && (
        <div className="mb-3">
          <Button onClick={canchas.abrirAlta}>{t('gestionCanchas.nueva')}</Button>
        </div>
      )}

      <TablaCanchas
        lista={canchas.lista}
        puedeAdministrar={permisos.canchas}
        onNueva={canchas.abrirAlta}
        onHorarios={setCanchaHorarios}
        onEditar={canchas.abrirEdicion}
        onBaja={baja.pedir}
      />

      <ModalCancha formulario={canchas.formulario} deportes={canchas.deportes} />
      <ConfirmarConflicto
        conflicto={canchas.conflicto}
        error={canchas.conflicto?.error}
        onConfirmar={canchas.confirmarConflicto}
        onCancelar={canchas.cancelarConflicto}
      />
      <ModalConfirmarAccion
        abierto={Boolean(baja.cancha)}
        titulo={t('gestionCanchas.bajaTitulo')}
        texto={t('gestionCanchas.bajaTexto', { nombre: baja.cancha?.nombre ?? '' })}
        error={baja.error}
        textoConfirmar={t('gestionCanchas.bajaConfirmar')}
        onConfirmar={baja.confirmar}
        onCancelar={baja.cerrar}
      />
    </div>
  );
}
