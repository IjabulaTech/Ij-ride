"use client";

import { RideHistoryList } from "@/components/ride/RideHistoryList";

export default function DriverHistoryPage() {
  return (
    <div className="space-y-4">
      <h2 className="text-lg font-bold text-gray-900">Trip history</h2>
      <RideHistoryList detailBase="/driver/history" />
    </div>
  );
}
