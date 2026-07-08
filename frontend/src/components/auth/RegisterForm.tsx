"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { ApiError } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/AuthContext";
import { homeFor } from "@/lib/auth/routes";
import { VEHICLE_CATEGORY_ICONS, VEHICLE_CATEGORY_LABELS } from "@/lib/format";
import type { VehicleCategory } from "@/types/api";

const DRIVER_CATEGORIES: VehicleCategory[] = ["KEKE", "CAR"];

export function RegisterForm({ role }: { role: "passenger" | "driver" }) {
  const { registerPassenger, registerDriver } = useAuth();
  const router = useRouter();

  const [form, setForm] = useState({
    first_name: "",
    last_name: "",
    phone: "",
    email: "",
    password: "",
    confirm: "",
  });
  const [driverCategory, setDriverCategory] = useState<VehicleCategory>("CAR");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string[]>>({});
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const set = (key: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [key]: e.target.value }));

  const fieldError = (key: string) => fieldErrors[key]?.join(" ");

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setFieldErrors({});
    if (form.password !== form.confirm) {
      setFieldErrors({ confirm: ["Passwords do not match."] });
      return;
    }
    setSubmitting(true);
    try {
      const base = {
        phone: form.phone,
        password: form.password,
        first_name: form.first_name,
        last_name: form.last_name,
        email: form.email,
      };
      const me =
        role === "passenger"
          ? await registerPassenger(base)
          : await registerDriver({ ...base, driver_category: driverCategory });
      router.replace(homeFor(me.role));
    } catch (err) {
      if (err instanceof ApiError) {
        setFieldErrors(err.fieldErrors);
        if (!Object.keys(err.fieldErrors).length) setError(err.message);
      } else {
        setError("Something went wrong. Please try again.");
      }
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {role === "driver" && (
        <Alert tone="info">
          Driver accounts need admin approval before you can go online and accept rides.
        </Alert>
      )}
      {role === "driver" && (
        <div>
          <p className="mb-2 text-sm font-medium text-gray-700">What will you drive?</p>
          <div className="grid grid-cols-2 gap-2">
            {DRIVER_CATEGORIES.map((c) => (
              <button
                key={c}
                type="button"
                onClick={() => setDriverCategory(c)}
                className={`rounded-lg border px-3 py-3 text-sm font-semibold ${
                  driverCategory === c
                    ? "border-emerald-600 bg-emerald-50 text-emerald-700"
                    : "border-gray-300 bg-white text-gray-700"
                }`}
              >
                <span className="mr-1 text-lg" aria-hidden>
                  {VEHICLE_CATEGORY_ICONS[c]}
                </span>
                {VEHICLE_CATEGORY_LABELS[c]}
              </button>
            ))}
          </div>
          {fieldError("driver_category") && (
            <p className="mt-1 text-xs text-red-600">{fieldError("driver_category")}</p>
          )}
          <p className="mt-1 text-xs text-gray-500">
            Your vehicle must match this category. Contact support to change it later.
          </p>
        </div>
      )}
      {error && <Alert tone="error">{error}</Alert>}
      <div className="grid grid-cols-2 gap-3">
        <Input label="First name" value={form.first_name} onChange={set("first_name")} required />
        <Input label="Last name" value={form.last_name} onChange={set("last_name")} />
      </div>
      <Input
        label="Phone number"
        type="tel"
        placeholder="08031234567"
        value={form.phone}
        onChange={set("phone")}
        error={fieldError("phone")}
        required
      />
      <Input
        label="Email (optional)"
        type="email"
        value={form.email}
        onChange={set("email")}
        error={fieldError("email")}
      />
      <Input
        label="Password"
        type="password"
        value={form.password}
        onChange={set("password")}
        error={fieldError("password")}
        hint="At least 8 characters, not too common."
        required
      />
      <Input
        label="Confirm password"
        type="password"
        value={form.confirm}
        onChange={set("confirm")}
        error={fieldError("confirm")}
        required
      />
      <Button type="submit" fullWidth loading={submitting}>
        {role === "passenger" ? "Create account" : "Sign up to drive"}
      </Button>
      <p className="text-center text-sm text-gray-600">
        Already have an account?{" "}
        <Link href="/login" className="font-semibold text-emerald-600 hover:underline">
          Log in
        </Link>
      </p>
    </form>
  );
}
