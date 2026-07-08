import { api, ApiError } from "./client";
import type {
  Estimate,
  LocationInput,
  OpenRide,
  Paginated,
  PaymentMethod,
  Ride,
  RideListItem,
  VehicleCategory,
} from "@/types/api";

export function estimate(
  vehicleCategory: VehicleCategory,
  pickup: LocationInput,
  dropoff: LocationInput
): Promise<Estimate> {
  return api<Estimate>("/rides/estimate/", {
    method: "POST",
    body: { vehicle_category: vehicleCategory, pickup, dropoff },
  });
}

export function createRide(data: {
  vehicle_category: VehicleCategory;
  pickup: LocationInput;
  dropoff: LocationInput;
  payment_method?: PaymentMethod;
}): Promise<Ride> {
  return api<Ride>("/rides/", { method: "POST", body: data });
}

/** The caller's current ride, or null (the endpoint 404s when there is none). */
export async function activeRide(): Promise<Ride | null> {
  try {
    return await api<Ride>("/rides/active/");
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) return null;
    throw err;
  }
}

export function listRides(page = 1): Promise<Paginated<RideListItem>> {
  return api<Paginated<RideListItem>>(`/rides/?page=${page}`);
}

export function getRide(id: number): Promise<Ride> {
  return api<Ride>(`/rides/${id}/`);
}

export function cancelRide(id: number, reason = ""): Promise<Ride> {
  return api<Ride>(`/rides/${id}/cancel/`, { method: "POST", body: { reason } });
}

export function claimPayment(id: number, reference = ""): Promise<Ride> {
  return api<Ride>(`/rides/${id}/payment/claim/`, { method: "POST", body: { reference } });
}

export function confirmPayment(id: number): Promise<Ride> {
  return api<Ride>(`/rides/${id}/payment/confirm/`, { method: "POST", body: {} });
}

// ---- driver-side (Module 11) ----

export function openRides(): Promise<Paginated<OpenRide>> {
  return api<Paginated<OpenRide>>("/rides/open/");
}

export function acceptRide(id: number): Promise<Ride> {
  return api<Ride>(`/rides/${id}/accept/`, { method: "POST", body: {} });
}

export function rejectRide(id: number): Promise<void> {
  return api<void>(`/rides/${id}/reject/`, { method: "POST", body: {} });
}

export function markArrived(id: number): Promise<Ride> {
  return api<Ride>(`/rides/${id}/arrived/`, { method: "POST", body: {} });
}

export function startTrip(id: number): Promise<Ride> {
  return api<Ride>(`/rides/${id}/start/`, { method: "POST", body: {} });
}

export function completeTrip(id: number): Promise<Ride> {
  return api<Ride>(`/rides/${id}/complete/`, { method: "POST", body: {} });
}
