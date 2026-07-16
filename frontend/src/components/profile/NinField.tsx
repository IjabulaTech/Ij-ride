"use client";

import { Input } from "@/components/ui/Input";

/** NIN input with a verification status line. Verification itself is done by an
 * admin (V1) — this just captures the 11-digit number and shows its status. */
export function NinField({
  value,
  onChange,
  verified,
  error,
}: {
  value: string;
  onChange: (next: string) => void;
  verified: boolean;
  error?: string;
}) {
  return (
    <div className="space-y-1">
      <Input
        label="NIN (National Identification Number)"
        value={value}
        onChange={(e) => onChange(e.target.value.replace(/\D/g, "").slice(0, 11))}
        inputMode="numeric"
        placeholder="11-digit NIN"
        maxLength={11}
        error={error}
        hint="Optional. Used to verify your identity."
      />
      {verified ? (
        <p className="text-xs font-semibold text-emerald-700">✓ NIN verified</p>
      ) : value.length === 11 ? (
        <p className="text-xs text-amber-600">Awaiting admin verification.</p>
      ) : null}
    </div>
  );
}
