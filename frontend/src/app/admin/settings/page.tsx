"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";

import { Alert } from "@/components/ui/Alert";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { FullPageSpinner } from "@/components/ui/Spinner";
import { ApiError } from "@/lib/api/client";
import { createFareSetting, listFareSettings } from "@/lib/api/admin";
import {
  formatDateTime,
  formatNaira,
  VEHICLE_CATEGORY_ICONS,
  VEHICLE_CATEGORY_LABELS,
} from "@/lib/format";
import type { FareSetting, VehicleCategory } from "@/types/api";

const CATEGORIES: VehicleCategory[] = ["KEKE", "CAR"];

const EMPTY_FORM = {
  base_fare: "",
  per_km: "",
  per_minute: "",
  minimum_fare: "",
  rounding_step: "50",
};

export default function FareSettingsPage() {
  const [settings, setSettings] = useState<FareSetting[] | null>(null);
  const [formCategory, setFormCategory] = useState<VehicleCategory>("CAR");
  const [form, setForm] = useState(EMPTY_FORM);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string[]>>({});
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ tone: "success" | "error"; text: string } | null>(null);

  const load = useCallback(async () => {
    const data = await listFareSettings();
    setSettings(data.results);
  }, []);

  useEffect(() => {
    load().catch(() => setMessage({ tone: "error", text: "Could not load fare settings." }));
  }, [load]);

  const activeFor = (category: VehicleCategory) =>
    settings?.find((s) => s.is_active && s.vehicle_category === category) ?? null;
  const set = (key: keyof typeof EMPTY_FORM) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [key]: e.target.value }));
  const fieldError = (key: string) => fieldErrors[key]?.join(" ");

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setMessage(null);
    setFieldErrors({});
    try {
      await createFareSetting({ ...form, vehicle_category: formCategory });
      await load();
      setForm(EMPTY_FORM);
      setMessage({
        tone: "success",
        text: `New ${VEHICLE_CATEGORY_LABELS[formCategory]} fares are now active. New ride quotes use them immediately.`,
      });
    } catch (err) {
      if (err instanceof ApiError) {
        setFieldErrors(err.fieldErrors);
        if (!Object.keys(err.fieldErrors).length) setMessage({ tone: "error", text: err.message });
      } else {
        setMessage({ tone: "error", text: "Could not save. Try again." });
      }
    } finally {
      setBusy(false);
    }
  }

  if (!settings) return <FullPageSpinner />;

  return (
    <div className="max-w-2xl space-y-4">
      <h2 className="text-lg font-bold text-gray-900">Fare settings</h2>

      {CATEGORIES.map((category) => {
        const active = activeFor(category);
        return (
          <Card key={category} className="space-y-2">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-gray-900">
                <span aria-hidden>{VEHICLE_CATEGORY_ICONS[category]}</span>{" "}
                {VEHICLE_CATEGORY_LABELS[category]} fares
              </h3>
              {active && <Badge tone="green">ACTIVE</Badge>}
            </div>
            {active ? (
              <p className="text-sm text-gray-600">
                Base {formatNaira(active.base_fare)} + {formatNaira(active.per_km)}/km +{" "}
                {formatNaira(active.per_minute)}/min · minimum {formatNaira(active.minimum_fare)}{" "}
                · rounded up to {formatNaira(active.rounding_step)} · since{" "}
                {formatDateTime(active.created_at)}
              </p>
            ) : (
              <Alert tone="error">
                No active {VEHICLE_CATEGORY_LABELS[category]} fares —{" "}
                {VEHICLE_CATEGORY_LABELS[category]} estimates and requests will fail until they
                are created below.
              </Alert>
            )}
          </Card>
        );
      })}

      <Card>
        <form onSubmit={handleSubmit} className="space-y-4">
          <h3 className="font-semibold text-gray-900">Set new fares</h3>
          <p className="text-sm text-gray-500">
            Saving creates a new active configuration; the previous one is kept for the pricing
            history of past rides.
          </p>
          {message && <Alert tone={message.tone}>{message.text}</Alert>}
          <div>
            <p className="mb-2 text-sm font-medium text-gray-700">Vehicle category</p>
            <div className="grid grid-cols-2 gap-2">
              {CATEGORIES.map((c) => (
                <button
                  key={c}
                  type="button"
                  onClick={() => setFormCategory(c)}
                  className={`rounded-lg border px-3 py-2.5 text-sm font-semibold ${
                    formCategory === c
                      ? "border-emerald-600 bg-emerald-50 text-emerald-700"
                      : "border-gray-300 bg-white text-gray-700"
                  }`}
                >
                  {VEHICLE_CATEGORY_ICONS[c]} {VEHICLE_CATEGORY_LABELS[c]}
                </button>
              ))}
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Input label="Base fare (₦)" type="number" min="0" step="0.01" value={form.base_fare} onChange={set("base_fare")} error={fieldError("base_fare")} required />
            <Input label="Per km (₦)" type="number" min="0" step="0.01" value={form.per_km} onChange={set("per_km")} error={fieldError("per_km")} required />
            <Input label="Per minute (₦)" type="number" min="0" step="0.01" value={form.per_minute} onChange={set("per_minute")} error={fieldError("per_minute")} required />
            <Input label="Minimum fare (₦)" type="number" min="0" step="0.01" value={form.minimum_fare} onChange={set("minimum_fare")} error={fieldError("minimum_fare")} required />
            <Input label="Round up to (₦)" type="number" min="0" step="0.01" value={form.rounding_step} onChange={set("rounding_step")} error={fieldError("rounding_step")} hint="0 disables rounding." />
          </div>
          <Button type="submit" fullWidth loading={busy}>
            Save and activate
          </Button>
        </form>
      </Card>

      <Card>
        <h3 className="mb-2 font-semibold text-gray-900">History</h3>
        <ul className="divide-y divide-gray-100 text-sm">
          {settings.map((s) => (
            <li key={s.id} className="flex items-center justify-between py-2">
              <span className="text-gray-600">
                <span className="mr-1 font-semibold text-gray-800">
                  {VEHICLE_CATEGORY_LABELS[s.vehicle_category]}:
                </span>
                {formatNaira(s.base_fare)} + {formatNaira(s.per_km)}/km +{" "}
                {formatNaira(s.per_minute)}/min · min {formatNaira(s.minimum_fare)}
              </span>
              <span className="flex items-center gap-2 text-xs text-gray-500">
                {formatDateTime(s.created_at)}
                {s.is_active && <Badge tone="green">active</Badge>}
              </span>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
