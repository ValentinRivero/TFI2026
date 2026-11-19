import Card from 'react-bootstrap/Card';

/** Bloque titulado del dashboard (desglose, ocupación, ranking, visitas); `children` es su contenido. */
export default function TarjetaReporte({ titulo, descripcion, children, className = '' }) {
  return (
    <Card body className={`h-100 ${className}`.trim()}>
      <h2 className="h5">{titulo}</h2>
      {descripcion && <p className="small text-secondary">{descripcion}</p>}
      {children}
    </Card>
  );
}
