import { io } from 'socket.io-client';

// Priorité 1: variable d'environnement (ex: REACT_APP_SOCKET_URL=https://poker06.eu.pythonanywhere.com)
const envUrl = process.env.REACT_APP_SOCKET_URL;

// Priorité 2: si on est servi par Flask (port 5000), utiliser l'origine courante (undefined)
const isFlaskOrigin = typeof window !== 'undefined' && window.location && window.location.port === '5000';

// Priorité 3: en dev CRA (port 3000), cibler explicitement http://localhost:5000
const defaultDevUrl = 'http://localhost:5000';

const endpoint = envUrl || (isFlaskOrigin ? undefined : defaultDevUrl);

// Détecter PythonAnywhere pour forcer le transport "polling" (les WebSockets ne sont pas toujours supportés)
let transports = ['polling', 'websocket'];
try {
  const target = endpoint || (typeof window !== 'undefined' ? window.location.origin : '');
  const url = new URL(target);
  if (url.hostname.endsWith('pythonanywhere.com')) {
    transports = ['polling'];
  }
} catch (e) {
  // Fallback silencieux: garder l'ordre polling → websocket
}

const socket = io(endpoint, {
  // Ne pas envoyer de credentials pour éviter CORS entre 3000 et 5000
  withCredentials: false,
  transports,
  autoConnect: true,
});

export default socket;
