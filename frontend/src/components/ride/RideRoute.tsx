export function RideRoute({ pickup, dropoff }: { pickup: string; dropoff: string }) {
  return (
    <div className="space-y-2">
      <div className="flex items-start gap-2">
        <span className="mt-1 h-2.5 w-2.5 shrink-0 rounded-full bg-emerald-500" aria-hidden />
        <div>
          <p className="text-xs text-gray-500">Pickup</p>
          <p className="text-sm font-medium text-gray-900">{pickup}</p>
        </div>
      </div>
      <div className="flex items-start gap-2">
        <span className="mt-1 h-2.5 w-2.5 shrink-0 rounded-full bg-red-500" aria-hidden />
        <div>
          <p className="text-xs text-gray-500">Destination</p>
          <p className="text-sm font-medium text-gray-900">{dropoff}</p>
        </div>
      </div>
    </div>
  );
}
