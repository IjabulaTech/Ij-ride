import { api } from "./client";
import type { AuthResponse, Me, PaymentMethod, VehicleCategory } from "@/types/api";

export interface RegisterData {
  phone: string;
  password: string;
  first_name?: string;
  last_name?: string;
  email?: string;
  /** Required when registering a driver — chooses their operating category. */
  driver_category?: VehicleCategory;
}

export function login(phone: string, password: string): Promise<AuthResponse> {
  return api<AuthResponse>("/auth/token/", {
    method: "POST",
    body: { phone, password },
    auth: false,
  });
}

/** Request a password-reset code by phone. Always resolves (the API responds
 * the same whether or not the account exists). */
export function requestPasswordReset(phone: string): Promise<{ detail: string }> {
  return api<{ detail: string }>("/auth/password/reset/request/", {
    method: "POST",
    body: { phone },
    auth: false,
  });
}

export function confirmPasswordReset(
  phone: string,
  code: string,
  new_password: string
): Promise<{ detail: string }> {
  return api<{ detail: string }>("/auth/password/reset/confirm/", {
    method: "POST",
    body: { phone, code, new_password },
    auth: false,
  });
}

export function registerPassenger(data: RegisterData): Promise<AuthResponse> {
  return api<AuthResponse>("/auth/register/passenger/", {
    method: "POST",
    body: data,
    auth: false,
  });
}

export function registerDriver(data: RegisterData): Promise<AuthResponse> {
  return api<AuthResponse>("/auth/register/driver/", {
    method: "POST",
    body: data,
    auth: false,
  });
}

export function me(): Promise<Me> {
  return api<Me>("/auth/me/");
}

export interface UpdateMeData {
  first_name?: string;
  last_name?: string;
  email?: string;
  nin?: string;
  default_payment_method?: PaymentMethod;
}

export function updateMe(data: UpdateMeData): Promise<Me> {
  return api<Me>("/auth/me/", { method: "PATCH", body: data });
}
