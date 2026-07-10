"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { flushSync } from "react-dom";

import { LocationAutocomplete } from "@/components/passenger/LocationAutocomplete";
import { RideRoute } from "@/components/ride/RideRoute";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ApiError } from "@/lib/api/client";
import * as geoApi from "@/lib/api/geo";
import * as ridesApi from "@/lib/api/rides";
import {
  formatDistance,
  formatDuration,
  formatNaira,
  PAYMENT_METHOD_LABELS,
  VEHICLE_CATEGORY_ICONS,
  VEHICLE_CATEGORY_IMAGES,
  VEHICLE_CATEGORY_LABELS,
} from "@/lib/format";
import {
  distanceFromYolaKm,
  EMPTY_LOCATION,
  toApiLocation,
  YOLA_SERVICE_RADIUS_KM,
  type LocationField,
} from "@/lib/location";
import type { Estimate, PaymentMethod, VehicleCategory } from "@/types/api";

const CATEGORIES: VehicleCategory[] = ["KEKE", "CAR"];

export function BookRideForm({ defaultPaymentMethod }: { defaultPaymentMethod: PaymentMethod }) {
  const router = useRouter();

  const [category, setCategory] = useState<VehicleCategory>("CAR");
  const [pickup, setPickup] = useState<LocationField>(EMPTY_LOCATION);
  const [dropoff, setDropoff] = useState<LocationField>(EMPTY_LOCATION);
  const [method, setMethod] = useState<PaymentMethod>(defaultPaymentMethod);
  const [estimate, setEstimate] = useState<Estimate | null>(null);
  const [busy, setBusy] = useState<"idle" | "estimating" | "requesting">("idle");
  const [error, setError] = useState("");
  const [hasActiveRide, setHasActiveRide] = useState(false);
  const [locating, setLocating] = useState(false);

  async function useMyLocation() {
    if (!navigator.geolocation) {
      setError("Location is not available in this browser.");
      return;
    }
    setLocating(true);
    setError("");
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const latNum = pos.coords.latitude;
        const lngNum = pos.coords.longitude;
        // Sanity check: if the browser is falling back to IP-based
        // geolocation, we can land hundreds of km from Yola. Reject that
        // rather than silently pinning the passenger to another city.
        const distKm = distanceFromYolaKm(latNum, lngNum);
        if (distKm > YOLA_SERVICE_RADIUS_KM) {
          flushSync(() => {
            setLocating(false);
            setError(
              `We got a location about ${Math.round(distKm)} km from Yola. This usually means precise location is off in Windows/Chrome, so the browser is guessing from your ISP. Type your pickup below, or enable precise location and try again.`
            );
          });
          // Focus the pickup input so the user is ready to type without extra clicks
          document.getElementById("pickup")?.focus();
          return;
        }
        const lat = latNum.toFixed(6);
        const lng = lngNum.toFixed(6);
        let label = "Current location";
        let address: string | undefined;
        try {
          const res = await geoApi.reverseGeocode(lat, lng);
          if (res.address) {
            label = res.address;
            address = res.address;
          }
        } catch {
          /* keep default label; coords still drive fare math */
        }
        setPickup({ label, address, lat, lng, source: "gps" });
        setLocating(false);
      },
      (err) => {
        setLocating(false);
        setError(
          err.code === err.PERMISSION_DENIED
            ? "Location permission denied — please type your pickup address."
            : err.code === err.TIMEOUT
              ? "Your device took too long to find GPS. Please type your pickup address."
              : "Could not get your location — type your pickup address instead."
        );
      },
      // Force real GPS instead of cached / IP-based positioning.
      { enableHighAccuracy: true, maximumAge: 0, timeout: 15_000 }
    );
  }

  async function getEstimate(e: FormEvent) {
    e.preventDefault();
    setError("");
    setBusy("estimating");
    try {
      // Coordinates always win when we have them; toApiLocation encapsulates it.
      const result = await ridesApi.estimate(
        category,
        toApiLocation(pickup),
        toApiLocation(dropoff)
      );
      setEstimate(result);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not get an estimate. Try again.");
    } finally {
      setBusy("idle");
    }
  }

  async function requestRide() {
    if (!estimate) return;
    setError("");
    setBusy("requesting");
    try {
      await ridesApi.createRide({
        vehicle_category: estimate.vehicle_category,
        pickup: { address: estimate.pickup.address, lat: estimate.pickup.lat, lng: estimate.pickup.lng },
        dropoff: {
          address: estimate.dropoff.address,
          lat: estimate.dropoff.lat,
          lng: estimate.dropoff.lng,
        },
        payment_method: method,
      });
      router.push("/passenger/ride");
    } catch (err) {
      if (err instanceof ApiError && err.message.toLowerCase().includes("active ride")) {
        setHasActiveRide(true);
      }
      setError(err instanceof ApiError ? err.message : "Could not request the ride. Try again.");
      setBusy("idle");
    }
  }

  if (estimate) {
    return (
      <Card className="space-y-4">
        <h3 className="font-semibold text-gray-900">Your fare estimate</h3>
        <RideRoute pickup={estimate.pickup.address} dropoff={estimate.dropoff.address} />
        <div className="flex items-end justify-between rounded-lg bg-emerald-50 p-3">
          <div>
            <p className="text-xs text-emerald-700">
              {VEHICLE_CATEGORY_ICONS[estimate.vehicle_category]}{" "}
              {VEHICLE_CATEGORY_LABELS[estimate.vehicle_category]} ride ·{" "}
              {formatDistance(estimate.distance_m)} · about {formatDuration(estimate.duration_s)}
            </p>
            <p className="text-3xl font-extrabold text-emerald-700">
              {formatNaira(estimate.fare)}
            </p>
          </div>
        </div>
        <div>
          <p className="mb-2 text-sm font-medium text-gray-700">How will you pay?</p>
          <div className="grid grid-cols-2 gap-2">
            {(Object.keys(PAYMENT_METHOD_LABELS) as PaymentMethod[]).map((m) => (
              <button
                key={m}
                type="button"
                onClick={() => setMethod(m)}
                className={`rounded-lg border px-3 py-2.5 text-sm font-semibold ${
                  method === m
                    ? "border-emerald-600 bg-emerald-50 text-emerald-700"
                    : "border-gray-300 bg-white text-gray-700"
                }`}
              >
                {PAYMENT_METHOD_LABELS[m]}
              </button>
            ))}
          </div>
        </div>
        {error && (
          <Alert tone="error">
            {error}{" "}
            {hasActiveRide && (
              <Link href="/passenger/ride" className="font-semibold underline">
                Go to your active ride
              </Link>
            )}
          </Alert>
        )}
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => setEstimate(null)} className="flex-1">
            Edit
          </Button>
          <Button
            onClick={requestRide}
            loading={busy === "requesting"}
            className="flex-[2]"
          >
            Request ride · {formatNaira(estimate.fare)}
          </Button>
        </div>
      </Card>
    );
  }

  return (
    <Card>
      <h3 className="mb-3 font-semibold text-gray-900">Where are you going?</h3>
      <form onSubmit={getEstimate} className="space-y-4">
        {error && (
          <Alert tone="error" onDismiss={() => setError("")}>
            {error}
          </Alert>
        )}
        <div>
          <p className="mb-2 text-sm font-medium text-gray-700">Ride type</p>
          <div className="grid grid-cols-2 gap-3">
            {CATEGORIES.map((c) => (
              <button
                key={c}
                type="button"
                onClick={() => setCategory(c)}
                aria-pressed={category === c}
                className={`flex flex-col items-center gap-1 rounded-xl border-2 p-2 text-sm font-semibold transition-colors ${
                  category === c
                    ? "border-emerald-600 bg-emerald-50 text-emerald-700"
                    : "border-gray-200 bg-white text-gray-700 hover:border-gray-300"
                }`}
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={VEHICLE_CATEGORY_IMAGES[c]}
                  alt={`${VEHICLE_CATEGORY_LABELS[c]} ride`}
                  className="h-20 w-full rounded-lg object-contain"
                />
                {VEHICLE_CATEGORY_LABELS[c]}
              </button>
            ))}
          </div>
        </div>
        <LocationAutocomplete
          label="Pickup"
          placeholder="e.g. Jimeta, Jambutu, AUN, FMC…"
          value={pickup}
          onChange={(next) => {
            setPickup(next);
            // Any active input from the user clears a stale GPS/error alert
            if (error) setError("");
          }}
          required
          extra={
            <div className="mt-1 flex items-center justify-between gap-2">
              <button
                type="button"
                onClick={useMyLocation}
                className="text-xs font-semibold text-emerald-600 hover:underline"
              >
                {locating ? "Locating…" : "📍 Use my current location"}
              </button>
              {pickup.source === "gps" && (
                <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] font-semibold text-emerald-700">
                  <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-500" aria-hidden />
                  Using your current location
                </span>
              )}
            </div>
          }
        />
        <LocationAutocomplete
          label="Destination"
          placeholder="e.g. AUN, FMC Yola, Modibbo Adama University"
          value={dropoff}
          onChange={(next) => {
            setDropoff(next);
            if (error) setError("");
          }}
          proximity={
            pickup.source === "gps" && pickup.lat && pickup.lng
              ? { lat: pickup.lat, lng: pickup.lng }
              : null
          }
          required
        />
        <Button type="submit" fullWidth loading={busy === "estimating"}>
          Get fare estimate
        </Button>
      </form>
    </Card>
  );
}
