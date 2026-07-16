/** Management API client — admin role only (enforced server-side). */
import { api } from "./client";
import type {
  AdminCommission,
  AdminDriver,
  AdminPayment,
  AdminUser,
  CommissionSummary,
  FareSetting,
  Paginated,
  Ride,
} from "@/types/api";

function query(params: Record<string, string | number | undefined>): string {
  const parts = Object.entries(params)
    .filter(([, v]) => v !== undefined && v !== "")
    .map(([k, v]) => `${k}=${encodeURIComponent(String(v))}`);
  return parts.length ? `?${parts.join("&")}` : "";
}

export function listUsers(params: {
  page?: number;
  role?: string;
  is_active?: string;
  search?: string;
}): Promise<Paginated<AdminUser>> {
  return api<Paginated<AdminUser>>(`/management/users/${query(params)}`);
}

export function listDrivers(params: {
  page?: number;
  approval_status?: string;
  search?: string;
}): Promise<Paginated<AdminDriver>> {
  return api<Paginated<AdminDriver>>(`/management/drivers/${query(params)}`);
}

export function getDriver(id: number): Promise<AdminDriver> {
  return api<AdminDriver>(`/management/drivers/${id}/`);
}

/** Admin marks a user's NIN verified/unverified after review. */
export function verifyNin(
  userId: number,
  verified: boolean
): Promise<{ id: number; nin: string; nin_verified: boolean }> {
  return api(`/management/users/${userId}/verify-nin/`, {
    method: "POST",
    body: { verified },
  });
}

export function approveDriver(id: number, note = ""): Promise<AdminDriver> {
  return api<AdminDriver>(`/management/drivers/${id}/approve/`, {
    method: "POST",
    body: { note },
  });
}

export function rejectDriver(id: number, reason: string): Promise<AdminDriver> {
  return api<AdminDriver>(`/management/drivers/${id}/reject/`, {
    method: "POST",
    body: { reason },
  });
}

export function listAdminRides(params: {
  page?: number;
  status?: string;
  search?: string;
  /** Inclusive calendar-day bounds, YYYY-MM-DD (Yola local time). */
  date_from?: string;
  date_to?: string;
}): Promise<Paginated<Ride>> {
  return api<Paginated<Ride>>(`/management/rides/${query(params)}`);
}

export function getAdminRide(id: number): Promise<Ride> {
  return api<Ride>(`/management/rides/${id}/`);
}

export function listPayments(params: {
  page?: number;
  status?: string;
  method?: string;
  search?: string;
}): Promise<Paginated<AdminPayment>> {
  return api<Paginated<AdminPayment>>(`/management/payments/${query(params)}`);
}

export function listFareSettings(page = 1): Promise<Paginated<FareSetting>> {
  return api<Paginated<FareSetting>>(`/management/fare-settings/?page=${page}`);
}

export interface FareSettingData {
  vehicle_category: "KEKE" | "CAR";
  base_fare: string;
  per_km: string;
  per_minute: string;
  minimum_fare: string;
  rounding_step?: string;
}

export function createFareSetting(data: FareSettingData): Promise<FareSetting> {
  return api<FareSetting>("/management/fare-settings/", { method: "POST", body: data });
}

export function listCommissions(params: {
  page?: number;
  status?: string;
  search?: string;
  driver_id?: number;
}): Promise<Paginated<AdminCommission>> {
  return api<Paginated<AdminCommission>>(`/management/commissions/${query(params)}`);
}

export function commissionSummary(): Promise<CommissionSummary> {
  return api<CommissionSummary>("/management/commissions/summary/");
}

export function remitCommission(id: number, note = ""): Promise<AdminCommission> {
  return api<AdminCommission>(`/management/commissions/${id}/remit/`, {
    method: "POST",
    body: { note },
  });
}

export function settleDriver(
  driverId: number,
  note = ""
): Promise<{ settled_count: number; settled_amount: string }> {
  return api(`/management/commissions/settle-driver/`, {
    method: "POST",
    body: { driver_id: driverId, note },
  });
}
