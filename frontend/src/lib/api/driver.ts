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

export function updateProfile(data: { license_number: string }): Promise<DriverProfile> {
  return api<DriverProfile>("/drivers/me/profile/", { method: "PUT", body: data });
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
  form.append("make", data.make);
  form.append("model", data.model);
  form.append("year", String(data.year));
  form.append("color", data.color);
  form.append("plate_number", data.plate_number);
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
