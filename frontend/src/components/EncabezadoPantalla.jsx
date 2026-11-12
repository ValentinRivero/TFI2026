/** Título de una pantalla con su descripción opcional. */
export default function EncabezadoPantalla({ titulo, descripcion }) {
  return (
    <header className="mb-4">
      <h1 className="h2">{titulo}</h1>
      {descripcion && <p className="text-secondary mb-0">{descripcion}</p>}
    </header>
  );
}
