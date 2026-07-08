"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { RequestCard } from "@/components/driver/RequestCard";
import { RideRoute } from "@/components/ride/RideRoute";
import { RideStatusBadge } from "@/components/ride/RideStatusBadge";
import { Alert } from "@/components/ui/Alert";
import { approvalStatusTone, Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { ApiError } from "@/lib/api/client";
import * as driverApi from "@/lib/api/driver";
import { acceptRide, activeRide, openRides, rejectRide } from "@/lib/api/rides";
import { useRideSocket } from "@/lib/hooks/useRideSocket";
import type { DriverAvailability, DriverProfile, OpenRide, Ride, Vehicle } from "@/types/api";

export default function DriverDashboard() {
  const router = useRouter();

  const [profile, setProfile] = useState<DriverProfile | null>(null);
  const [vehicle, setVehicle] = useState<Vehicle | null>(null);
  const [availability, setAvailability] = useState<DriverAvailability | null>(null);
  const [trip, setTrip] = useState<Ride | null>(null);
  const [requests, setRequests] = useState<OpenRide[]>([]);
  const [loading, setLoading] = useState(true);
  const [toggleBusy, setToggleBusy] = useState(false);
  const [acceptBusyId, setAcceptBusyId] = useState<number | null>(null);
  const [error, setError] = useState("");

  const isOnline = availability?.is_online ?? false;
  const onlineRef = useRef(isOnline);
  onlineRef.current = isOnline;

  const refreshOpen = useCallback(async () => {
    try {
      const data = await openRides();
      setRequests(data.results);
    } catch {
      /* fallback poll retries */
    }
  }, []);

  // Initial load
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [p, v, a, t] = await Promise.all([
          driverApi.getProfile(),
          driverApi.getVehicle(),
          driverApi.getAvailability(),
          activeRide(),
        ]);
        if (cancelled) return;
        setProfile(p);
        setVehicle(v);
        setAvailability(a);
        setTrip(t);
        if (a.is_online && !t) await refreshOpen();
      } catch {
        if (!cancelled) setError("Could not load your driver profile.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [refreshOpen]);

  // Realtime dispatch feed
  const socketRef = useRideSocket((message) => {
    if (message.type === "dispatch.new_request") {
      setRequests((prev) =>
        prev.some((r) => r.id === message.ride.id) ? prev : [...prev, message.ride]
      );
    } else if (message.type === "dispatch.request_closed") {
      setRequests((prev) => prev.filter((r) => r.id !== message.ride_id));
    } else if (message.type === "connection.ready" && message.dispatch) {
      refreshOpen();
    }
  });

  // Poll fallback while online without an active trip
  useEffect(() => {
    if (!isOnline || trip) return;
    const timer = setInterval(refreshOpen, 20_000);
    return () => clearInterval(timer);
  }, [isOnline, trip, refreshOpen]);

  // Best-effort location pings while online
  useEffect(() => {
    if (!isOnline || typeof navigator === "undefined" || !navigator.geolocation) return;
    const ping = () =>
      navigator.geolocation.getCurrentPosition(
        (pos) =>
          driverApi
            .updateLocation(pos.coords.latitude.toFixed(6), pos.coords.longitude.toFixed(6))
            .catch(() => undefined),
        () => undefined
      );
    ping();
    const timer = setInterval(ping, 60_000);
    return () => clearInterval(timer);
  }, [isOnline]);

  async function toggleOnline() {
    setToggleBusy(true);
    setError("");
    try {
      const next = !isOnline;
      const a = await driverApi.setAvailability(next);
      setAvailability(a);
      if (next) {
        socketRef.current?.subscribeDispatch();
        await refreshOpen();
      } else {
        socketRef.current?.unsubscribeDispatch();
        setRequests([]);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not update your status.");
    } finally {
      setToggleBusy(false);
    }
  }

  async function accept(id: number) {
    setAcceptBusyId(id);
    setError("");
    try {
      await acceptRide(id);
      router.push("/driver/trip");
    } catch (err) {
      setRequests((prev) => prev.filter((r) => r.id !== id));
      setError(err instanceof ApiError ? err.message : "Could not accept this ride.");
      setAcceptBusyId(null);
    }
  }

  async function dismiss(id: number) {
    setRequests((prev) => prev.filter((r) => r.id !== id));
    rejectRide(id).catch(() => undefined);
  }

  if (loading) {
    return (
      <div className="flex justify-center py-16 text-emerald-600">
        <Spinner size="lg" />
      </div>
    );
  }
  if (!profile) return <Alert tone="error">{error || "Could not load your profile."}</Alert>;

  // ---- approval gates ----
  if (profile.approval_status !== "APPROVED") {
    return (
      <div className="space-y-4">
        <Card className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-gray-900">Driver status</h2>
            <Badge tone={approvalStatusTone(profile.approval_status)}>
              {profile.approval_status}
            </Badge>
          </div>
          {profile.approval_status === "PENDING" ? (
            <p className="text-sm text-gray-600">
              Your account is awaiting admin approval. Completing your profile and vehicle
              details helps it go faster.
            </p>
          ) : (
            <Alert tone="error">
              Your application was rejected
              {profile.approval_note ? `: ${profile.approval_note}` : "."} Update your details to
              be reviewed again.
            </Alert>
          )}
          <Link href="/driver/onboarding" className="block">
            <Button fullWidth>Complete your profile</Button>
          </Link>
        </Card>
      </div>
    );
  }

  // ---- active trip shortcut ----
  if (trip) {
    return (
      <Card className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold text-gray-900">Trip in progress</h2>
          <RideStatusBadge status={trip.status} />
        </div>
        <RideRoute pickup={trip.pickup_address} dropoff={trip.dropoff_address} />
        <Link href="/driver/trip" className="block">
          <Button fullWidth>Continue trip</Button>
        </Link>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {/* Online toggle */}
      <Card className="space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-gray-900">
              {isOnline ? "You are online" : "You are offline"}
            </h2>
            <p className="text-sm text-gray-500">
              {isOnline
                ? "Ride requests will appear below."
                : "Go online to start receiving ride requests."}
            </p>
          </div>
          <span
            className={`h-3 w-3 rounded-full ${isOnline ? "bg-emerald-500" : "bg-gray-300"}`}
            aria-hidden
          />
        </div>
        {!vehicle && (
          <Alert tone="info">
            Add your vehicle before going online.{" "}
            <Link href="/driver/onboarding" className="font-semibold underline">
              Add vehicle
            </Link>
          </Alert>
        )}
        {error && <Alert tone="error">{error}</Alert>}
        <Button
          fullWidth
          variant={isOnline ? "secondary" : "primary"}
          loading={toggleBusy}
          disabled={!vehicle && !isOnline}
          onClick={toggleOnline}
        >
          {isOnline ? "Go offline" : "Go online"}
        </Button>
      </Card>

      {/* Dispatch feed */}
      {isOnline && (
        <div className="space-y-2">
          <h3 className="font-semibold text-gray-900">
            Ride requests{requests.length > 0 && ` (${requests.length})`}
          </h3>
          {requests.length === 0 ? (
            <Card>
              <div className="flex items-center gap-3 text-gray-500">
                <Spinner size="sm" />
                <p className="text-sm">Waiting for requests…</p>
              </div>
            </Card>
          ) : (
            requests.map((ride) => (
              <RequestCard
                key={ride.id}
                ride={ride}
                busy={acceptBusyId === ride.id}
                onAccept={() => accept(ride.id)}
                onDismiss={() => dismiss(ride.id)}
              />
            ))
          )}
        </div>
      )}
    </div>
  );
}
