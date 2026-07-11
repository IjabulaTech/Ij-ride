import { api, ApiError } from "./client";
import type {
  DriverAvailability,
  DriverProfile,
  Earnings,
  Vehicle,
  VehicleCategory,
} from "@/types/api";

export function getProfile(): Promise<DriverProfile> {
  return api<DriverProfile>("/drivers/me/profile/");
}

export function updateProfile(data: {
  license_number: string;
  /** Optional personal profile photo; omit to keep the existing one. */
  photo?: File | null;
}): Promise<DriverProfile> {
  if (data.photo) {
    // Multipart when a new photo is attached
    const form = new FormData();
    form.append("license_number", data.license_number);
    form.append("photo", data.photo);
    return api<DriverProfile>("/drivers/me/profile/", { method: "PUT", body: form });
  }
  return api<DriverProfile>("/drivers/me/profile/", {
    method: "PUT",
    body: { license_number: data.license_number },
  });
}

/** The driver's active vehicle, or null (404 before one is registered). */
export async function getVehicle(): Promise<Vehicle | null> {
  try {
    return await api<Vehicle>("/drivers/me/vehicle/");
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) return null;
    throw err;
  }
}

export interface VehicleData {
  category: VehicleCategory;
  make: string;
  model: string;
  year: number | string;
  color: string;
  plate_number: string;
  /** New photo to upload; omit to keep the existing one. */
  photo?: File | null;
}

export function saveVehicle(data: VehicleData): Promise<Vehicle> {
  // Multipart so the photo can ride along; works fine without a photo too.
  const form = new FormData();
  form.append("category", data.category);
  form.append("plate_number", data.plate_number);
  // Car-only fields — a KEKE leaves these blank, so only send what's filled
  // (an empty "year" would fail integer validation server-side).
  if (data.make) form.append("make", data.make);
  if (data.model) form.append("model", data.model);
  if (String(data.year)) form.append("year", String(data.year));
  if (data.color) form.append("color", data.color);
  if (data.photo) form.append("photo", data.photo);
  return api<Vehicle>("/drivers/me/vehicle/", { method: "PUT", body: form });
}

export function getAvailability(): Promise<DriverAvailability> {
  return api<DriverAvailability>("/drivers/me/availability/");
}

export function setAvailability(is_online: boolean): Promise<DriverAvailability> {
  return api<DriverAvailability>("/drivers/me/availability/", {
    method: "POST",
    body: { is_online },
  });
}

export function updateLocation(lat: string, lng: string): Promise<DriverAvailability> {
  return api<DriverAvailability>("/drivers/me/location/", { method: "POST", body: { lat, lng } });
}

export function getEarnings(): Promise<Earnings> {
  return api<Earnings>("/drivers/me/earnings/");
}
