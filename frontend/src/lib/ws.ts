/** WebSocket client for /ws/rides/. Auto-reconnects with backoff (except on
 * auth failure), keeps the connection alive with pings, and fans messages
 * out to subscribers. Used by the passenger (Module 10) and driver
 * (Module 11) screens. */
import { getAccessToken } from "@/lib/auth/tokens";
import type { OpenRide, Ride, SupportMessage } from "@/types/api";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? "ws://127.0.0.1:8000/ws/rides/";
const CLOSE_UNAUTHORIZED = 4401;
const PING_INTERVAL_MS = 30_000;
const MAX_RETRY_MS = 30_000;

export type ServerMessage =
  | { type: "connection.ready"; dispatch: boolean }
  | { type: "pong" }
  | { type: "ride.event"; event: string; ride: Ride }
  | { type: "dispatch.new_request"; ride: OpenRide }
  | { type: "dispatch.request_closed"; ride_id: number }
  | { type: "dispatch.subscribed" }
  | { type: "dispatch.unsubscribed" }
  | { type: "support.message"; message: SupportMessage; thread_id: number; user_id: number }
  | { type: "error"; detail: string };

type Listener = (message: ServerMessage) => void;

export class RideSocket {
  private ws: WebSocket | null = null;
  private listeners = new Set<Listener>();
  private closedByUser = false;
  private retryMs = 1_000;
  private pingTimer: ReturnType<typeof setInterval> | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;

  connect(): void {
    this.closedByUser = false;
    this.open();
  }

  on(listener: Listener): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  send(action: string): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ action }));
    }
  }

  subscribeDispatch(): void {
    this.send("subscribe_dispatch");
  }

  unsubscribeDispatch(): void {
    this.send("unsubscribe_dispatch");
  }

  close(): void {
    this.closedByUser = true;
    this.stopTimers();
    this.ws?.close();
    this.ws = null;
  }

  private open(): void {
    const token = getAccessToken();
    if (!token || typeof window === "undefined") return;

    const ws = new WebSocket(`${WS_URL}?token=${encodeURIComponent(token)}`);
    this.ws = ws;

    ws.onopen = () => {
      this.retryMs = 1_000;
      this.pingTimer = setInterval(() => this.send("ping"), PING_INTERVAL_MS);
    };

    ws.onmessage = (event) => {
      let message: ServerMessage;
      try {
        message = JSON.parse(event.data as string) as ServerMessage;
      } catch {
        return;
      }
      this.listeners.forEach((listener) => listener(message));
    };

    ws.onclose = (event) => {
      this.stopTimers();
      if (this.closedByUser || event.code === CLOSE_UNAUTHORIZED) return;
      this.reconnectTimer = setTimeout(() => this.open(), this.retryMs);
      this.retryMs = Math.min(this.retryMs * 2, MAX_RETRY_MS);
    };
  }

  private stopTimers(): void {
    if (this.pingTimer) clearInterval(this.pingTimer);
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.pingTimer = null;
    this.reconnectTimer = null;
  }
}
