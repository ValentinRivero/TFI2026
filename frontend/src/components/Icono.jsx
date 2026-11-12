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
  inicio: 'M4 11l8-7 8 7M6 9.5V20h4v-6h4v6h4V9.5',
  candado: 'M7 11V8a5 5 0 0110 0v3M6 11h12a1 1 0 011 1v7a1 1 0 01-1 1H6a1 1 0 01-1-1v-7a1 1 0 011-1zM12 15v2',
  buscar: 'M11 18a7 7 0 100-14 7 7 0 000 14zM20.5 20.5L16 16',
  correo: 'M4 6h16a1 1 0 011 1v10a1 1 0 01-1 1H4a1 1 0 01-1-1V7a1 1 0 011-1zM3.5 7.5l8.5 6 8.5-6',
  instagram: 'M7 3.5h10A3.5 3.5 0 0120.5 7v10a3.5 3.5 0 01-3.5 3.5H7A3.5 3.5 0 013.5 17V7A3.5 3.5 0 017 3.5zM12 16a4 4 0 100-8 4 4 0 000 8zM17 7.5v.01',
  facebook: 'M14 20v-7.5h2.5l.5-3h-3V7.7c0-.9.3-1.5 1.6-1.5H17V3.6c-.3-.1-1.2-.2-2.2-.2C12.5 3.4 11 4.8 11 7.2v2.3H8.5v3H11V20h3z',
  twitter: 'M5 5l14 14M19 5L5 19',
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
