export function formatNaira(amount: string | number | null | undefined): string {
  if (amount === null || amount === undefined || amount === "") return "—";
  const value = typeof amount === "string" ? parseFloat(amount) : amount;
  if (Number.isNaN(value)) return "—";
  return `₦${value.toLocaleString("en-NG", { maximumFractionDigits: 0 })}`;
}

export function formatDistance(meters: number | null | undefined): string {
  if (meters === null || meters === undefined) return "—";
  return meters < 1000 ? `${meters} m` : `${(meters / 1000).toFixed(1)} km`;
}

export function formatDuration(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined) return "—";
  return `${Math.max(1, Math.round(seconds / 60))} min`;
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("en-NG", { dateStyle: "medium", timeStyle: "short" });
}

export const PAYMENT_METHOD_LABELS = {
  CASH: "Cash",
  TRANSFER: "Bank transfer",
} as const;

export const VEHICLE_CATEGORY_LABELS = {
  KEKE: "Keke",
  CAR: "Car",
} as const;

export const VEHICLE_CATEGORY_ICONS = {
  KEKE: "🛺",
  CAR: "🚗",
} as const;

/** Real vehicle photos for the ride-type selector (public/vehicle-icons). */
export const VEHICLE_CATEGORY_IMAGES = {
  KEKE: "/vehicle-icons/keke.jpg",
  CAR: "/vehicle-icons/car.jpg",
} as const;
