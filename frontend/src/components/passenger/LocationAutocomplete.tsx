"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { Input } from "@/components/ui/Input";
import * as geoApi from "@/lib/api/geo";
import type { GeoSuggestion } from "@/lib/api/geo";
import type { LocationField } from "@/lib/location";

const DEBOUNCE_MS = 220;
const MIN_CHARS = 2;

type UiState =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "results"; items: GeoSuggestion[] }
  | { kind: "empty" }
  | { kind: "error" };

/** Address input with real Mapbox (Yola-biased) suggestions.
 *
 * Owns nothing except the search UI — the LocationField state is lifted
 * to the parent so the form can distinguish gps / suggestion / typed. */
export function LocationAutocomplete({
  label,
  placeholder,
  value,
  onChange,
  proximity,
  required,
  disabled,
  extra,
}: {
  label: string;
  placeholder?: string;
  value: LocationField;
  onChange: (next: LocationField) => void;
  /** Live GPS coords (rider's location) — forwarded to bias results. */
  proximity?: { lat: string; lng: string } | null;
  required?: boolean;
  disabled?: boolean;
  extra?: React.ReactNode;
}) {
  const [ui, setUi] = useState<UiState>({ kind: "idle" });
  const [open, setOpen] = useState(false);
  // Don't refire the query on the exact string we just filled from a pick.
  const suppressForRef = useRef<string | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (suppressForRef.current === value.label) return;
    if (value.label.trim().length < MIN_CHARS) {
      setUi({ kind: "idle" });
      setOpen(false);
      return;
    }

    let cancelled = false;
    setUi({ kind: "loading" });
    setOpen(true);

    const timer = setTimeout(async () => {
      try {
        const data = await geoApi.suggest(value.label, 6, proximity ?? null);
        if (cancelled) return;
        // Deduplicate on the fuller address AND label; keep first occurrence.
        const seenAddress = new Set<string>();
        const seenLabel = new Set<string>();
        const items = data.results.filter((s) => {
          const addr = (s.address || s.label).toLowerCase();
          const label = s.label.toLowerCase();
          if (seenAddress.has(addr) || seenLabel.has(label)) return false;
          seenAddress.add(addr);
          seenLabel.add(label);
          return true;
        });
        setUi(items.length ? { kind: "results", items } : { kind: "empty" });
      } catch {
        if (!cancelled) setUi({ kind: "error" });
      }
    }, DEBOUNCE_MS);

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [value.label]);

  useEffect(() => {
    function onDown(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    window.addEventListener("mousedown", onDown);
    return () => window.removeEventListener("mousedown", onDown);
  }, []);

  function pick(item: GeoSuggestion) {
    suppressForRef.current = item.address;
    onChange({
      label: item.address,
      address: item.address,
      place_name: item.place_name || item.address,
      place_type: item.place_type ? [item.place_type] : [],
      lat: item.lat,
      lng: item.lng,
      source: "suggestion",
    });
    setOpen(false);
    setUi({ kind: "idle" });
  }

  function handleTyping(next: string) {
    suppressForRef.current = null;
    if (value.source && value.source !== "typed") {
      // User edited a GPS/suggestion result -> stored coords are stale
      onChange({ label: next, source: next ? "typed" : null });
    } else {
      onChange({ ...value, label: next, source: next ? "typed" : null });
    }
  }

  const dropdown = useMemo(() => {
    switch (ui.kind) {
      case "loading":
        return <li className="px-3 py-2 text-xs text-gray-500">Searching Yola…</li>;
      case "empty":
        return (
          <li className="px-3 py-2 text-xs text-gray-500">
            No matches. Press <span className="font-semibold">Get fare estimate</span> to search
            anyway.
          </li>
        );
      case "error":
        return (
          <li className="px-3 py-2 text-xs text-red-600">
            Address search is unavailable right now — you can still type freely.
          </li>
        );
      case "results":
        return ui.items.map((item, index) => (
          <li key={`${item.address}-${index}`}>
            <button
              type="button"
              onMouseDown={(e) => {
                e.preventDefault();
                pick(item);
              }}
              className="block w-full px-3 py-2 text-left text-sm hover:bg-emerald-50"
              role="option"
              aria-selected="false"
            >
              <p className="font-medium text-gray-900">{item.label}</p>
              {item.address && item.address !== item.label && (
                <p className="text-xs text-gray-500">{item.address}</p>
              )}
            </button>
          </li>
        ));
      default:
        return null;
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ui]);

  return (
    <div ref={containerRef} className="relative">
      <Input
        label={label}
        placeholder={placeholder}
        value={value.label}
        onChange={(e) => handleTyping(e.target.value)}
        onFocus={() => ui.kind !== "idle" && setOpen(true)}
        autoComplete="off"
        required={required}
        disabled={disabled}
      />
      {extra}
      {open && ui.kind !== "idle" && (
        <ul
          className="absolute z-20 mt-1 max-h-64 w-full overflow-auto rounded-lg border border-gray-200 bg-white shadow-lg"
          role="listbox"
        >
          {dropdown}
        </ul>
      )}
    </div>
  );
}
