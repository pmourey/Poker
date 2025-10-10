import { io } from 'socket.io-client';

// Priorité 1: variable d'environnement (ex: REACT_APP_SOCKET_URL=https://poker06.eu.pythonanywhere.com)
const envUrl = process.env.REACT_APP_SOCKET_URL;

// Détection environnement
const isBrowser = typeof window !== 'undefined';
const isDev = process.env.NODE_ENV === 'development';

// Toggle pour forcer le mode polling (évite les upgrades WS en dev / derrière proxy NAT)
const forcePolling = process.env.REACT_APP_SIO_POLLING_ONLY === '1' || isDev;

// Si servi par Flask (port 5000), on garde same-origin (endpoint undefined)
const isFlaskOrigin = isBrowser && window.location && window.location.port === '5000';

// En dev CRA, préférer same-origin pour exploiter le proxy CRA → Flask
// Fallback (production statique en local): cibler explicitement http://localhost:5000
const defaultDevUrl = 'http://localhost:5000';

// Choix de l’endpoint
// - envUrl si défini
// - sinon same-origin en dev CRA et si servi par Flask
// - sinon fallback explicite (ex: build statique pointant sur un backend local)
const endpoint = envUrl || (isFlaskOrigin ? undefined : (isDev ? undefined : defaultDevUrl));

// Détecter PythonAnywhere pour forcer le transport "polling"
let transports = ['polling', 'websocket'];
let disableUpgrade = false;
try {
  const targetOrigin = envUrl || (isBrowser ? window.location.origin : '');
  const url = new URL(targetOrigin);
  if (url.hostname.endsWith('pythonanywhere.com')) {
    transports = ['polling'];
    disableUpgrade = true; // éviter toute tentative d'upgrade côté client
  }
} catch (e) {
  // Fallback silencieux: garder l'ordre polling → websocket
}

// En développement (ou si REACT_APP_SIO_POLLING_ONLY=1), forcer polling-only
if (forcePolling) {
  transports = ['polling'];
  disableUpgrade = true;
}

const socket = io(endpoint, {
  withCredentials: false,
  transports,
  upgrade: disableUpgrade || false,
  reconnection: true,
  reconnectionAttempts: Infinity,
  reconnectionDelay: 500,
  reconnectionDelayMax: 5000,
  timeout: 25000,
});

export default socket;
