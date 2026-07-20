"use client";

import { useCallback, useEffect, useState } from "react";

import { ChatThread } from "@/components/support/ChatThread";
import { SupportContactCard } from "@/components/support/SupportContactCard";
import { Alert } from "@/components/ui/Alert";
import { Card } from "@/components/ui/Card";
import { ApiError } from "@/lib/api/client";
import { myMessages, sendSupportMessage } from "@/lib/api/support";
import { useRideSocket } from "@/lib/hooks/useRideSocket";
import { playBeep } from "@/lib/sound";
import type { SupportMessage } from "@/types/api";

/** Live chat with the IJ Ride support team, plus call/WhatsApp shortcuts. */
export default function SupportPage() {
  const [messages, setMessages] = useState<SupportMessage[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const data = await myMessages();
      setMessages(data.results);
      setError("");
    } catch {
      setError("Could not load your messages. Pull down to retry or call us instead.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  // Live: an admin reply arrives on the user's own socket group
  useRideSocket((event) => {
    if (event.type !== "support.message") return;
    setMessages((prev) =>
      prev.some((m) => m.id === event.message.id) ? prev : [...prev, event.message]
    );
    if (event.message.from_admin) playBeep("normal");
  });

  async function send(body: string) {
    try {
      const sent = await sendSupportMessage(body);
      setMessages((prev) => (prev.some((m) => m.id === sent.id) ? prev : [...prev, sent]));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Message not sent. Try again.");
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-bold text-gray-900">Help &amp; support</h2>
        <p className="text-sm text-gray-600">
          Chat with our team — we usually reply within a few minutes.
        </p>
      </div>

      {error && <Alert tone="error">{error}</Alert>}

      <Card className="flex h-[26rem] flex-col p-3">
        <ChatThread
          messages={messages}
          mine={(m) => !m.from_admin}
          onSend={send}
          loading={loading}
          emptyText="No messages yet. Send us a message and we'll get right back to you."
          placeholder="Describe your issue…"
        />
      </Card>

      <SupportContactCard />
    </div>
  );
}
