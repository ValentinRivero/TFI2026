/** Sección titulada de la política de privacidad. */
export default function SeccionPolitica({ titulo, children }) {
  return (
    <section className="mb-4">
      <h2 className="h4">{titulo}</h2>
      {children}
    </section>
  );
}
