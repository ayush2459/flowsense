const WS_BASE = "ws://localhost:8000";

export function connectAllFacilities({
  onMessage,
  onStatus,
  onError
} = {}) {
  let socket = null;
  let reconnectTimer = null;
  let stopped = false;
  let reconnectDelay = 1000;

  const cleanupSocket = () => {
    if (!socket) return;

    socket.onopen = null;
    socket.onmessage = null;
    socket.onerror = null;
    socket.onclose = null;

    if (
      socket.readyState === WebSocket.OPEN ||
      socket.readyState === WebSocket.CONNECTING
    ) {
      try {
        socket.close(1000, "Dashboard cleanup");
      } catch {
        // Ignore cleanup errors.
      }
    }

    socket = null;
  };

  const scheduleReconnect = () => {
    if (stopped || reconnectTimer) return;

    reconnectTimer = setTimeout(() => {
      reconnectTimer = null;

      if (!stopped) {
        connect();
      }
    }, reconnectDelay);

    reconnectDelay = Math.min(
      reconnectDelay * 2,
      5000
    );
  };

  const connect = () => {
    if (stopped) return;

    if (
      socket &&
      (
        socket.readyState === WebSocket.OPEN ||
        socket.readyState === WebSocket.CONNECTING
      )
    ) {
      return;
    }

    const url = `${WS_BASE}/ws/live/all`;

    console.log("[Realtime] Connecting:", url);

    onStatus?.("connecting");

    try {
      socket = new WebSocket(url);
    } catch (error) {
      console.error(
        "[Realtime] WebSocket construction failed:",
        error
      );

      onError?.(error);
      scheduleReconnect();
      return;
    }

    socket.onopen = () => {
      if (stopped) {
        cleanupSocket();
        return;
      }

      reconnectDelay = 1000;

      console.log(
        "[Realtime] Connected to all facilities"
      );

      onStatus?.("live");
    };

    socket.onmessage = (event) => {
      if (stopped) return;

      try {
        const message = JSON.parse(
          event.data
        );

        if (
          message.type === "heartbeat" ||
          message.type === "pong"
        ) {
          return;
        }

        if (
          message.type === "telemetry"
        ) {
          onMessage?.(message);
        }
      } catch (error) {
        console.error(
          "[Realtime] Invalid message:",
          error
        );

        onError?.(error);
      }
    };

    socket.onerror = (event) => {
      if (stopped) return;

      console.error(
        "[Realtime] WebSocket error:",
        event
      );

      onError?.(event);
    };

    socket.onclose = (event) => {
      console.log(
        `[Realtime] WebSocket closed: code=${event.code}, reason=${event.reason || "none"}`
      );

      socket = null;

      if (stopped) return;

      onStatus?.("reconnecting");
      scheduleReconnect();
    };
  };

  connect();

  return () => {
    stopped = true;

    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }

    cleanupSocket();
  };
}