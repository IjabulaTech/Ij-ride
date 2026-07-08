import type { Role } from "@/types/api";

const HOME: Record<Role, string> = {
  PASSENGER: "/passenger",
  DRIVER: "/driver",
  ADMIN: "/admin",
};

export function homeFor(role: Role): string {
  return HOME[role] ?? "/login";
}
