"use client";

import { useEffect, useRef, useState } from "react";

import type { Paginated } from "@/types/api";

/** Paginated list state for the admin tables. `filterKey` should encode the
 * current filters — changing it resets to page 1 and refetches. */
export function usePaged<T>(
  fetcher: (page: number) => Promise<Paginated<T>>,
  filterKey: string
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
    setLoading(true);
    setError("");
    fetcherRef
      .current(page)
      .then((d) => !cancelled && setData(d))
      .catch(() => !cancelled && setError("Could not load data."))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [page, filterKey]);

  return { data, page, setPage, loading, error };
}
