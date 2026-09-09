const WS_BASE = "ws://127.0.0.1:8000";

export function connectAllFacilities({ onMessage, onStatus, onError } = {}) {
  let socket = null;
  let reconnectTimer = null;
  let stopped = false;

  const connect = () => {
    if (stopped) return;

    onStatus?.("connecting");
    socket = new WebSocket(`${WS_BASE}/ws/live/all`);

    socket.onopen = () => {
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

    socket.onerror = (error) => {
      console.error("[Realtime] WebSocket error:", error);
      onError?.(error);
    };

    socket.onclose = () => {
      if (stopped) return;
      onStatus?.("reconnecting");
      reconnectTimer = setTimeout(connect, 2000);
    };
  };

  connect();

  return () => {
    stopped = true;
    if (reconnectTimer) clearTimeout(reconnectTimer);
    if (socket) socket.close();
  };
}
