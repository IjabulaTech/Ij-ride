"use client";

import { useEffect, useState } from "react";

import { Alert } from "@/components/ui/Alert";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { ApiError } from "@/lib/api/client";
import { getMaintenance, setMaintenance } from "@/lib/api/ops";

/** Admin on/off switch. Takes effect immediately — no redeploy. */
export function MaintenanceCard() {
  const [on, setOn] = useState(false);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState<{ tone: "success" | "error"; text: string } | null>(null);

  useEffect(() => {
    getMaintenance()
      .then((s) => {
        setOn(s.maintenance);
        setMessage(s.message);
      })
      .catch(() => setNote({ tone: "error", text: "Could not load maintenance status." }))
      .finally(() => setLoading(false));
  }, []);

  async function toggle(next: boolean) {
    setBusy(true);
    setNote(null);
    try {
      const s = await setMaintenance(next, message);
      setOn(s.maintenance);
      setMessage(s.message);
      setNote({
        tone: "success",
        text: next
          ? "Maintenance mode is ON — passengers and drivers now see the notice."
          : "Maintenance mode is OFF — the app is live again.",
      });
    } catch (err) {
      setNote({
        tone: "error",
        text: err instanceof ApiError ? err.message : "Could not update maintenance mode.",
      });
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card className="space-y-3">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h3 className="font-semibold text-gray-900">Maintenance mode</h3>
          <p className="text-sm text-gray-600">
            Pauses the app for passengers and drivers while you work. Admins keep full access.
          </p>
        </div>
        <Badge tone={on ? "red" : "green"}>{loading ? "…" : on ? "ON" : "Off"}</Badge>
      </div>

      {note && <Alert tone={note.tone}>{note.text}</Alert>}

      <Input
        label="Message shown to users"
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        placeholder="We'll be back shortly…"
        hint="Saved when you switch it on."
        disabled={loading}
      />

      {on ? (
        <Button fullWidth loading={busy} disabled={loading} onClick={() => toggle(false)}>
          Turn OFF — put the app back live
        </Button>
      ) : (
        <Button
          fullWidth
          variant="danger"
          loading={busy}
          disabled={loading}
          onClick={() => toggle(true)}
        >
          Turn ON maintenance mode
        </Button>
      )}
    </Card>
  );
}
