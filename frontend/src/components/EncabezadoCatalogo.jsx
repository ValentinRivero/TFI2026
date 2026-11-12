import { t } from '../i18n/index.js';

/** Bienvenida de la portada; `children` es el lugar del clima general de la ciudad. */
export default function EncabezadoCatalogo({ children }) {
  return (
    <header className="mb-4">
      <h1 className="display-6">{t('catalogo.titulo')}</h1>
      <p className="lead text-secondary mb-3">{t('catalogo.bienvenida')}</p>
      {children}
    </header>
  );
}
