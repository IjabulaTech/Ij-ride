"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import * as authApi from "@/lib/api/auth";
import { clearTokens, getAccessToken, getRefreshToken, setTokens } from "@/lib/auth/tokens";
import type { Me } from "@/types/api";

interface AuthContextValue {
  user: Me | null;
  /** True while the initial session restore is in flight. */
  loading: boolean;
  login: (phone: string, password: string) => Promise<Me>;
  registerPassenger: (data: authApi.RegisterData) => Promise<Me>;
  registerDriver: (data: authApi.RegisterData) => Promise<Me>;
  logout: () => void;
  refreshUser: () => Promise<Me | null>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (!getAccessToken() && !getRefreshToken()) {
        setLoading(false);
        return;
      }
      try {
        const current = await authApi.me();
        if (!cancelled) setUser(current);
      } catch {
        clearTokens();
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const finishAuth = useCallback(async (tokens: { access: string; refresh: string }) => {
    setTokens(tokens);
    const current = await authApi.me();
    setUser(current);
    return current;
  }, []);

  const login = useCallback(
    async (phone: string, password: string) => {
      const data = await authApi.login(phone, password);
      return finishAuth(data);
    },
    [finishAuth]
  );

  const registerPassenger = useCallback(
    async (data: authApi.RegisterData) => finishAuth(await authApi.registerPassenger(data)),
    [finishAuth]
  );

  const registerDriver = useCallback(
    async (data: authApi.RegisterData) => finishAuth(await authApi.registerDriver(data)),
    [finishAuth]
  );

  const logout = useCallback(() => {
    clearTokens();
    setUser(null);
  }, []);

  const refreshUser = useCallback(async () => {
    try {
      const current = await authApi.me();
      setUser(current);
      return current;
    } catch {
      return null;
    }
  }, []);

  const value = useMemo(
    () => ({ user, loading, login, registerPassenger, registerDriver, logout, refreshUser }),
    [user, loading, login, registerPassenger, registerDriver, logout, refreshUser]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
