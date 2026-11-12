/** Estado sin contenido de una pantalla o lista: título, descripción y, opcionalmente, una acción (`children`). */
export default function EstadoVacio({ titulo, descripcion, children, className = '' }) {
  return (
    <div className={`superficie p-4 text-center ${className}`.trim()}>
      <h2 className="h5">{titulo}</h2>
      {descripcion && <p className="text-secondary">{descripcion}</p>}
      {children}
    </div>
  );
}
