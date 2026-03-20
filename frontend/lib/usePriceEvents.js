/**
 * usePriceEvents — real-time price change hook via Server-Sent Events
 *
 * Connects to GET /api/events and fires a callback whenever a competitor
 * updates their price on any of the user's monitored products.
 *
 * Usage:
 *   usePriceEvents({ onEvent: (ev) => addToast(...) })
 *
 * The connection is opened only when the user is authenticated (token present)
 * and is automatically closed when the component unmounts.
 * Reconnects with exponential back-off on error (max 60s).
 */

import { useEffect, useRef } from 'react';

const BASE = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000').replace(/\/$/, '');
const MAX_BACKOFF = 60_000; // 60 seconds

export default function usePriceEvents({ onEvent, enabled = true }) {
  const esRef = useRef(null);
  const backoffRef = useRef(1000);
  const timerRef = useRef(null);

  useEffect(() => {
    if (!enabled) return;

    function connect() {
      const token =
        typeof window !== 'undefined' ? localStorage.getItem('accessToken') : null;

      if (!token) return; // not authenticated — don't connect

      // EventSource doesn't support custom headers, so we append the token
      // as a query parameter. The backend reads it from the Authorization
      // header OR from ?token= when the standard header isn't available.
      const url = `${BASE}/api/events?token=${encodeURIComponent(token)}`;
      const es = new EventSource(url);
      esRef.current = es;

      es.onopen = () => {
        backoffRef.current = 1000; // reset back-off on successful connect
      };

      es.onmessage = (e) => {
        try {
          const ev = JSON.parse(e.data);
          if (ev.type !== 'ping' && onEvent) {
            onEvent(ev);
          }
        } catch {
          // malformed event — ignore
        }
      };

      es.onerror = () => {
        es.close();
        esRef.current = null;
        // Exponential back-off reconnect
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
  }, [enabled]); // eslint-disable-line react-hooks/exhaustive-deps
}
