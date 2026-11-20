const canal = new EventTarget();
const LEIDA = 'notificacion-leida';
const TODAS_LEIDAS = 'notificaciones-todas-leidas';

/** Avisa a la campana que una notificación propia se marcó como leída, para que descuente el contador en el acto. */
export const anunciarLeida = () => canal.dispatchEvent(new Event(LEIDA));

/** Suscribe `escuchar` a las lecturas anunciadas; devuelve la función que cancela la suscripción. */
export const alMarcarLeida = (escuchar) => {
  canal.addEventListener(LEIDA, escuchar);
  return () => canal.removeEventListener(LEIDA, escuchar);
};

/** Avisa que todas las notificaciones propias se marcaron como leídas, para que los contadores pasen a cero en el acto. */
export const anunciarTodasLeidas = () => canal.dispatchEvent(new Event(TODAS_LEIDAS));

/** Suscribe `escuchar` al aviso de "todas leídas"; devuelve la función que cancela la suscripción. */
export const alMarcarTodasLeidas = (escuchar) => {
  canal.addEventListener(TODAS_LEIDAS, escuchar);
  return () => canal.removeEventListener(TODAS_LEIDAS, escuchar);
};
