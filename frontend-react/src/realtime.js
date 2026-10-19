
const API_BASE =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const WS_BASE = API_BASE
  .replace(/^https:/i, "wss:")
  .replace(/^http:/i, "ws:")
  .replace(/\/+$/, "");

export function connectAllFacilities({
  onMessage,
  onStatus,
  onError,
} = {}) {
  let socket = null;
  let reconnectTimer = null;
  let startTimer = null;
  let stopped = false;
  let reconnectDelay = 1000;

  const MIN_RECONNECT_DELAY = 1000;
  const MAX_RECONNECT_DELAY = 10000;

  const clearStartTimer = () => {
    if (startTimer !== null) {
      clearTimeout(startTimer);
      startTimer = null;
    }
  };

  const clearReconnectTimer = () => {
    if (reconnectTimer !== null) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
  };

  const cleanupSocket = (target = socket) => {
    if (!target) return;

    // Detach callbacks before closing to avoid cleanup-triggered
    // reconnects and stale state updates.
    target.onopen = null;
    target.onmessage = null;
    target.onerror = null;
    target.onclose = null;

    if (
      target.readyState === WebSocket.CONNECTING ||
      target.readyState === WebSocket.OPEN
    ) {
      try {
        target.close(1000, "Dashboard cleanup");
      } catch {
        // Ignore socket cleanup errors.
      }
    }

    if (socket === target) {
      socket = null;
    }
  };

  const scheduleReconnect = () => {
    if (stopped || reconnectTimer !== null) return;

    const delay = reconnectDelay;

    reconnectTimer = setTimeout(() => {
      reconnectTimer = null;

      if (!stopped) {
        connect();
      }
    }, delay);

    reconnectDelay = Math.min(
      reconnectDelay * 2,
      MAX_RECONNECT_DELAY
    );
  };

  const connect = () => {
    if (stopped) return;

    if (
      socket &&
      (
        socket.readyState === WebSocket.CONNECTING ||
        socket.readyState === WebSocket.OPEN
      )
    ) {
      return;
    }

    const url = `${WS_BASE}/ws/live/all`;

    console.log("[Realtime] Connecting:", url);
    onStatus?.("connecting");

    let nextSocket;

    try {
      nextSocket = new WebSocket(url);
      socket = nextSocket;
    } catch (error) {
      console.error(
        "[Realtime] WebSocket construction failed:",
        error
      );

      onError?.(error);
      onStatus?.("reconnecting");
      scheduleReconnect();
      return;
    }

    nextSocket.onopen = () => {
      // Ignore callbacks from an old or stopped connection.
      if (stopped || socket !== nextSocket) {
        cleanupSocket(nextSocket);
        return;
      }

      reconnectDelay = MIN_RECONNECT_DELAY;

      console.log("[Realtime] Connected to all facilities");
      onStatus?.("live");
    };

    nextSocket.onmessage = (event) => {
      if (stopped || socket !== nextSocket) return;

      try {
        const message = JSON.parse(event.data);

        // Ignore server heartbeat messages.
        if (
          message?.type === "heartbeat" ||
          message?.type === "pong"
        ) {
          return;
        }

        if (message?.type === "telemetry") {
          if (message?.resource_discrepancy) {
          window.dispatchEvent(new CustomEvent('flowsense:resource-discrepancy', { detail: message.resource_discrepancy }));
        }
        const discrepancyReport =
            message.resource_discrepancy ??
            message.data?.resource_discrepancy ??
            message.detection?.resource_discrepancy;
          if (discrepancyReport) {
            window.dispatchEvent(new CustomEvent("flowsense:resource-discrepancy", {
              detail: {
                ...discrepancyReport,
                facility_code: message.facility_code ?? message.data?.facility_code ?? discrepancyReport.facility_code,
                facility_name: message.facility_name ?? message.data?.facility_name ?? discrepancyReport.facility_name,
                timestamp: message.timestamp ?? discrepancyReport.timestamp
              }
            }));
          }
          onMessage?.(message);
        }
      } catch (error) {
        console.error("[Realtime] Invalid message:", error);
        onError?.(error);
      }
    };

    nextSocket.onerror = (event) => {
      if (stopped || socket !== nextSocket) return;

      console.error("[Realtime] WebSocket error:", event);
      onError?.(event);

      // Let onclose schedule a single reconnect.
    };

    nextSocket.onclose = (event) => {
      // Ignore close events belonging to replaced sockets.
      if (socket !== nextSocket) return;

      socket = null;

      console.log(
        `[Realtime] WebSocket closed: code=${event.code}, reason=${event.reason || "none"}`
      );

      if (stopped) return;

      onStatus?.("reconnecting");
      scheduleReconnect();
    };
  };

  // Defer startup so React Strict Mode's immediate development
  // cleanup can cancel the initial connection.
  startTimer = setTimeout(() => {
    startTimer = null;

    if (!stopped) {
      connect();
    }
  }, 0);

  return () => {
    if (stopped) return;

    stopped = true;

    clearStartTimer();
    clearReconnectTimer();
    cleanupSocket();
  };
}


