/** Customer-support chat: the user's own thread, plus the admin inbox. */
import { api } from "./client";
import type { Paginated, SupportMessage, SupportThread } from "@/types/api";

// ---- signed-in user ----
export function myMessages(): Promise<{ thread_id: number; results: SupportMessage[] }> {
  return api("/support/messages/");
}

export function sendSupportMessage(body: string): Promise<SupportMessage> {
  return api<SupportMessage>("/support/messages/", { method: "POST", body: { body } });
}

// ---- admin ----
export function listSupportThreads(params: {
  page?: number;
  unread?: string;
  search?: string;
}): Promise<Paginated<SupportThread>> {
  const parts = Object.entries(params)
    .filter(([, v]) => v !== undefined && v !== "")
    .map(([k, v]) => `${k}=${encodeURIComponent(String(v))}`);
  return api<Paginated<SupportThread>>(
    `/management/support/threads/${parts.length ? `?${parts.join("&")}` : ""}`
  );
}

export function threadMessages(
  threadId: number
): Promise<{ thread: SupportThread; results: SupportMessage[] }> {
  return api(`/management/support/threads/${threadId}/messages/`);
}

export function replyToThread(threadId: number, body: string): Promise<SupportMessage> {
  return api<SupportMessage>(`/management/support/threads/${threadId}/messages/`, {
    method: "POST",
    body: { body },
  });
}
