"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { apiPath } from "@/lib/basePath";

/**
 * Client-side fetching for the scanner-backed views.
 *
 * Three behaviours here exist because of how these panels are actually used:
 *
 *  * **Filter changes must not race.** Clicking through Radar filters quickly issues
 *    overlapping requests, and without sequencing a slow earlier response can land
 *    after a fast later one and repaint stale rows. Each request carries a sequence
 *    number and only the newest is allowed to commit.
 *  * **Refetching must not blank the screen.** `loading` is only true on the first
 *    load; subsequent fetches keep the previous rows visible so the list does not
 *    flash empty every time a chip is toggled.
 *  * **Unreachable is a state, not an exception.** The BFF always answers with a
 *    well-formed payload carrying `degraded`, so there is no throw path to handle.
 */

export interface ScoutFetchState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useScoutData<T>(path: string | null): ScoutFetchState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [nonce, setNonce] = useState(0);

  // Guards against out-of-order responses repainting the list.
  const sequence = useRef(0);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  useEffect(() => {
    if (!path) return;
    const mine = ++sequence.current;
    const controller = new AbortController();

    // Only show a spinner when there is nothing to show instead.
    setLoading((prev) => (data === null ? true : prev));
    setError(null);

    fetch(apiPath(path), { signal: controller.signal, cache: "no-store" })
      .then(async (res) => {
        if (res.status === 401) throw new Error("Your session has expired. Please sign in again.");
        if (!res.ok) throw new Error(`Request failed (${res.status})`);
        return (await res.json()) as T;
      })
      .then((payload) => {
        if (!mounted.current || mine !== sequence.current) return;
        setData(payload);
        setLoading(false);
      })
      .catch((e: unknown) => {
        if (!mounted.current || mine !== sequence.current) return;
        if (e instanceof DOMException && e.name === "AbortError") return;
        setError(e instanceof Error ? e.message : String(e));
        setLoading(false);
      });

    return () => controller.abort();
    // `data` is intentionally omitted: including it would refetch on every commit.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, nonce]);

  const refetch = useCallback(() => setNonce((n) => n + 1), []);
  return { data, loading, error, refetch };
}

/** POST helper for the action buttons (rescan, dismiss, send test). */
export function useScoutAction() {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(
    async (path: string, init?: RequestInit): Promise<Record<string, unknown> | null> => {
      setPending(true);
      setError(null);
      try {
        const res = await fetch(apiPath(path), {
          method: "POST",
          cache: "no-store",
          ...init,
        });
        const body = await res.json().catch(() => ({}));
        if (!res.ok) {
          throw new Error(body?.reason || body?.error || `Request failed (${res.status})`);
        }
        return body;
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
        return null;
      } finally {
        setPending(false);
      }
    },
    []
  );

  return { run, pending, error };
}
