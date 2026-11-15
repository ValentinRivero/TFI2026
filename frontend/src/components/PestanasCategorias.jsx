import Nav from 'react-bootstrap/Nav';
import { CATEGORIA_NOTIFICACION } from '../config/catalogos.js';
import { t } from '../i18n/index.js';

const TODAS = 'todas';

/**
 * Pestañas por categoría de notificación (Todas, Reservas, Cuentas, Operatoria y Sistema). `activa` es el código de la
 * categoría o vacío para todas; `onCambiar` recibe el mismo formato.
 */
export default function PestanasCategorias({ activa, onCambiar }) {
  const pestanas = [
    { valor: TODAS, etiqueta: t('notificaciones.categoriaTodas') },
    ...Object.entries(CATEGORIA_NOTIFICACION).map(([codigo, { etiqueta }]) => ({ valor: codigo, etiqueta })),
  ];
  const vigente = activa || TODAS;

  return (
    <Nav
      variant="tabs"
      className="mb-3 flex-nowrap overflow-auto"
      activeKey={vigente}
      onSelect={(valor) => onCambiar(valor === TODAS ? '' : valor)}
      aria-label={t('notificaciones.categorias')}
    >
      {pestanas.map(({ valor, etiqueta }) => (
        <Nav.Item key={valor}>
          <Nav.Link as="button" type="button" eventKey={valor} aria-current={valor === vigente ? 'page' : undefined} className="text-nowrap">
            {etiqueta}
          </Nav.Link>
        </Nav.Item>
      ))}
    </Nav>
  );
}
