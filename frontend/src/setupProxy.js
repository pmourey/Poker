/*
  Proxy de développement ciblé pour CRA:
  - Redirige /socket.io (HTTP/WS) vers le backend Flask (http://localhost:5000)
  - Redirige /api (HTTP) vers le backend Flask pour les endpoints REST (ex: /api/games)
*/
const { createProxyMiddleware } = require('http-proxy-middleware');

// WS activé par défaut, sauf si explicitement désactivé ou si on utilise une URL directe
const hasDirectURL = !!process.env.REACT_APP_SOCKET_URL;
const wsDisabled = process.env.REACT_APP_PROXY_SOCKETIO_WS === '0';
const enableSocketIOWS = !wsDisabled && !hasDirectURL;

module.exports = function(app) {
  // API REST
  app.use(
    '/api',
    createProxyMiddleware({
      target: 'http://localhost:5000',
      changeOrigin: true,
      ws: true,
      logLevel: 'warn',
      proxyTimeout: 30000,
      timeout: 30000,
    })
  );

  // Socket.IO (HTTP + WS)
  app.use(
    '/socket.io',
    createProxyMiddleware({
      target: 'http://localhost:5000',
      changeOrigin: true,
      ws: enableSocketIOWS,
      logLevel: 'warn',
      proxyTimeout: 120000,
      timeout: 120000,
      onError(err, req, res) {
        console.warn('[proxy:/socket.io] error:', err && err.message);
      },
    })
  );
};
