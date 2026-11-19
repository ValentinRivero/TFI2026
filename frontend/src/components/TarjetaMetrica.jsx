import Card from 'react-bootstrap/Card';

/** Cifra destacada del resumen del dashboard con su rótulo y, opcionalmente, una aclaración. */
export default function TarjetaMetrica({ etiqueta, valor, detalle }) {
  return (
    <Card body className="h-100">
      <p className="small text-secondary mb-1">{etiqueta}</p>
      <p className="metrica-valor num mb-0">{valor}</p>
      {detalle && <p className="small text-secondary mt-1 mb-0">{detalle}</p>}
    </Card>
  );
}
