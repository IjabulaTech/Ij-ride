"use client";

import { useEffect, useRef, useState } from "react";

import type { Paginated } from "@/types/api";

/** Paginated list state for the admin tables. `filterKey` should encode the
 * current filters — changing it resets to page 1 and refetches. Pass `pollMs`
 * to silently re-fetch the current page on an interval (live updating). */
export function usePaged<T>(
  fetcher: (page: number) => Promise<Paginated<T>>,
  filterKey: string,
  pollMs?: number
) {
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  const [page, setPage] = useState(1);
  const [data, setData] = useState<Paginated<T> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    setPage(1);
  }, [filterKey]);

  useEffect(() => {
    let cancelled = false;
    // Only the first load of a page/filter shows the spinner; background polls
    // refresh data in place without flashing the loading state.
    const fetchPage = (background: boolean) => {
      if (!background) setLoading(true);
      setError("");
      fetcherRef
        .current(page)
        .then((d) => !cancelled && setData(d))
        .catch(() => !cancelled && !background && setError("Could not load data."))
        .finally(() => !cancelled && !background && setLoading(false));
    };

    fetchPage(false);
    if (!pollMs) return () => {
      cancelled = true;
    };
    const timer = setInterval(() => fetchPage(true), pollMs);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [page, filterKey, pollMs]);

  return { data, page, setPage, loading, error };
}
