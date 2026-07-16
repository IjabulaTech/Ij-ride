"use client";

import { useState } from "react";

import { Pagination, Table, Td } from "@/components/admin/Table";
import { Alert } from "@/components/ui/Alert";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Spinner";
import { listUsers, verifyNin } from "@/lib/api/admin";
import { formatDateTime } from "@/lib/format";
import { usePaged } from "@/lib/hooks/usePaged";

const ROLE_TONES = { PASSENGER: "blue", DRIVER: "green", ADMIN: "gray" } as const;

export default function AdminUsersPage() {
  const [role, setRole] = useState("");
  const [search, setSearch] = useState("");
  const [applied, setApplied] = useState({ role: "", search: "" });
  // Optimistic per-row NIN status after an admin toggles it (avoids a full reload)
  const [ninOverrides, setNinOverrides] = useState<Record<number, boolean>>({});
  const [ninBusyId, setNinBusyId] = useState<number | null>(null);

  async function toggleNin(userId: number, verified: boolean) {
    setNinBusyId(userId);
    try {
      const res = await verifyNin(userId, verified);
      setNinOverrides((prev) => ({ ...prev, [userId]: res.nin_verified }));
    } catch {
      /* leave as-is on failure */
    } finally {
      setNinBusyId(null);
    }
  }

  const { data, page, setPage, loading, error } = usePaged(
    (p) => listUsers({ page: p, role: applied.role, search: applied.search }),
    JSON.stringify(applied)
  );

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-2">
        <h2 className="mr-auto text-lg font-bold text-gray-900">Users</h2>
        <select
          value={role}
          onChange={(e) => setRole(e.target.value)}
          className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm"
        >
          <option value="">All roles</option>
          <option value="PASSENGER">Passengers</option>
          <option value="DRIVER">Drivers</option>
          <option value="ADMIN">Admins</option>
        </select>
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search phone, name, email…"
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
        />
        <button
          onClick={() => setApplied({ role, search })}
          className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white"
        >
          Filter
        </button>
      </div>

      {error && <Alert tone="error">{error}</Alert>}
      {loading || !data ? (
        <div className="flex justify-center py-16 text-emerald-600">
          <Spinner size="lg" />
        </div>
      ) : (
        <>
          <Table head={["Phone", "Name", "Email", "Role", "NIN", "Status", "Joined"]}>
            {data.results.map((user) => {
              const ninVerified = ninOverrides[user.id] ?? user.nin_verified;
              return (
                <tr key={user.id}>
                  <Td className="font-mono text-xs">{user.phone}</Td>
                  <Td>{[user.first_name, user.last_name].filter(Boolean).join(" ") || "—"}</Td>
                  <Td>{user.email || "—"}</Td>
                  <Td>
                    <Badge tone={ROLE_TONES[user.role]}>{user.role}</Badge>
                  </Td>
                  <Td>
                    {user.nin ? (
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs">{user.nin}</span>
                        {ninVerified ? (
                          <Badge tone="green">Verified</Badge>
                        ) : (
                          <Button
                            variant="secondary"
                            loading={ninBusyId === user.id}
                            onClick={() => toggleNin(user.id, true)}
                            className="px-2 py-1 text-xs"
                          >
                            Verify
                          </Button>
                        )}
                      </div>
                    ) : (
                      <span className="text-xs text-gray-400">—</span>
                    )}
                  </Td>
                  <Td>
                    <Badge tone={user.is_active ? "green" : "red"}>
                      {user.is_active ? "Active" : "Disabled"}
                    </Badge>
                  </Td>
                  <Td className="text-xs text-gray-500">{formatDateTime(user.date_joined)}</Td>
                </tr>
              );
            })}
          </Table>
          <Pagination page={page} count={data.count} onPage={setPage} />
        </>
      )}
    </div>
  );
}
