import { Badge, rideStatusTone } from "@/components/ui/Badge";
import type { RideStatus } from "@/types/api";

export const RIDE_STATUS_LABELS: Record<RideStatus, string> = {
  SEARCHING: "Finding driver",
  ACCEPTED: "Driver on the way",
  DRIVER_ARRIVED: "Driver arrived",
  IN_PROGRESS: "On trip",
  COMPLETED: "Completed",
  CANCELLED: "Cancelled",
  EXPIRED: "Expired",
};

export function RideStatusBadge({ status }: { status: RideStatus }) {
  return <Badge tone={rideStatusTone(status)}>{RIDE_STATUS_LABELS[status]}</Badge>;
}
