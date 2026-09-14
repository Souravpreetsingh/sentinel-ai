import { useCallback, useEffect, useState } from 'react';
import { sentinelWS, EVENT_TYPES } from '../services/websocket';

export function useWebSocket() {
  const [connected, setConnected] = useState(sentinelWS.connected);
  const [lastEvent, setLastEvent] = useState(null);

  const subscribe = useCallback(
    (eventType, callback) => sentinelWS.subscribe(eventType, callback),
    []
  );

  useEffect(() => {
    const offConnection = sentinelWS.onConnectionChange((isConnected) => {
      setConnected(isConnected);
    });

    const eventTypes = Object.values(EVENT_TYPES);
    const handlers = eventTypes.map((eventType) => {
      const handler = (data) => {
        setLastEvent({
          type: eventType,
          data,
          receivedAt: Date.now(),
        });
      };
      sentinelWS.subscribe(eventType, handler);
      return handler;
    });

    sentinelWS.connect();

    return () => {
      sentinelWS.disconnect();
      eventTypes.forEach((eventType, index) => {
        sentinelWS.unsubscribe(eventType, handlers[index]);
      });
      offConnection();
    };
  }, []);

  return { connected, lastEvent, subscribe };
}