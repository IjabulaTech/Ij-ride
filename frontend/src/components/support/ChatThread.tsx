"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";

import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Spinner";
import type { SupportMessage } from "@/types/api";

function timeLabel(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

/** Message list + composer. `mine` decides which side a bubble sits on, so the
 * same component serves the user's view and the admin's view. */
export function ChatThread({
  messages,
  mine,
  onSend,
  loading,
  emptyText,
  placeholder = "Type your message…",
  disabled = false,
}: {
  messages: SupportMessage[];
  mine: (m: SupportMessage) => boolean;
  onSend: (body: string) => Promise<void>;
  loading?: boolean;
  emptyText: string;
  placeholder?: string;
  disabled?: boolean;
}) {
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const endRef = useRef<HTMLDivElement | null>(null);

  // Keep the newest message in view as the conversation grows
  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [messages.length]);

  async function submit(e: FormEvent) {
    e.preventDefault();
    const body = draft.trim();
    if (!body || sending) return;
    setSending(true);
    try {
      await onSend(body);
      setDraft("");
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="min-h-56 flex-1 space-y-2 overflow-y-auto rounded-lg border border-gray-200 bg-gray-50 p-3">
        {loading ? (
          <div className="flex justify-center py-8 text-blue-600">
            <Spinner size="md" />
          </div>
        ) : messages.length === 0 ? (
          <p className="py-8 text-center text-sm text-gray-500">{emptyText}</p>
        ) : (
          messages.map((m) => {
            const isMine = mine(m);
            return (
              <div key={m.id} className={`flex ${isMine ? "justify-end" : "justify-start"}`}>
                <div
                  className={`max-w-[80%] rounded-2xl px-3 py-2 text-sm ${
                    isMine
                      ? "rounded-br-sm bg-blue-600 text-white"
                      : "rounded-bl-sm border border-gray-200 bg-white text-gray-900"
                  }`}
                >
                  {!isMine && (
                    <p className="mb-0.5 text-xs font-semibold text-gray-500">{m.sender_name}</p>
                  )}
                  <p className="whitespace-pre-wrap break-words">{m.body}</p>
                  <p
                    className={`mt-1 text-right text-[10px] ${
                      isMine ? "text-blue-100" : "text-gray-400"
                    }`}
                  >
                    {timeLabel(m.created_at)}
                  </p>
                </div>
              </div>
            );
          })
        )}
        <div ref={endRef} />
      </div>

      <form onSubmit={submit} className="mt-2 flex items-end gap-2">
        <textarea
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              submit(e as unknown as FormEvent);
            }
          }}
          rows={1}
          placeholder={placeholder}
          disabled={disabled}
          aria-label="Message"
          className="max-h-32 min-h-[42px] flex-1 resize-y rounded-lg border border-gray-300 px-3 py-2.5 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <Button type="submit" loading={sending} disabled={disabled || !draft.trim()}>
          Send
        </Button>
      </form>
    </div>
  );
}
