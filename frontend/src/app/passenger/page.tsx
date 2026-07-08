"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { BookRideForm } from "@/components/passenger/BookRideForm";
import { RideStatusBadge } from "@/components/ride/RideStatusBadge";
import { RideRoute } from "@/components/ride/RideRoute";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { activeRide } from "@/lib/api/rides";
import { useAuth } from "@/lib/auth/AuthContext";
import type { PassengerProfile, Ride } from "@/types/api";

export default function PassengerDashboard() {
  const { user } = useAuth();
  const profile = user?.profile as PassengerProfile | null;

  const [checking, setChecking] = useState(true);
  const [current, setCurrent] = useState<Ride | null>(null);

  useEffect(() => {
    let cancelled = false;
    activeRide()
      .then((ride) => !cancelled && setCurrent(ride))
      .catch(() => undefined)
      .finally(() => !cancelled && setChecking(false));
    return () => {
      cancelled = true;
    };
  }, []);

  if (checking) {
    return (
      <div className="flex justify-center py-16 text-emerald-600">
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-bold text-gray-900">
        Hi{user?.first_name ? `, ${user.first_name}` : ""} 👋
      </h2>

      {current ? (
        <Card className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-gray-900">You have a ride in progress</h3>
            <RideStatusBadge status={current.status} />
          </div>
          <RideRoute pickup={current.pickup_address} dropoff={current.dropoff_address} />
          <Link href="/passenger/ride" className="block">
            <Button fullWidth>Continue to your ride</Button>
          </Link>
        </Card>
      ) : (
        <BookRideForm defaultPaymentMethod={profile?.default_payment_method ?? "CASH"} />
      )}
    </div>
  );
}
