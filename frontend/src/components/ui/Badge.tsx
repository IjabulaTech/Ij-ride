import type { ReactNode } from "react";

import type { ApprovalStatus, PaymentStatus, RideStatus } from "@/types/api";

export type BadgeTone = "green" | "yellow" | "red" | "gray" | "blue";

const TONES: Record<BadgeTone, string> = {
  green: "bg-emerald-100 text-emerald-800",
  yellow: "bg-amber-100 text-amber-800",
  red: "bg-red-100 text-red-800",
  gray: "bg-gray-100 text-gray-700",
  blue: "bg-blue-100 text-blue-800",
};

export function Badge({ tone = "gray", children }: { tone?: BadgeTone; children: ReactNode }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${TONES[tone]}`}
    >
      {children}
    </span>
  );
}

export function rideStatusTone(status: RideStatus): BadgeTone {
  switch (status) {
    case "SEARCHING":
      return "yellow";
    case "ACCEPTED":
    case "DRIVER_ARRIVED":
      return "blue";
    case "IN_PROGRESS":
      return "green";
    case "COMPLETED":
      return "green";
    case "CANCELLED":
    case "EXPIRED":
      return "red";
  }
}

export function paymentStatusTone(status: PaymentStatus): BadgeTone {
  switch (status) {
    case "PAID":
      return "green";
    case "CLAIMED":
      return "blue";
    case "PENDING":
      return "yellow";
    case "FAILED":
      return "red";
  }
}

export function approvalStatusTone(status: ApprovalStatus): BadgeTone {
  switch (status) {
    case "APPROVED":
      return "green";
    case "PENDING":
      return "yellow";
    case "REJECTED":
      return "red";
  }
}
