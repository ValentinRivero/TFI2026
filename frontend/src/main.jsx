import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import 'bootstrap/dist/css/bootstrap.min.css';
import './styles/tema.css';
import App from './App.jsx';
import { iniciarSesionPrevia } from './services/authService.js';
import { registrarServiceWorker } from './utils/serviceWorker.js';

// Recupera la sesión (refresh con la cookie y perfil) mientras se dibuja la app.
iniciarSesionPrevia();
registrarServiceWorker();

createRoot(document.getElementById('raiz')).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>,
);
