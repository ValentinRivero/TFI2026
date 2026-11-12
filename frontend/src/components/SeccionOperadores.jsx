import Card from 'react-bootstrap/Card';
import { t } from '../i18n/index.js';
import Alerta from './Alerta.jsx';
import FormularioOperador from './FormularioOperador.jsx';
import ListaAdmin from './ListaAdmin.jsx';
import ModalConfirmarAccion from './ModalConfirmarAccion.jsx';
import OperadorRow from './OperadorRow.jsx';

const COLUMNAS = [
  { clave: 'nombre', etiqueta: t('operadores.nombre') },
  { clave: 'correo', etiqueta: t('operadores.correo') },
  { clave: 'telefono', etiqueta: t('operadores.telefono') },
  { clave: 'acciones', etiqueta: t('operadores.acciones'), className: 'text-lg-end' },
];

/**
 * Operadores del complejo (presentación): alta por correo, lista paginada y desvinculación con confirmación.
 * `operadores` es lo que devuelve `useOperadores`. Solo la ven el dueño y el superadmin.
 */
export default function SeccionOperadores({ operadores }) {
  const { lista, aviso, aDesvincular } = operadores;

  return (
    <Card body className="mb-4">
      <h2 className="h5">{t('operadores.titulo')}</h2>
      <p className="text-secondary">{t('operadores.descripcion')}</p>

      {aviso && (
        <Alerta variante="success" onCerrar={operadores.descartarAviso}>
          {t(aviso === 'vinculado' ? 'operadores.vinculado' : 'operadores.desvinculado')}
        </Alerta>
      )}

      <FormularioOperador
        email={operadores.email}
        onCambiar={operadores.cambiarEmail}
        onEnviar={operadores.vincular}
        enviando={operadores.vinculando}
        error={operadores.errorVincular}
      />

      <ListaAdmin
        lista={lista}
        columnas={COLUMNAS}
        etiqueta={t('operadores.titulo')}
        resumen={t('operadores.resumen', { total: lista.total })}
        errorTitulo={t('operadores.errorTitulo')}
        vacio={{ titulo: t('operadores.vacioTitulo'), descripcion: t('operadores.vacioDescripcion') }}
        renderFila={(operador) => (
          <OperadorRow key={operador.id} operador={operador} onDesvincular={operadores.pedirDesvincular} />
        )}
      />

      <ModalConfirmarAccion
        abierto={Boolean(aDesvincular)}
        titulo={t('operadores.confirmarTitulo')}
        texto={t('operadores.confirmarTexto', { nombre: aDesvincular?.nombre_completo ?? '' })}
        error={operadores.errorDesvincular}
        textoConfirmar={t('operadores.desvincular')}
        onConfirmar={operadores.confirmarDesvincular}
        onCancelar={operadores.cerrarDesvincular}
      />
    </Card>
  );
}
