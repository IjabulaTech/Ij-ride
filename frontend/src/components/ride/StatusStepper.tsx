import type { RideStatus } from "@/types/api";

const STEPS: { label: string; statuses: RideStatus[] }[] = [
  { label: "Finding a driver", statuses: ["SEARCHING"] },
  { label: "Driver on the way", statuses: ["ACCEPTED"] },
  { label: "Driver arrived", statuses: ["DRIVER_ARRIVED"] },
  { label: "Trip in progress", statuses: ["IN_PROGRESS"] },
  { label: "Trip completed", statuses: ["COMPLETED"] },
];

function currentIndex(status: RideStatus): number {
  const index = STEPS.findIndex((step) => step.statuses.includes(status));
  return index === -1 ? -1 : index;
}

export function StatusStepper({ status }: { status: RideStatus }) {
  const current = currentIndex(status);
  if (current === -1) return null; // cancelled/expired render their own message

  return (
    <ol className="space-y-2">
      {STEPS.map((step, index) => {
        const done = index < current || status === "COMPLETED";
        const active = index === current && status !== "COMPLETED";
        return (
          <li key={step.label} className="flex items-center gap-3">
            <span
              className={`flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-bold ${
                done
                  ? "bg-emerald-600 text-white"
                  : active
                    ? "animate-pulse bg-emerald-100 text-emerald-700 ring-2 ring-emerald-500"
                    : "bg-gray-200 text-gray-400"
              }`}
            >
              {done ? "✓" : index + 1}
            </span>
            <span
              className={`text-sm ${
                active ? "font-semibold text-gray-900" : done ? "text-gray-700" : "text-gray-400"
              }`}
            >
              {step.label}
            </span>
          </li>
        );
      })}
    </ol>
  );
}
