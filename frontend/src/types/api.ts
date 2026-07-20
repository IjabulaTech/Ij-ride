/** TypeScript mirrors of the Django API serializers. */

export type Role = "PASSENGER" | "DRIVER" | "ADMIN";
export type PaymentMethod = "CASH" | "TRANSFER";
export type PaymentStatus = "PENDING" | "CLAIMED" | "PAID" | "FAILED";
export type RideStatus =
  | "SEARCHING"
  | "ACCEPTED"
  | "DRIVER_ARRIVED"
  | "IN_PROGRESS"
  | "COMPLETED"
  | "CANCELLED"
  | "EXPIRED";
export type ApprovalStatus = "PENDING" | "APPROVED" | "REJECTED";
export type VehicleCategory = "KEKE" | "CAR";

export interface User {
  id: number;
  phone: string;
  first_name: string;
  last_name: string;
  email: string;
  role: Role;
  nin: string;
  nin_verified: boolean;
  date_joined: string;
}

export interface PassengerProfile {
  default_payment_method: PaymentMethod;
}

export interface DriverProfileSummary {
  driver_category: VehicleCategory;
  license_number: string;
  approval_status: ApprovalStatus;
  approval_note: string;
}

export interface Me extends User {
  profile: PassengerProfile | DriverProfileSummary | null;
}

export interface AuthTokens {
  access: string;
  refresh: string;
}

/** POST /auth/token/ and /auth/register/... both return this shape. */
export interface AuthResponse extends AuthTokens {
  user: User;
}

export interface Vehicle {
  id: number;
  category: VehicleCategory;
  // make/model/color are "" and year is null for KEKE (tricycle) listings
  make: string;
  model: string;
  year: number | null;
  color: string;
  plate_number: string;
  photo_url: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface DriverAvailability {
  is_online: boolean;
  current_lat: string | null;
  current_lng: string | null;
  location_updated_at: string | null;
  last_seen_at: string | null;
}

export interface DriverProfile {
  driver_category: VehicleCategory;
  license_number: string;
  photo_url: string | null;
  approval_status: ApprovalStatus;
  approval_note: string;
  approved_at: string | null;
  created_at: string;
}

export interface RideUser {
  id: number;
  phone: string;
  first_name: string;
  last_name: string;
  /** Driver's personal profile photo; null for passengers or when unset. */
  photo_url: string | null;
}

export interface RidePayment {
  method: PaymentMethod;
  status: PaymentStatus;
  amount: string | null;
  currency: string;
  reference: string;
  claimed_at: string | null;
  confirmed_at: string | null;
}

export interface Ride {
  id: number;
  status: RideStatus;
  requested_vehicle_category: VehicleCategory;
  passenger: RideUser;
  driver: RideUser | null;
  vehicle: Vehicle | null;
  pickup_address: string;
  pickup_lat: string;
  pickup_lng: string;
  dropoff_address: string;
  dropoff_lat: string;
  dropoff_lng: string;
  estimated_distance_m: number | null;
  estimated_duration_s: number | null;
  estimated_fare: string | null;
  final_fare: string | null;
  payment_method: PaymentMethod;
  payment: RidePayment | null;
  accepted_at: string | null;
  arrived_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  cancelled_at: string | null;
  expired_at: string | null;
  cancelled_by_role: string;
  cancellation_reason: string;
  created_at: string;
}

export interface RideListItem {
  id: number;
  status: RideStatus;
  requested_vehicle_category: VehicleCategory;
  pickup_address: string;
  dropoff_address: string;
  estimated_fare: string | null;
  final_fare: string | null;
  payment_method: PaymentMethod;
  created_at: string;
  completed_at: string | null;
  cancelled_at: string | null;
}

export interface OpenRide {
  id: number;
  requested_vehicle_category: VehicleCategory;
  pickup_address: string;
  pickup_lat: string;
  pickup_lng: string;
  dropoff_address: string;
  dropoff_lat: string;
  dropoff_lng: string;
  estimated_distance_m: number | null;
  estimated_duration_s: number | null;
  estimated_fare: string | null;
  payment_method: PaymentMethod;
  passenger_first_name: string;
  created_at: string;
}

export interface LocationInput {
  address?: string;
  lat?: string | null;
  lng?: string | null;
}

export interface Estimate {
  vehicle_category: VehicleCategory;
  pickup: { address: string; lat: string; lng: string };
  dropoff: { address: string; lat: string; lng: string };
  distance_m: number;
  duration_s: number;
  fare: string;
  currency: string;
  breakdown: {
    base_fare: string;
    distance_fare: string;
    time_fare: string;
    minimum_fare_applied: boolean;
    rounding_step: string;
  };
}

export interface EarningsWindow {
  trips: number;
  gross: string;
  paid: string;
  unpaid: string;
  commission: string;
  net: string;
}

export interface Earnings {
  currency: string;
  outstanding_commission: string;
  today: EarningsWindow;
  last_7_days: EarningsWindow;
  all_time: EarningsWindow;
}

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

// ---- management API (admin console) ----

export interface AdminUser extends User {
  is_active: boolean;
  last_login: string | null;
}

/** One message in a customer-support conversation. */
export interface SupportMessage {
  id: number;
  thread: number;
  body: string;
  from_admin: boolean;
  sender_name: string;
  created_at: string;
}

/** A user's support conversation, as shown in the admin inbox. */
export interface SupportThread {
  id: number;
  user_id: number;
  phone: string;
  name: string;
  role: Role;
  last_message_at: string | null;
  last_message_preview: string;
  unread_for_admin: number;
  created_at: string;
}

export interface AdminDriver {
  id: number;
  user: User;
  license_number: string;
  photo_url: string | null;
  approval_status: ApprovalStatus;
  approval_note: string;
  approved_at: string | null;
  approved_by: number | null;
  active_vehicle: Vehicle | null;
  availability: DriverAvailability | null;
  created_at: string;
}

export interface AdminPayment {
  id: number;
  ride_id: number;
  ride_status: RideStatus;
  passenger_phone: string;
  driver_phone: string | null;
  pickup_address: string;
  dropoff_address: string;
  amount: string | null;
  currency: string;
  method: PaymentMethod;
  status: PaymentStatus;
  reference: string;
  claimed_at: string | null;
  confirmed_by_phone: string | null;
  confirmed_at: string | null;
  provider: string;
  provider_ref: string;
  created_at: string;
}

export interface FareSetting {
  id: number;
  vehicle_category: VehicleCategory;
  base_fare: string;
  per_km: string;
  per_minute: string;
  minimum_fare: string;
  rounding_step: string;
  currency: string;
  is_active: boolean;
  created_by: number | null;
  created_at: string;
}

export type CommissionType = "PERCENTAGE" | "FIXED";
export type RemittanceStatus = "PENDING" | "REMITTED" | "WAIVED";

export interface AdminCommission {
  id: number;
  ride_id: number;
  driver_id: number;
  driver_phone: string;
  driver_name: string;
  fare_amount: string;
  commission_type: CommissionType | "";
  commission_value: string;
  commission_amount: string;
  driver_earning: string;
  status: RemittanceStatus;
  remitted_at: string | null;
  confirmed_by_phone: string | null;
  note: string;
  created_at: string;
}

export interface CommissionSummary {
  totals: {
    commission_total: string;
    outstanding: string;
    remitted: string;
    waived: string;
    rides_with_commission: number;
  };
  drivers_owing: {
    driver_id: number;
    phone: string;
    name: string;
    outstanding: string;
    pending_rides: number;
  }[];
}
