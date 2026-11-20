import Button from 'react-bootstrap/Button';
import { Link } from 'react-router-dom';
import { describir, ESTADO_USUARIO } from '../config/catalogos.js';
import { t } from '../i18n/index.js';
import { rutaDeFichaUsuario } from '../utils/sistema.js';
import Alerta from './Alerta.jsx';
import AlertaReintento from './AlertaReintento.jsx';
import BotonAccion from './BotonAccion.jsx';
import Cargando from './Cargando.jsx';

const nombresDeCanchas = (canchas) => canchas.map((cancha) => cancha.nombre).join(', ');

/** Complejo con las canchas que usan el deporte y el acceso a las canchas del complejo en el panel. */
function UsoDeporte({ uso, onIrAlComplejo }) {
  return (
    <li className="d-flex flex-wrap justify-content-between align-items-start gap-2 py-2 border-bottom">
      <div>
        <div>{uso.complejo_nombre}</div>
        <div className="small text-secondary">{t('usos.deportes.canchas', { canchas: nombresDeCanchas(uso.canchas) })}</div>
      </div>
      <Button size="sm" variant="outline-secondary" onClick={() => onIrAlComplejo(uso.complejo_id)}>
        {t('usos.deportes.ir')}
      </Button>
    </li>
  );
}

/** Complejo que ofrece el servicio y el acceso a su configuración en el panel. */
function UsoServicio({ uso, onIrAlComplejo }) {
  return (
    <li className="d-flex flex-wrap justify-content-between align-items-center gap-2 py-2 border-bottom">
      <span>{uso.complejo_nombre}</span>
      <Button size="sm" variant="outline-secondary" onClick={() => onIrAlComplejo(uso.complejo_id)}>
        {t('usos.servicios.ir')}
      </Button>
    </li>
  );
}

/** Cuenta con el rol y el enlace a su ficha en la gestión de usuarios. */
function UsoRol({ uso }) {
  const estado = describir(ESTADO_USUARIO, uso.estado);

  return (
    <li className="d-flex flex-wrap justify-content-between align-items-start gap-2 py-2 border-bottom">
      <div>
        <div>{uso.nombre}</div>
        <div className="small text-secondary">{uso.email}</div>
        <span className={`badge ${estado.badge} mt-1`}>{estado.etiqueta}</span>
      </div>
      <Link to={rutaDeFichaUsuario(uso.id)} className="btn btn-sm btn-outline-secondary">{t('usos.roles.ir')}</Link>
    </li>
  );
}

const ITEMS = { deportes: UsoDeporte, servicios: UsoServicio, roles: UsoRol };

const clave = (tipo, uso) => (tipo === 'roles' ? uso.id : uso.complejo_id);

/**
 * Dónde está en uso un ítem, con sus estados de carga, error y "Mostrar más". `tipo` es `deportes`, `servicios` o
 * `roles`; `usos` es lo que devuelve `useDetalleDeUsos` (`lista`); `onIrAlComplejo(id)` lleva al panel del complejo.
 */
export default function ListaUsos({ tipo, usos, onIrAlComplejo }) {
  const { items, total, hayMas, cargando, cargandoMas, error, errorMas, cargarMas, recargar } = usos;
  const Item = ITEMS[tipo];

  if (cargando) return <Cargando variante="seccion" />;
  if (error) return <AlertaReintento titulo={t('usos.errorTitulo')} mensaje={error.mensaje} onReintentar={recargar} />;
  if (items.length === 0) return <p className="text-secondary mb-0">{t('usos.vacio')}</p>;

  return (
    <section aria-label={t(`usos.${tipo}.titulo`)}>
      <p className="small text-secondary" role="status">{t(`usos.${tipo}.resumen`, { mostrados: items.length, total })}</p>
      <ul className="list-unstyled mb-3">
        {items.map((uso) => <Item key={clave(tipo, uso)} uso={uso} onIrAlComplejo={onIrAlComplejo} />)}
      </ul>
      {errorMas && <Alerta variante="warning">{t('usos.errorMas')} {errorMas.mensaje}</Alerta>}
      {hayMas && (
        <div className="text-center">
          <BotonAccion variant="outline-primary" cargando={cargandoMas} onClick={cargarMas}>{t('comun.mostrarMas')}</BotonAccion>
        </div>
      )}
      <p className="small text-secondary mt-3 mb-0">{t(`usos.${tipo}.ayuda`)}</p>
    </section>
  );
}
