import { useEffect, useRef } from "react";

/**
 * Memanggil callback berulang untuk pembaruan semi-real-time (polling).
 */
export function usePolling(callback, intervalMs = 2000, enabled = true) {
  const callbackRef = useRef(callback);
  callbackRef.current = callback;

  useEffect(() => {
    if (!enabled) return undefined;

    const jalankan = () => {
      Promise.resolve(callbackRef.current()).catch(() => {});
    };

    jalankan();
    const timerId = window.setInterval(jalankan, intervalMs);
    return () => window.clearInterval(timerId);
  }, [intervalMs, enabled]);
}
