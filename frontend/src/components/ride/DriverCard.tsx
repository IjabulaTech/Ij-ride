/* eslint-disable @next/next/no-img-element */
import { VEHICLE_CATEGORY_ICONS, VEHICLE_CATEGORY_LABELS } from "@/lib/format";
import type { RideUser, Vehicle } from "@/types/api";

export function DriverCard({ driver, vehicle }: { driver: RideUser; vehicle: Vehicle | null }) {
  const name = [driver.first_name, driver.last_name].filter(Boolean).join(" ") || "Your driver";
  const categoryIcon = vehicle ? VEHICLE_CATEGORY_ICONS[vehicle.category] : "🚗";
  const categoryLabel = vehicle ? VEHICLE_CATEGORY_LABELS[vehicle.category] : "Vehicle";

  return (
    <div className="space-y-3 rounded-lg bg-gray-50 p-3">
      <div className="flex items-center justify-between">
        <div>
          <p className="font-semibold text-gray-900">{name}</p>
          {vehicle && (
            <>
              <p className="text-sm text-gray-600">
                <span aria-hidden>{categoryIcon}</span> {categoryLabel} · {vehicle.color}{" "}
                {vehicle.make} {vehicle.model}
              </p>
              <p className="text-sm font-mono font-semibold text-gray-800">
                {vehicle.plate_number}
              </p>
            </>
          )}
        </div>
        <a
          href={`tel:${driver.phone}`}
          className="rounded-full bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700"
        >
          Call
        </a>
      </div>
      {vehicle?.photo_url ? (
        <img
          src={vehicle.photo_url}
          alt={`${vehicle.color} ${vehicle.make} ${vehicle.model} (${vehicle.plate_number})`}
          className="h-36 w-full rounded-lg border border-gray-200 object-cover"
        />
      ) : (
        <div
          className="flex h-36 w-full flex-col items-center justify-center gap-1 rounded-lg border border-dashed border-gray-300 bg-white text-gray-400"
          role="img"
          aria-label={`No ${categoryLabel} photo uploaded`}
        >
          <span className="text-4xl" aria-hidden>
            {categoryIcon}
          </span>
          <span className="text-xs font-medium">No vehicle photo yet</span>
        </div>
      )}
    </div>
  );
}
