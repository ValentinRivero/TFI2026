/** Título de una pantalla con su descripción opcional y, a la derecha (debajo en pantallas chicas), sus acciones. */
export default function EncabezadoPantalla({ titulo, descripcion, acciones }) {
  const texto = (
    <div>
      <h1 className="h2">{titulo}</h1>
      {descripcion && <p className="text-secondary mb-0">{descripcion}</p>}
    </div>
  );
  if (!acciones) return <header className="mb-4">{texto}</header>;
  return (
    <header className="mb-4 d-flex flex-wrap justify-content-between align-items-start gap-3">
      {texto}
      <div className="flex-shrink-0">{acciones}</div>
    </header>
  );
}
