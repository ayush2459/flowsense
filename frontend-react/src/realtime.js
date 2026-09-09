const WS_BASE = `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.host.replace(/:\d+$/, ":8000")}`;

export function connectAllFacilities({ onMessage, onStatus, onError } = {}) {
  let socket = null;
  let reconnectTimer = null;
  let stopped = false;
  let reconnectDelay = 1000;

  const connect = () => {
    if (stopped) return;

    onStatus?.("connecting");

    try {
      socket = new WebSocket(`${WS_BASE}/ws/live/all`);
    } catch (error) {
      onError?.(error);
      scheduleReconnect();
      return;
    }

    socket.onopen = () => {
      reconnectDelay = 1000;
      console.log("[Realtime] Connected to all facilities");
      onStatus?.("live");
    };

    socket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        if (message.type === "heartbeat" || message.type === "pong") return;
        if (message.type === "telemetry") onMessage?.(message);
      } catch (error) {
        console.error("[Realtime] Invalid message:", error);
        onError?.(error);
      }
    };

    socket.onerror = () => {
      // Browser WebSocket errors contain little useful detail. The close
      // handler below performs the reconnect and updates the UI state.
      onStatus?.("reconnecting");
    };

    socket.onclose = () => {
      if (stopped) return;
      onStatus?.("reconnecting");
      scheduleReconnect();
    };
  };

  const scheduleReconnect = () => {
    if (stopped || reconnectTimer) return;
    reconnectTimer = setTimeout(() => {
      reconnectTimer = null;
      connect();
    }, reconnectDelay);
    reconnectDelay = Math.min(reconnectDelay * 2, 5000);
  };

  connect();

  return () => {
    stopped = true;
    if (reconnectTimer) clearTimeout(reconnectTimer);
    reconnectTimer = null;
    if (socket && socket.readyState === WebSocket.OPEN) socket.close(1000, "Dashboard closed");
    socket = null;
  };
}
