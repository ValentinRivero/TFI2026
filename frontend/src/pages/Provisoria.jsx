import { ETIQUETA_ROL } from '../config/catalogos.js';
import useSesion from '../hooks/useSesion.js';
import { t } from '../i18n/index.js';

/** Vista mínima de las pantallas que se completan en etapas siguientes: permite probar rutas, sesión y roles. */
export default function Provisoria({ titulo }) {
  const { usuario, rol } = useSesion();

  return (
    <section>
      <h1 className="h2">{titulo}</h1>
      <p className="text-secondary">{t('provisoria.descripcion')}</p>
      {usuario && (
        <p className="small mb-0">
          {t('provisoria.sesion', { nombre: usuario.nombre_completo, rol: ETIQUETA_ROL[rol] ?? rol ?? '' })}
        </p>
      )}
    </section>
  );
}
