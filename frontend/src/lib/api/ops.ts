/** Maintenance mode: public status + the admin on/off switch. */
import { api } from "./client";

export interface MaintenanceState {
  maintenance: boolean;
  message: string;
}

/** Public — no auth, and never blocked while maintenance is on. */
export function maintenanceStatus(): Promise<MaintenanceState> {
  return api<MaintenanceState>("/ops/status/", { auth: false });
}

export function getMaintenance(): Promise<MaintenanceState> {
  return api<MaintenanceState>("/management/maintenance/");
}

export function setMaintenance(active: boolean, message = ""): Promise<MaintenanceState> {
  return api<MaintenanceState>("/management/maintenance/", {
    method: "POST",
    body: { active, message },
  });
}
