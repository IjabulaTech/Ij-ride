"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { RideStatusBadge } from "@/components/ride/RideStatusBadge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { listRides } from "@/lib/api/rides";
import { formatDateTime, formatNaira } from "@/lib/format";
import type { RideListItem } from "@/types/api";

/** Paginated terminal-ride list, role-agnostic (the API scopes by caller). */
export function RideHistoryList({ detailBase }: { detailBase: string }) {
  const [items, setItems] = useState<RideListItem[]>([]);
  const [nextPage, setNextPage] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);

  async function load(page: number, append: boolean) {
    const data = await listRides(page);
    setItems((prev) => (append ? [...prev, ...data.results] : data.results));
    setNextPage(data.next ? page + 1 : null);
  }

  useEffect(() => {
    load(1, false)
      .catch(() => undefined)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex justify-center py-16 text-emerald-600">
        <Spinner size="lg" />
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <Card>
        <p className="text-sm text-gray-500">
          No past trips yet. Completed and cancelled rides will show up here.
        </p>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        {items.map((ride) => (
          <Link key={ride.id} href={`${detailBase}/${ride.id}`} className="block">
            <Card className="transition-colors hover:border-emerald-300">
              <div className="flex items-center justify-between gap-2">
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-gray-900">
                    {ride.pickup_address} → {ride.dropoff_address}
                  </p>
                  <p className="text-xs text-gray-500">{formatDateTime(ride.created_at)}</p>
                </div>
                <div className="shrink-0 text-right">
                  <p className="text-sm font-bold text-gray-900">
                    {formatNaira(ride.final_fare ?? ride.estimated_fare)}
                  </p>
                  <RideStatusBadge status={ride.status} />
                </div>
              </div>
            </Card>
          </Link>
        ))}
      </div>
      {nextPage && (
        <Button
          variant="secondary"
          fullWidth
          loading={loadingMore}
          onClick={async () => {
            setLoadingMore(true);
            await load(nextPage, true).catch(() => undefined);
            setLoadingMore(false);
          }}
        >
          Load more
        </Button>
      )}
    </div>
  );
}
