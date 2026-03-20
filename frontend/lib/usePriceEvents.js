/**
 * usePriceEvents - real-time price change hook via Server-Sent Events.
 *
 * Connects to GET /api/events and fires a callback whenever a competitor
 * updates their price on any of the user's monitored products.
 *
 * Usage:
 *   usePriceEvents({ onEvent: (ev) => addToast(...) })
 *
 * The connection uses the browser's secure auth cookie and reconnects
 * with exponential backoff on error (max 60s).
 */

import { useEffect, useRef } from 'react';

const BASE = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000').replace(/\/$/, '');
const MAX_BACKOFF = 60_000;

export default function usePriceEvents({ onEvent, enabled = true }) {
  const esRef = useRef(null);
  const backoffRef = useRef(1000);
  const timerRef = useRef(null);

  useEffect(() => {
    if (!enabled) return;

    function connect() {
      const es = new EventSource(`${BASE}/api/events`, { withCredentials: true });
      esRef.current = es;

      es.onopen = () => {
        backoffRef.current = 1000;
      };

      es.onmessage = (e) => {
        try {
          const ev = JSON.parse(e.data);
          if (ev.type !== 'ping' && onEvent) {
            onEvent(ev);
          }
        } catch {
          // Ignore malformed events.
        }
      };

      es.onerror = () => {
        es.close();
        esRef.current = null;
        const delay = Math.min(backoffRef.current, MAX_BACKOFF);
        backoffRef.current = Math.min(backoffRef.current * 2, MAX_BACKOFF);
        timerRef.current = setTimeout(connect, delay);
      };
    }

    connect();

    return () => {
      if (esRef.current) {
        esRef.current.close();
        esRef.current = null;
      }
      if (timerRef.current) {
        clearTimeout(timerRef.current);
      }
    };
  }, [enabled, onEvent]);
}
