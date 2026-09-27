import { useEffect, useRef, useState } from "react";

const WS_URL = import.meta.env.VITE_WS_URL || "ws://localhost:8000";

export default function useWebSocket(path, onMessage) {
  const wsRef = useRef(null);
  const onMessageRef = useRef(onMessage);
  const [connected, setConnected] = useState(false);

  // Uvek koristi najnoviji callback bez re-konektovanja
  useEffect(() => {
    onMessageRef.current = onMessage;
  }, [onMessage]);

  useEffect(() => {
    let ws;
    let reconnectTimer;
    let closedByUser = false;

    const connect = () => {
      ws = new WebSocket(`${WS_URL}${path}`);
      wsRef.current = ws;

      ws.onopen = () => setConnected(true);
      ws.onclose = () => {
        setConnected(false);
        if (!closedByUser) {
          // Automatski reconnect za 2 sekunde
          reconnectTimer = setTimeout(connect, 2000);
        }
      };
      ws.onerror = () => setConnected(false);
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          onMessageRef.current?.(data);
        } catch (e) {
          console.error("WS parse error", e);
        }
      };
    };

    connect();

    return () => {
      closedByUser = true;
      clearTimeout(reconnectTimer);
      ws?.close();
    };
  }, [path]);

  return { connected, ws: wsRef.current };
}
