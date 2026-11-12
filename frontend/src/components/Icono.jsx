/**
 * Íconos de interfaz: trazos SVG propios sobre una grilla de 24 x 24, sin librerías ni imágenes de terceros.
 * Para sumar uno alcanza con agregar su trazado a `TRAZOS`. Heredan el color del texto (`currentColor`).
 */
const TRAZOS = {
  check: 'M5 12.5l4.5 4.5L19 7.5',
  cerrar: 'M6 6l12 12M18 6L6 18',
  menu: 'M4 7h16M4 12h16M4 17h16',
  usuario: 'M12 12a4 4 0 100-8 4 4 0 000 8zM4.5 20a7.5 7.5 0 0115 0',
  calendario: 'M5 6h14a1 1 0 011 1v12a1 1 0 01-1 1H5a1 1 0 01-1-1V7a1 1 0 011-1zM4 10.5h16M8.5 3.5v4M15.5 3.5v4',
  reloj: 'M12 21a9 9 0 100-18 9 9 0 000 18zM12 7v5.5l3.5 2',
  ubicacion: 'M12 21s-6.5-5.6-6.5-11a6.5 6.5 0 0113 0c0 5.4-6.5 11-6.5 11zM12 12.5a2.5 2.5 0 100-5 2.5 2.5 0 000 5z',
  alerta: 'M12 4l9 16H3L12 4zM12 10v4.5M12 17.5v.01',
  informacion: 'M12 21a9 9 0 100-18 9 9 0 000 18zM12 11v5.5M12 7.5v.01',
  anterior: 'M14.5 6l-6 6 6 6',
  siguiente: 'M9.5 6l6 6-6 6',
  campana: 'M6 17h12l-1.5-2.5V10a4.5 4.5 0 00-9 0v4.5L6 17zM10 20a2 2 0 004 0',
  mapa: 'M9 4L3.5 6v14L9 18l6 2 5.5-2V4L15 6 9 4zM9 4v14M15 6v14',
};

export default function Icono({ nombre, tamano = 20, titulo, className = '' }) {
  const trazo = TRAZOS[nombre];
  if (!trazo) return null;
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      width={tamano}
      height={tamano}
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      role={titulo ? 'img' : undefined}
      aria-label={titulo}
      aria-hidden={titulo ? undefined : 'true'}
      focusable="false"
    >
      <path d={trazo} />
    </svg>
  );
}
