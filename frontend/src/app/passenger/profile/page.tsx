"use client";

import { useState, type FormEvent } from "react";

import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { ApiError } from "@/lib/api/client";
import { updateMe } from "@/lib/api/auth";
import { useAuth } from "@/lib/auth/AuthContext";
import { PAYMENT_METHOD_LABELS } from "@/lib/format";
import type { PassengerProfile, PaymentMethod } from "@/types/api";

export default function ProfilePage() {
  const { user, refreshUser } = useAuth();
  const profile = user?.profile as PassengerProfile | null;

  const [firstName, setFirstName] = useState(user?.first_name ?? "");
  const [lastName, setLastName] = useState(user?.last_name ?? "");
  const [email, setEmail] = useState(user?.email ?? "");
  const [method, setMethod] = useState<PaymentMethod>(
    profile?.default_payment_method ?? "CASH"
  );
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ tone: "success" | "error"; text: string } | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setMessage(null);
    try {
      await updateMe({
        first_name: firstName,
        last_name: lastName,
        email,
        default_payment_method: method,
      });
      await refreshUser();
      setMessage({ tone: "success", text: "Profile updated." });
    } catch (err) {
      setMessage({
        tone: "error",
        text: err instanceof ApiError ? err.message : "Could not save. Try again.",
      });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-bold text-gray-900">Your profile</h2>
      <Card>
        <form onSubmit={handleSubmit} className="space-y-4">
          {message && <Alert tone={message.tone}>{message.text}</Alert>}
          <Input label="Phone number" value={user?.phone ?? ""} disabled hint="Phone numbers can't be changed." />
          <div className="grid grid-cols-2 gap-3">
            <Input
              label="First name"
              value={firstName}
              onChange={(e) => setFirstName(e.target.value)}
            />
            <Input
              label="Last name"
              value={lastName}
              onChange={(e) => setLastName(e.target.value)}
            />
          </div>
          <Input
            label="Email (optional)"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <div>
            <p className="mb-2 text-sm font-medium text-gray-700">Default payment method</p>
            <div className="grid grid-cols-2 gap-2">
              {(Object.keys(PAYMENT_METHOD_LABELS) as PaymentMethod[]).map((m) => (
                <button
                  key={m}
                  type="button"
                  onClick={() => setMethod(m)}
                  className={`rounded-lg border px-3 py-2.5 text-sm font-semibold ${
                    method === m
                      ? "border-emerald-600 bg-emerald-50 text-emerald-700"
                      : "border-gray-300 bg-white text-gray-700"
                  }`}
                >
                  {PAYMENT_METHOD_LABELS[m]}
                </button>
              ))}
            </div>
          </div>
          <Button type="submit" fullWidth loading={busy}>
            Save changes
          </Button>
        </form>
      </Card>
    </div>
  );
}
