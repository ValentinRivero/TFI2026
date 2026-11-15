const canal = new EventTarget();
const LEIDA = 'notificacion-leida';

/** Avisa a la campana que una notificación propia se marcó como leída, para que descuente el contador en el acto. */
export const anunciarLeida = () => canal.dispatchEvent(new Event(LEIDA));

/** Suscribe `escuchar` a las lecturas anunciadas; devuelve la función que cancela la suscripción. */
export const alMarcarLeida = (escuchar) => {
  canal.addEventListener(LEIDA, escuchar);
  return () => canal.removeEventListener(LEIDA, escuchar);
};
