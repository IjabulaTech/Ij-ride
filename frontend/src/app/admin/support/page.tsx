"use client";

import { useCallback, useEffect, useState } from "react";

import { ChatThread } from "@/components/support/ChatThread";
import { Alert } from "@/components/ui/Alert";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { listSupportThreads, replyToThread, threadMessages } from "@/lib/api/support";
import { formatDateTime } from "@/lib/format";
import { useRideSocket } from "@/lib/hooks/useRideSocket";
import { playBeep } from "@/lib/sound";
import type { SupportMessage, SupportThread } from "@/types/api";

const POLL_MS = 20_000;

export default function AdminSupportPage() {
  const [threads, setThreads] = useState<SupportThread[]>([]);
  const [selected, setSelected] = useState<SupportThread | null>(null);
  const [messages, setMessages] = useState<SupportMessage[]>([]);
  const [onlyUnread, setOnlyUnread] = useState(false);
  const [loadingThreads, setLoadingThreads] = useState(true);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [error, setError] = useState("");

  const loadThreads = useCallback(async () => {
    try {
      const data = await listSupportThreads({ unread: onlyUnread ? "true" : "" });
      setThreads(data.results);
      setError("");
    } catch {
      setError("Could not load support threads.");
    } finally {
      setLoadingThreads(false);
    }
  }, [onlyUnread]);

  useEffect(() => {
    setLoadingThreads(true);
    loadThreads();
    const timer = setInterval(loadThreads, POLL_MS);
    return () => clearInterval(timer);
  }, [loadThreads]);

  const openThread = useCallback(async (thread: SupportThread) => {
    setSelected(thread);
    setLoadingMessages(true);
    try {
      const data = await threadMessages(thread.id);
      setMessages(data.results);
      // Clearing the badge locally mirrors the server marking it read
      setThreads((prev) =>
        prev.map((t) => (t.id === thread.id ? { ...t, unread_for_admin: 0 } : t))
      );
    } catch {
      setError("Could not open that conversation.");
    } finally {
      setLoadingMessages(false);
    }
  }, []);

  // Live: every support message reaches admins via the shared inbox group
  useRideSocket((event) => {
    if (event.type !== "support.message") return;
    if (selected && event.thread_id === selected.id) {
      setMessages((prev) =>
        prev.some((m) => m.id === event.message.id) ? prev : [...prev, event.message]
      );
    }
    if (!event.message.from_admin) playBeep("alert");
    loadThreads();
  });

  async function send(body: string) {
    if (!selected) return;
    const sent = await replyToThread(selected.id, body);
    setMessages((prev) => (prev.some((m) => m.id === sent.id) ? prev : [...prev, sent]));
    loadThreads();
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <h2 className="mr-auto text-lg font-bold text-gray-900">Support inbox</h2>
        <label className="flex items-center gap-2 text-sm text-gray-600">
          <input
            type="checkbox"
            checked={onlyUnread}
            onChange={(e) => setOnlyUnread(e.target.checked)}
            className="h-4 w-4 rounded border-gray-300"
          />
          Unread only
        </label>
      </div>

      {error && <Alert tone="error">{error}</Alert>}

      <div className="grid gap-4 lg:grid-cols-[20rem_1fr]">
        {/* Conversations */}
        <Card className="max-h-[32rem] overflow-y-auto p-0">
          {loadingThreads ? (
            <div className="flex justify-center py-10 text-blue-600">
              <Spinner size="md" />
            </div>
          ) : threads.length === 0 ? (
            <p className="p-4 text-sm text-gray-500">No conversations yet.</p>
          ) : (
            <ul className="divide-y divide-gray-100">
              {threads.map((t) => (
                <li key={t.id}>
                  <button
                    type="button"
                    onClick={() => openThread(t)}
                    className={`block w-full px-4 py-3 text-left hover:bg-gray-50 ${
                      selected?.id === t.id ? "bg-blue-50" : ""
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate font-medium text-gray-900">{t.name}</span>
                      {t.unread_for_admin > 0 && (
                        <Badge tone="red">{t.unread_for_admin}</Badge>
                      )}
                    </div>
                    <p className="truncate text-xs text-gray-500">
                      {t.last_message_preview || "No messages yet"}
                    </p>
                    <p className="mt-0.5 text-[11px] text-gray-400">
                      {t.role} · {t.phone}
                      {t.last_message_at ? ` · ${formatDateTime(t.last_message_at)}` : ""}
                    </p>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </Card>

        {/* Conversation */}
        <Card className="flex h-[32rem] flex-col p-3">
          {selected ? (
            <>
              <div className="mb-2 border-b border-gray-100 pb-2">
                <p className="font-semibold text-gray-900">{selected.name}</p>
                <p className="font-mono text-xs text-gray-500">{selected.phone}</p>
              </div>
              <ChatThread
                messages={messages}
                mine={(m) => m.from_admin}
                onSend={send}
                loading={loadingMessages}
                emptyText="No messages in this conversation yet."
                placeholder="Reply as IJ Ride Support…"
              />
            </>
          ) : (
            <p className="m-auto text-sm text-gray-500">
              Select a conversation to read and reply.
            </p>
          )}
        </Card>
      </div>
    </div>
  );
}
