"use client";

import { useEffect, useState } from "react";
import { ShieldOff, UserPlus, Users } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { getSupabaseBrowserClient } from "@/lib/supabase-browser";
import { cn } from "@/lib/utils";

interface MemberRow {
  user_id: string;
  role: string;
  created_at: string;
}

export function TeamMembers() {
  const [members, setMembers] = useState<MemberRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("member");
  const [info, setInfo] = useState<string | null>(null);

  useEffect(() => {
    void load();
  }, []);

  const load = async () => {
    setLoading(true);
    const sb = getSupabaseBrowserClient();
    const { data } = await sb
      .from("tenant_members")
      .select("user_id, role, created_at")
      .order("created_at", { ascending: true });
    setMembers(data ?? []);
    setLoading(false);
  };

  const invite = (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim()) return;
    // Stub: el flujo real es Supabase Admin → Auth → Invite + insert manual
    // en tenant_members. Sin SUPABASE_SERVICE_ROLE_KEY en frontend, esto
    // tiene que pasar por un endpoint del API. Marcamos como pendiente.
    setInfo(
      `Pendiente: el invite real necesita un endpoint en el API que use service_role. ` +
        `De momento, da de alta a ${email} a mano en Supabase Studio → Authentication → Add user.`,
    );
    setEmail("");
  };

  return (
    <div className="space-y-6 p-6">
      <header className="flex items-center justify-between border-b border-border/60 pb-4">
        <div className="flex items-center gap-3">
          <Users className="h-4 w-4 text-secondary" />
          <span className="label-eyebrow">Equipo · Globalizame</span>
        </div>
        <span className="text-[11px] tracking-wider text-muted-foreground">
          Solo emails autorizados acceden a Cazador
        </span>
      </header>

      {/* Invitar */}
      <form
        onSubmit={invite}
        className="grid grid-cols-1 gap-px bg-border/40 border border-border/60 md:grid-cols-[1fr_160px_auto]"
      >
        <div className="bg-card p-3">
          <span className="label-eyebrow">email</span>
          <Input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="nuevo@globalizame.com"
            className={cn(
              "h-9 rounded-none border-0 border-b border-border/0 bg-transparent px-0 text-sm shadow-none",
              "focus-visible:border-primary focus-visible:ring-0",
            )}
          />
        </div>
        <div className="bg-card p-3">
          <span className="label-eyebrow">rol</span>
          <Select value={role} onValueChange={(v) => v !== null && setRole(v)}>
            <SelectTrigger className="h-9 rounded-none border-0 border-b border-border/0 bg-transparent px-0 text-sm shadow-none focus:ring-0">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="rounded-none border-border">
              <SelectItem value="admin" className="rounded-none">admin</SelectItem>
              <SelectItem value="member" className="rounded-none">member</SelectItem>
              <SelectItem value="viewer" className="rounded-none">viewer</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="bg-card p-3 flex items-end justify-end">
          <Button
            type="submit"
            className="h-9 rounded-none bg-primary text-[11px] uppercase tracking-wider"
          >
            <UserPlus className="mr-1.5 h-3.5 w-3.5" />
            Invitar
          </Button>
        </div>
      </form>

      {info && (
        <div className="flex items-start gap-2 border border-[var(--warning)]/40 bg-[var(--warning)]/[0.06] px-4 py-3 text-[12px] text-[var(--warning)]">
          <ShieldOff className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{info}</span>
        </div>
      )}

      {/* Tabla de miembros */}
      <div className="border border-border/60">
        <header className="flex items-center justify-between border-b border-border/60 bg-background/40 px-4 py-2 text-[11px] tracking-wider text-muted-foreground">
          <span>{loading ? "cargando…" : `${members.length} miembros`}</span>
        </header>
        {members.length === 0 ? (
          <div className="p-8 text-center">
            <p className="label-eyebrow mb-2">aún solo tú</p>
            <p className="text-sm text-muted-foreground">
              Da de alta a tu equipo en Supabase Studio → Authentication, luego
              añádelos a este tenant con el botón de arriba (cuando esté listo).
            </p>
          </div>
        ) : (
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b border-border/40 bg-background/40">
                <th className="px-4 py-2 text-left">
                  <span className="label-eyebrow">user_id</span>
                </th>
                <th className="px-4 py-2 text-left">
                  <span className="label-eyebrow">rol</span>
                </th>
                <th className="px-4 py-2 text-left">
                  <span className="label-eyebrow">alta</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {members.map((m) => (
                <tr key={m.user_id} className="border-b border-border/30">
                  <td className="px-4 py-2 font-mono text-[12px] text-muted-foreground">
                    {m.user_id.slice(0, 8)}…
                  </td>
                  <td className="px-4 py-2">
                    <Badge
                      variant="outline"
                      className={cn(
                        "rounded-none bg-transparent font-mono text-[10px] uppercase tracking-wider",
                        m.role === "admin"
                          ? "border-primary text-primary"
                          : "border-border text-muted-foreground",
                      )}
                    >
                      {m.role}
                    </Badge>
                  </td>
                  <td className="px-4 py-2 font-mono text-[11px] tabular-nums text-muted-foreground">
                    {m.created_at.split("T")[0]}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
