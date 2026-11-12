import Alert from 'react-bootstrap/Alert';

/** Aviso en pantalla. Muestra texto plano: el contenido de la API nunca se interpreta como HTML. */
export default function Alerta({ variante = 'danger', titulo, children, onCerrar, className = '' }) {
  return (
    <Alert variant={variante} dismissible={Boolean(onCerrar)} onClose={onCerrar} className={className} role="alert">
      {titulo && <Alert.Heading as="h2" className="h6 mb-1">{titulo}</Alert.Heading>}
      {children}
    </Alert>
  );
}
