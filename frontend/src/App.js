import React, { useEffect, useMemo, useRef, useState } from 'react';
import './App.css';
import socket from './socket';

function App() {
  const [connected, setConnected] = useState(false);
  const [playerName, setPlayerName] = useState('');
  // Charger le nom stocké localement au premier rendu (pré-remplissage pratique)
  useEffect(() => {
    try {
      const stored = localStorage.getItem('playerName');
      if (stored) setPlayerName(stored);
    } catch (_) { /* ignore */ }
  }, []);
  // Sauvegarder le nom à chaque changement
  useEffect(() => {
    try { localStorage.setItem('playerName', playerName || ''); } catch (_) { /* ignore */ }
  }, [playerName]);

  const [gameIdInput, setGameIdInput] = useState('');
  const [gameId, setGameId] = useState('');
  const [playerId, setPlayerId] = useState('');
  const [game, setGame] = useState(null); // server game_update (no hands)
  const [myHand, setMyHand] = useState([]);
  const [error, setError] = useState('');
  const [raiseAmount, setRaiseAmount] = useState(20);
  const [handResult, setHandResult] = useState(null);
  const [tableMessage, setTableMessage] = useState(null);
  const listenersReady = useRef(false);
  // Nouvelles: liste des parties ouvertes
  const [openGames, setOpenGames] = useState([]);

  // Helpers
  const isInGame = !!gameId;
  const myIndex = useMemo(() => {
    if (!game || !playerId) return -1;
    return (game.players || []).findIndex(p => p.id === playerId);
  }, [game, playerId]);
  const isMyTurn = useMemo(() => myIndex >= 0 && game && game.current_player === myIndex, [myIndex, game]);
  const myCanBet = useMemo(() => {
    if (!game || myIndex < 0) return false;
    const me = game.players[myIndex] || {};
    return !!me.can_bet; // fourni par le backend
  }, [game, myIndex]);
  const myStack = useMemo(() => {
    if (!game || myIndex < 0) return 0;
    const me = game.players[myIndex] || {};
    return Number.isFinite(me.stack) ? me.stack : 0;
  }, [game, myIndex]);
  // Nom affiché: prioriser le nom du serveur (dans la partie) sinon le champ saisi
  const myName = useMemo(() => {
    if (game && myIndex >= 0) {
      const me = game.players?.[myIndex];
      if (me && me.name) return me.name;
    }
    return playerName || '';
  }, [game, myIndex, playerName]);
  const myEligibleNow = useMemo(() => {
    if (!game || myIndex < 0) return true;
    const me = game.players?.[myIndex];
    if (!me) return true;
    const hn = Number(game.hand_number || 0);
    const efh = Number(me.eligible_from_hand || 1);
    return hn === 0 || efh <= hn; // hn=0 => pas encore démarré
  }, [game, myIndex]);

  // Nouvelles dérivées: phase d'enchères uniquement sur preflop/flop/turn/river
  const isBettingPhase = useMemo(() => {
    const phase = game?.phase;
    return phase === 'preflop' || phase === 'flop' || phase === 'turn' || phase === 'river';
  }, [game]);
  const canActNow = isBettingPhase && isMyTurn && myCanBet;

  useEffect(() => {
    // Basic connection state
    const resolveEndpoint = () => {
      const envUrl = process.env.REACT_APP_SOCKET_URL;
      if (envUrl) return envUrl;
      if (typeof window !== 'undefined' && window.location && window.location.port === '5000') {
        return window.location.origin;
      }
      return 'http://localhost:5000';
    };

    const onConnect = () => { setConnected(true); setError(''); };
    const onDisconnect = () => setConnected(false);
    const onConnectError = (err) => {
      const endpoint = resolveEndpoint();
      setError(`Connexion socket échouée: ${err?.message || err || 'inconnue'}. Backend attendu: ${endpoint}`);
    };
    const onReconnect = () => setError('');
    const onReconnectAttempt = (n) => setError(`Tentative de reconnexion (#${n})...`);
    const onReconnectError = (err) => setError(`Reconnexion échouée: ${err?.message || err || 'inconnue'}`);

    socket.on('connect', onConnect);
    socket.on('disconnect', onDisconnect);
    socket.on('connect_error', onConnectError);
    socket.on('reconnect', onReconnect);
    socket.on('reconnect_attempt', onReconnectAttempt);
    socket.on('reconnect_error', onReconnectError);

    // One-time listeners
    if (!listenersReady.current) {
      listenersReady.current = true;

      socket.on('error', (payload) => {
        // Flask emits {'message': '...'}
        setError(payload?.message || 'Erreur inconnue');
      });

      socket.on('game_created', ({ game_id, player_id }) => {
        setGameId(game_id);
        setPlayerId(player_id);
        setError('');
      });

      socket.on('game_joined', ({ game_id, player_id }) => {
        setGameId(game_id);
        setPlayerId(player_id);
        setError('');
      });

      socket.on('game_started', () => {
        // Reset my hand state will be updated by 'hand_dealt'
        setMyHand([]);
        setHandResult(null);
      });

      socket.on('hand_dealt', ({ hand }) => {
        setMyHand(hand || []);
      });

      socket.on('left_game', () => {
        setGameId('');
        setGame(null);
        setMyHand([]);
        setHandResult(null);
      });

      socket.on('game_update', (gameState) => {
        setGame(gameState);
      });

      socket.on('hand_result', (result) => {
        // result: { player_id, name, amount, reason }
        setHandResult(result || null);
        // Ne pas effacer immédiatement mes cartes; elles seront réinitialisées sur 'game_started'
        // setMyHand([]);
      });

      socket.on('table_message', (payload) => {
        const text = (payload && payload.text) ? String(payload.text) : '';
        setTableMessage(text || '');
      });
    }

    return () => {
      socket.off('connect', onConnect);
      socket.off('disconnect', onDisconnect);
      socket.off('connect_error', onConnectError);
      socket.off('reconnect', onReconnect);
      socket.off('reconnect_attempt', onReconnectAttempt);
      socket.off('reconnect_error', onReconnectError);
      // Note: we keep main listeners for app lifetime
    };
  }, []);

  // Supprimer l'auto-hide du message de victoire: le message reste affiché
  // jusqu'à la prochaine main (réinitialisé par l'événement 'game_started').
  // useEffect(() => {
  //   if (!handResult) return;
  //   const t = setTimeout(() => setHandResult(null), 5000);
  //   return () => clearTimeout(t);
  // }, [handResult]);

  // Re-clamper la valeur de raise si le stack diminue (ou augmente en dessous de la valeur actuelle)
  useEffect(() => {
    setRaiseAmount(prev => {
      const clamped = Math.max(0, Math.min(prev || 0, myStack || 0));
      return clamped;
    });
  }, [myStack]);

  // Auto-hide global table message after a few seconds
  useEffect(() => {
    if (!tableMessage) return;
    const t = setTimeout(() => setTableMessage(null), 4500);
    return () => clearTimeout(t);
  }, [tableMessage]);

  // Charger périodiquement la liste des parties ouvertes
  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const res = await fetch('/api/games', { headers: { 'Accept': 'application/json' } });
        if (!res.ok) return;
        const data = await res.json();
        if (!cancelled) setOpenGames(Array.isArray(data?.games) ? data.games : []);
      } catch (_) {
        // ignorer en dev
      }
    };
    load();
    const id = setInterval(load, 7000);
    return () => { cancelled = true; clearInterval(id); };
  }, []);

  const refreshOpenGames = async () => {
    try {
      const res = await fetch('/api/games', { headers: { 'Accept': 'application/json' } });
      if (!res.ok) return;
      const data = await res.json();
      setOpenGames(Array.isArray(data?.games) ? data.games : []);
    } catch (_) {}
  };

  const createGame = (e) => {
    e.preventDefault();
    setError('');
    if (!playerName.trim()) {
      setError('Nom de joueur requis');
      return;
    }
    socket.emit('create_game', { player_name: playerName.trim() });
  };

  const joinGame = (e) => {
    e.preventDefault();
    setError('');
    if (!playerName.trim()) {
      setError('Nom de joueur requis');
      return;
    }
    if (!gameIdInput.trim()) {
      setError('ID de partie requis');
      return;
    }
    socket.emit('join_game', { player_name: playerName.trim(), game_id: gameIdInput.trim() });
  };

  const startGame = () => {
    if (!gameId) return;
    socket.emit('start_game', { game_id: gameId });
  };

  const leaveGame = () => {
    if (!gameId) return;
    socket.emit('leave_game', { game_id: gameId });
  };

  const act = (action, amount = 0) => {
    if (!gameId) return;
    // Borne l'amount à la taille du stack avant envoi
    const safeAmount = Math.max(0, Math.min(amount || 0, myStack || 0));
    socket.emit('player_action', { game_id: gameId, action, amount: safeAmount });
  };

  const prettyCard = (c) => c; // already like 'AS', 'TD', etc.

  const canCheck = () => {
    if (!game || myIndex < 0) return false;
    if (!myCanBet) return false;
    if (!isBettingPhase) return false;
    const me = game.players[myIndex];
    return (game.current_bet || 0) <= (me.current_bet || 0);
  };

  const canCall = () => {
    if (!game || myIndex < 0) return false;
    if (!myCanBet) return false;
    if (!isBettingPhase) return false;
    const me = game.players[myIndex];
    return (game.current_bet || 0) > (me.current_bet || 0);
  };

  return (
    <div className="App" style={{ maxWidth: 900, margin: '0 auto', padding: 16 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
        <h1 style={{ margin: 0 }}>Poker React + Flask</h1>
        {myName ? (
          <div style={{ fontSize: 14, color: '#555' }}>Joueur: <strong>{myName}</strong></div>
        ) : null}
      </div>
      <div style={{ marginBottom: 8 }}>Etat Socket: {connected ? 'connecté' : 'déconnecté'}</div>

      {error && (
        <div style={{ background: '#ffe6e6', padding: 8, border: '1px solid #ffcccc', marginBottom: 12 }}>
          Erreur: {error}
        </div>
      )}

      {tableMessage && (
        <div style={{ background: '#fff3cd', padding: 10, border: '1px solid #ffeeba', marginBottom: 12, color: '#856404' }}>
          {tableMessage}
        </div>
      )}

      {handResult && (
        <div style={{ background: '#e6ffe6', padding: 10, border: '1px solid #b3ffb3', marginBottom: 12 }}>
          Main terminée — Gagnant: <strong>{handResult.name || 'Inconnu'}</strong> (+{handResult.amount ?? 0})
        </div>
      )}

      {/* Lobby */}
      {!isInGame && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          <form onSubmit={createGame} style={{ border: '1px solid #ddd', padding: 12 }}>
            <h2>Créer une partie</h2>
            <div style={{ marginBottom: 8 }}>
              <label>Nom du joueur</label>
              <input
                type="text"
                value={playerName}
                onChange={(e) => setPlayerName(e.target.value)}
                placeholder="Votre nom"
                style={{ width: '100%' }}
              />
            </div>
            <button type="submit" disabled={!connected}>Créer</button>
          </form>

          <form onSubmit={joinGame} style={{ border: '1px solid #ddd', padding: 12 }}>
            <h2>Rejoindre une partie</h2>
            <div style={{ marginBottom: 8 }}>
              <label>Nom du joueur</label>
              <input
                type="text"
                value={playerName}
                onChange={(e) => setPlayerName(e.target.value)}
                placeholder="Votre nom"
                style={{ width: '100%' }}
              />
            </div>
            <div style={{ marginBottom: 8 }}>
              <label>Partie en cours</label>
              <div style={{ display: 'flex', gap: 8 }}>
                <select
                  value={gameIdInput}
                  onChange={(e) => setGameIdInput(e.target.value)}
                  style={{ flex: 1 }}
                >
                  <option value="">— Sélectionner une partie —</option>
                  {openGames.map((g) => (
                    <option key={g.id} value={g.id}>
                      {g.id} — {g.host || 'hôte ?'} — {g.connected}/{g.players} — {g.phase}
                    </option>
                  ))}
                </select>
                <button type="button" onClick={refreshOpenGames}>Actualiser</button>
              </div>
              <div style={{ color: '#888', fontSize: 12, marginTop: 4 }}>
                Sélectionner une partie ou entrer un ID manuellement ci‑dessous.
              </div>
            </div>
            <div style={{ marginBottom: 8 }}>
              <label>ID de partie</label>
              <input
                type="text"
                value={gameIdInput}
                onChange={(e) => setGameIdInput(e.target.value)}
                placeholder="ex: a1b2c3d4"
                style={{ width: '100%' }}
              />
            </div>
            <button type="submit" disabled={!connected}>Rejoindre</button>
          </form>
        </div>
      )}

      {/* In-game UI */}
      {isInGame && (
        <div style={{ border: '1px solid #ddd', padding: 12, marginTop: 12 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h2 style={{ margin: 0 }}>Partie: {gameId}</h2>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              {myName ? <div style={{ fontSize: 14, color: '#555' }}>Joueur: <strong>{myName}</strong></div> : null}
              <button onClick={leaveGame} style={{ marginRight: 8 }}>Quitter</button>
              <button onClick={startGame} disabled={!game?.can_start_new_hand}>Nouvelle main</button>
            </div>
          </div>

          <div style={{ margin: '8px 0' }}>Phase: {game?.phase}</div>
          <div style={{ margin: '8px 0' }}>Pot: {game?.pot ?? 0}</div>
          {!!game?.hand_number && (
            <div style={{ margin: '8px 0', color: '#777' }}>Main n° {game.hand_number}</div>
          )}

          {!myEligibleNow && (
            <div style={{ background: '#eef5ff', padding: 8, border: '1px solid #d6e4ff', marginBottom: 12, color: '#2f5aa8' }}>
              Vous avez rejoint en cours de main. Vous participerez à partir de la prochaine main.
            </div>
          )}

          <div style={{ margin: '8px 0' }}>
            <strong>Board:</strong>{' '}
            {(game?.community_cards || []).map((c, i) => (
              <span key={i} style={{ marginRight: 6, padding: '2px 4px', border: '1px solid #ccc' }}>
                {prettyCard(c)}
              </span>
            ))}
          </div>

          <div style={{ margin: '8px 0' }}>
            <strong>Ma main:</strong>{' '}
            {myHand.length ? (
              myHand.map((c, i) => (
                <span key={i} style={{ marginRight: 6, padding: '2px 4px', border: '1px solid #ccc' }}>
                  {prettyCard(c)}
                </span>
              ))
            ) : (
              <em>{myEligibleNow ? '(non distribuée)' : '(en attente de la prochaine main)'}</em>
            )}
          </div>

          <div style={{ marginTop: 12 }}>
            <h3>Joueurs</h3>
            <div style={{ display: 'grid', gap: 8 }}>
              {(game?.players || []).map((p, idx) => {
                const hn = Number(game?.hand_number || 0);
                const efh = Number(p?.eligible_from_hand || 1);
                const nextHandFlag = hn > 0 && efh > hn;
                return (
                  <div key={p.id} style={{
                    border: '1px solid #eee', padding: 8,
                    background: idx === game?.current_player ? '#f0fff0' : 'white'
                  }}>
                    <div>
                      <strong>{p.name}</strong> {p.id === playerId ? '(moi)' : ''}
                      {p.folded ? ' - [FOLD]' : ''}
                      {!p.connected ? ' - [déconnecté]' : ''}
                      {nextHandFlag ? ' - [prochaine main]' : (!p.can_bet ? ' - [hors mise]' : '')}
                    </div>
                    <div>Stack: {p.stack} | Mise courante: {p.current_bet}</div>
                  </div>
                );
              })}
            </div>
          </div>

          <div style={{ marginTop: 16, borderTop: '1px solid #eee', paddingTop: 12 }}>
            <h3>Actions</h3>
            {!isBettingPhase && (
              <div style={{ marginBottom: 8, color: '#888' }}>
                Vous ne pouvez pas miser hors d'une main en cours. Cliquez sur "Nouvelle main" pour distribuer.
              </div>
            )}
            {!myEligibleNow && isBettingPhase && (
              <div style={{ marginBottom: 8, color: '#888' }}>
                Vous avez rejoint en cours de main. Vous pourrez agir à la prochaine main.
              </div>
            )}
            {!(!myEligibleNow) && !myCanBet && isBettingPhase && (
              <div style={{ marginBottom: 8, color: '#888' }}>
                Vous ne pouvez pas miser dans cette main.
              </div>
            )}
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
              <button disabled={!canActNow || !canCheck() || !myEligibleNow} onClick={() => act('check')}>Check</button>
              <button disabled={!canActNow || !canCall() || !myEligibleNow} onClick={() => act('call')}>Call</button>
              <button disabled={!canActNow || !myEligibleNow} onClick={() => act('fold')}>Fold</button>
              <div>
                <input
                  type="number"
                  value={raiseAmount}
                  onChange={(e) => {
                    const raw = parseInt(e.target.value || '0', 10);
                    const clamped = Math.max(0, Math.min(raw, myStack || 0));
                    setRaiseAmount(clamped);
                  }}
                  min={0}
                  max={myStack || 0}
                  style={{ width: 100, marginRight: 8 }}
                  disabled={!canActNow || !myEligibleNow}
                />
                <button disabled={!canActNow || !myEligibleNow || (raiseAmount || 0) <= 0} onClick={() => act('raise', raiseAmount)}>Raise</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
