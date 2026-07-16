"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";

import { AuthPageFrame } from "@/components/auth/AuthPageFrame";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { ImageMarquee } from "@/components/ui/ImageMarquee";
import { Input } from "@/components/ui/Input";
import { ApiError } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/AuthContext";
import { homeFor } from "@/lib/auth/routes";

export default function LoginPage() {
  const { login, user, loading } = useAuth();
  const router = useRouter();

  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // Already signed in? Straight to the dashboard.
  useEffect(() => {
    if (!loading && user) router.replace(homeFor(user.role));
  }, [user, loading, router]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const me = await login(phone, password);
      router.replace(homeFor(me.role));
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 401
          ? "Wrong phone number or password."
          : err instanceof ApiError
            ? err.message
            : "Could not reach the server. Is it running?"
      );
      setSubmitting(false);
    }
  }

  return (
    <AuthPageFrame heading="Log in to continue" below={<ImageMarquee />}>
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && <Alert tone="error">{error}</Alert>}
        <Input
          label="Phone number or email"
          type="text"
          autoComplete="username"
          placeholder="08031234567 or you@email.com"
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
          required
        />
        <Input
          label="Password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        <div className="text-right">
          <Link
            href="/forgot-password"
            className="text-sm font-semibold text-blue-600 hover:underline"
          >
            Forgot password?
          </Link>
        </div>
        <Button type="submit" fullWidth loading={submitting}>
          Log in
        </Button>
        <div className="space-y-1 text-center text-sm text-gray-600">
          <p>
            New here?{" "}
            <Link href="/register" className="font-semibold text-blue-600 hover:underline">
              Create a passenger account
            </Link>
          </p>
          <p>
            Want to drive?{" "}
            <Link
              href="/register/driver"
              className="font-semibold text-blue-600 hover:underline"
            >
              Sign up as a driver
            </Link>
          </p>
        </div>
      </form>
    </AuthPageFrame>
  );
}
