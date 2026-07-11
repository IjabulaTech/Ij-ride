/* eslint-disable @next/next/no-img-element */
import { VEHICLE_CATEGORY_ICONS, VEHICLE_CATEGORY_LABELS } from "@/lib/format";
import type { RideUser, Vehicle } from "@/types/api";

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (!parts.length) return "🚗";
  return parts
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase())
    .join("");
}

export function DriverCard({ driver, vehicle }: { driver: RideUser; vehicle: Vehicle | null }) {
  const name = [driver.first_name, driver.last_name].filter(Boolean).join(" ") || "Your driver";
  const categoryIcon = vehicle ? VEHICLE_CATEGORY_ICONS[vehicle.category] : "🚗";
  const categoryLabel = vehicle ? VEHICLE_CATEGORY_LABELS[vehicle.category] : "Vehicle";
  // KEKE listings have no make/model/colour — show only what's set.
  const vehicleDescription = vehicle
    ? [vehicle.color, vehicle.make, vehicle.model].filter(Boolean).join(" ")
    : "";
  const vehiclePhotoAlt = [categoryLabel, vehicleDescription, vehicle?.plate_number]
    .filter(Boolean)
    .join(" ");

  return (
    <div className="space-y-3 rounded-lg bg-gray-50 p-3">
      <div className="flex items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-3">
          {/* Driver profile photo, with initials fallback */}
          {driver.photo_url ? (
            <img
              src={driver.photo_url}
              alt={name}
              className="h-12 w-12 shrink-0 rounded-full border border-gray-200 object-cover"
            />
          ) : (
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-emerald-100 text-sm font-bold text-emerald-700">
              {initials(name)}
            </div>
          )}
          <div className="min-w-0">
            <p className="truncate font-semibold text-gray-900">{name}</p>
            {vehicle && (
              <>
                <p className="truncate text-sm text-gray-600">
                  <span aria-hidden>{categoryIcon}</span> {categoryLabel}
                  {vehicleDescription && ` · ${vehicleDescription}`}
                </p>
                <p className="text-sm font-mono font-semibold text-gray-800">
                  {vehicle.plate_number}
                </p>
              </>
            )}
          </div>
        </div>
        <a
          href={`tel:${driver.phone}`}
          className="shrink-0 rounded-full bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700"
        >
          Call
        </a>
      </div>
      {vehicle?.photo_url ? (
        <img
          src={vehicle.photo_url}
          alt={vehiclePhotoAlt}
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
