import { io } from 'socket.io-client';

// Priorité 1: variable d'environnement (ex: REACT_APP_SOCKET_URL=https://poker06.eu.pythonanywhere.com)
const envUrl = process.env.REACT_APP_SOCKET_URL;

// Détection environnement
const isBrowser = typeof window !== 'undefined';
const isDev = process.env.NODE_ENV === 'development';

// Ne forcer le polling que si explicitement demandé
const forcePolling = process.env.REACT_APP_SIO_POLLING_ONLY === '1';

// Endpoint: par défaut same-origin (undefined). Permet au build servi par Flask de fonctionner sur n'importe quel domaine/port.
// On n'utilise un endpoint explicite que si REACT_APP_SOCKET_URL est défini.
const endpoint = envUrl || undefined;

// Transports: autoriser websocket + polling par défaut avec upgrade pour une meilleure résilience en dev
let transports = ['websocket', 'polling'];
let disableUpgrade = false; // autoriser le handshake polling -> websocket

// Forcer le polling sur certains hôtes si nécessaire (ex: pythonanywhere bloque WS)
try {
  const targetOrigin = envUrl || (isBrowser ? window.location.origin : '');
  const url = new URL(targetOrigin);
  if (url.hostname.endsWith('pythonanywhere.com')) {
    transports = ['polling'];
    disableUpgrade = true;
  }
} catch (e) {
  // Fallback silencieux
}

// Si explicitement forcé, basculer en polling-only
if (forcePolling) {
  transports = ['polling'];
  disableUpgrade = true;
}

const socket = io(endpoint, {
  withCredentials: false,
  transports,
  upgrade: !disableUpgrade,
  reconnection: true,
  reconnectionAttempts: Infinity,
  reconnectionDelay: 500,
  reconnectionDelayMax: 5000,
  timeout: 25000,
});

export default socket;
