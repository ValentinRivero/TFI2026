import { describir, ESTADO_USUARIO, ETIQUETA_ROL } from '../config/catalogos.js';
import useResumenUsuario from '../hooks/useResumenUsuario.js';
import { t } from '../i18n/index.js';
import Cargando from './Cargando.jsx';

const BAJA = 0;

/**
 * Resumen mínimo de una cuenta (nombre, rol, estado y complejo) para el recuadro emergente de la auditoría. Se
 * monta recién al mostrarse el recuadro, así que solo consulta las cuentas que el superadmin realmente mira. El
 * complejo es el vinculado a la cuenta o, si no tiene, el del evento de auditoría (`complejoNombre`).
 */
export default function ResumenUsuario({ usuarioId, complejoNombre }) {
  const { datos, error, cargando } = useResumenUsuario(usuarioId);

  if (cargando) return <Cargando variante="inline" />;
  if (error || !datos) return <p className="small text-danger mb-0">{t('usuarios.resumenError')}</p>;

  const estado = describir(ESTADO_USUARIO, datos.estado);
  const complejo = datos.complejo_operado_nombre || complejoNombre;

  return (
    <div>
      <p className="fw-semibold mb-1">{datos.nombre_completo}</p>
      <dl className="row g-1 small mb-0">
        <dt className="col-4 fw-normal text-secondary">{t('usuarios.resumenRol')}</dt>
        <dd className="col-8 mb-0">{ETIQUETA_ROL[datos.rol] ?? datos.rol}</dd>
        <dt className="col-4 fw-normal text-secondary">{t('usuarios.resumenEstado')}</dt>
        <dd className="col-8 mb-0"><span className={`badge ${estado.badge}`}>{estado.etiqueta}</span></dd>
        {complejo && (
          <>
            <dt className="col-4 fw-normal text-secondary">{t('usuarios.resumenComplejo')}</dt>
            <dd className="col-8 mb-0">{complejo}</dd>
          </>
        )}
      </dl>
      {datos.estado === BAJA && <p className="small text-secondary mt-2 mb-0">{t('usuarios.resumenBaja')}</p>}
    </div>
  );
}
