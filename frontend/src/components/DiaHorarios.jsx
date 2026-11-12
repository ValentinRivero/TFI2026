import Button from 'react-bootstrap/Button';
import { DIA_SEMANA } from '../config/catalogos.js';
import { t } from '../i18n/index.js';
import RangoHorarioRow from './RangoHorarioRow.jsx';

/**
 * Los rangos de apertura de un día de la semana. Un día sin rangos queda cerrado. `errores` es el mapa por fila de
 * `validarBorrador` (clave de la fila a errores por campo).
 */
export default function DiaHorarios({ dia, filas, errores, soloLectura, onAgregar, onCambiar, onQuitar }) {
  const nombre = DIA_SEMANA[dia].etiqueta;

  return (
    <section className="dia-horarios" aria-label={nombre}>
      <div className="d-flex flex-wrap align-items-center justify-content-between gap-2 mb-2">
        <h3 className="h6 mb-0">{nombre}</h3>
        {!soloLectura && (
          <Button size="sm" variant="outline-primary" onClick={() => onAgregar(dia)}>
            {t('horarios.agregar')}
          </Button>
        )}
      </div>

      {filas.length === 0 && <p className="text-secondary small mb-0">{t('horarios.cerrado')}</p>}

      <div className="d-grid gap-2">
        {filas.map((fila, indice) => (
          <RangoHorarioRow
            key={fila.clave}
            fila={fila}
            errores={errores[fila.clave]}
            descripcion={t('horarios.rangoDelDia', { numero: indice + 1, dia: nombre })}
            soloLectura={soloLectura}
            onCambiar={onCambiar}
            onQuitar={onQuitar}
          />
        ))}
      </div>
    </section>
  );
}
