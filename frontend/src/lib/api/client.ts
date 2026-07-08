/** Fetch wrapper: base URL, Bearer auth, single-flight token refresh on 401,
 * and DRF error normalization. All API modules go through api(). */
import { clearTokens, getAccessToken, getRefreshToken, setTokens } from "@/lib/auth/tokens";

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public fieldErrors: Record<string, string[]> = {}
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function normalizeError(status: number, data: unknown): ApiError {
  if (data && typeof data === "object") {
    const record = data as Record<string, unknown>;
    if (typeof record.detail === "string") return new ApiError(status, record.detail);

    const fieldErrors: Record<string, string[]> = {};
    const messages: string[] = [];
    for (const [field, value] of Object.entries(record)) {
      const list = Array.isArray(value) ? value.map(String) : [String(value)];
      fieldErrors[field] = list;
      messages.push(field === "non_field_errors" ? list.join(" ") : `${field}: ${list.join(" ")}`);
    }
    if (messages.length) return new ApiError(status, messages.join(" · "), fieldErrors);
  }
  return new ApiError(status, `Request failed (${status}).`);
}

let refreshInFlight: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  const refresh = getRefreshToken();
  if (!refresh) return null;
  try {
    const resp = await fetch(`${BASE_URL}/auth/token/refresh/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh }),
    });
    if (!resp.ok) {
      clearTokens();
      return null;
    }
    const data = (await resp.json()) as { access: string; refresh?: string };
    setTokens({ access: data.access, refresh: data.refresh ?? refresh });
    return data.access;
  } catch {
    return null;
  }
}

export interface ApiOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  /** Set false for anonymous endpoints (login/register). */
  auth?: boolean;
}

export async function api<T>(path: string, options: ApiOptions = {}): Promise<T> {
  const { method = "GET", body, auth = true } = options;

  // FormData bodies (file uploads) go through as-is — the browser sets the
  // multipart boundary header itself.
  const isForm = typeof FormData !== "undefined" && body instanceof FormData;

  const doFetch = (token: string | null) =>
    fetch(`${BASE_URL}${path}`, {
      method,
      headers: {
        ...(body !== undefined && !isForm ? { "Content-Type": "application/json" } : {}),
        ...(auth && token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: isForm ? (body as FormData) : body !== undefined ? JSON.stringify(body) : undefined,
    });

  let resp = await doFetch(getAccessToken());

  if (resp.status === 401 && auth && getRefreshToken()) {
    refreshInFlight = refreshInFlight ?? refreshAccessToken();
    const fresh = await refreshInFlight;
    refreshInFlight = null;
    if (fresh) resp = await doFetch(fresh);
  }

  if (resp.status === 204) return undefined as T;
  const data: unknown = await resp.json().catch(() => null);
  if (!resp.ok) throw normalizeError(resp.status, data);
  return data as T;
}
