"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { AuthPageFrame } from "@/components/auth/AuthPageFrame";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { confirmPasswordReset, requestPasswordReset } from "@/lib/api/auth";
import { ApiError } from "@/lib/api/client";

export default function ForgotPasswordPage() {
  const router = useRouter();
  const [step, setStep] = useState<"request" | "confirm" | "done">("request");
  const [phone, setPhone] = useState("");
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string[]>>({});
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const fieldError = (key: string) => fieldErrors[key]?.join(" ");

  async function sendCode(e: FormEvent) {
    e.preventDefault();
    setError("");
    setFieldErrors({});
    setBusy(true);
    try {
      await requestPasswordReset(phone);
      setStep("confirm");
    } catch (err) {
      if (err instanceof ApiError && Object.keys(err.fieldErrors).length) {
        setFieldErrors(err.fieldErrors);
      } else {
        setError(err instanceof ApiError ? err.message : "Something went wrong. Try again.");
      }
    } finally {
      setBusy(false);
    }
  }

  async function resetPassword(e: FormEvent) {
    e.preventDefault();
    setError("");
    setFieldErrors({});
    if (password !== confirm) {
      setFieldErrors({ confirm: ["Passwords do not match."] });
      return;
    }
    setBusy(true);
    try {
      await confirmPasswordReset(phone, code.trim(), password);
      setStep("done");
    } catch (err) {
      if (err instanceof ApiError && Object.keys(err.fieldErrors).length) {
        setFieldErrors(err.fieldErrors);
      } else {
        setError(
          err instanceof ApiError ? err.message : "Could not reset your password. Try again."
        );
      }
    } finally {
      setBusy(false);
    }
  }

  if (step === "done") {
    return (
      <AuthPageFrame heading="Password reset">
        <div className="space-y-4 text-center">
          <p className="text-4xl">✅</p>
          <p className="text-sm text-gray-600">
            Your password has been reset. You can now log in with your new password.
          </p>
          <Button fullWidth onClick={() => router.replace("/login")}>
            Go to login
          </Button>
        </div>
      </AuthPageFrame>
    );
  }

  if (step === "confirm") {
    return (
      <AuthPageFrame heading="Enter your reset code">
        <form onSubmit={resetPassword} className="space-y-4">
          <Alert tone="info">
            We sent a 6-digit code to <span className="font-semibold">{phone}</span> by SMS. Enter
            it below with your new password.
          </Alert>
          {error && <Alert tone="error">{error}</Alert>}
          <Input
            label="Reset code"
            inputMode="numeric"
            placeholder="6-digit code"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            error={fieldError("code")}
            required
          />
          <Input
            label="New password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            error={fieldError("new_password")}
            hint="At least 8 characters, not too common."
            required
          />
          <Input
            label="Confirm new password"
            type="password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            error={fieldError("confirm")}
            required
          />
          <Button type="submit" fullWidth loading={busy}>
            Reset password
          </Button>
          <button
            type="button"
            onClick={() => {
              setStep("request");
              setCode("");
            }}
            className="w-full text-center text-sm font-semibold text-blue-600 hover:underline"
          >
            Use a different phone number
          </button>
        </form>
      </AuthPageFrame>
    );
  }

  return (
    <AuthPageFrame heading="Reset your password">
      <form onSubmit={sendCode} className="space-y-4">
        <p className="text-sm text-gray-600">
          Enter the phone number on your account. We&apos;ll send you a code to reset your
          password.
        </p>
        {error && <Alert tone="error">{error}</Alert>}
        <Input
          label="Phone number"
          type="tel"
          placeholder="08031234567"
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
          error={fieldError("phone")}
          required
        />
        <Button type="submit" fullWidth loading={busy}>
          Send reset code
        </Button>
        <p className="text-center text-sm text-gray-600">
          Remembered it?{" "}
          <Link href="/login" className="font-semibold text-blue-600 hover:underline">
            Back to login
          </Link>
        </p>
      </form>
    </AuthPageFrame>
  );
}
