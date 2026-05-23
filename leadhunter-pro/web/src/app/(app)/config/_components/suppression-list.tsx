"use client";

import { useEffect, useState } from "react";
import { Plus, ShieldOff, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { getSupabaseBrowserClient } from "@/lib/supabase-browser";
import { cn } from "@/lib/utils";

interface SuppressionRow {
  channel: string;
  identifier: string;
  reason: string;
  notes: string | null;
  created_at: string;
}

const REASON_LABELS: Record<string, string> = {
  user_unsubscribed: "baja",
  hard_bounce: "bounce",
  spam_complaint: "spam",
  gdpr_erase: "GDPR",
  manual: "manual",
  imported: "import",
};

export function SuppressionList() {
  const [rows, setRows] = useState<SuppressionRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [channel, setChannel] = useState("email");
  const [identifier, setIdentifier] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void load();
  }, []);

  const load = async () => {
    setLoading(true);
    const sb = getSupabaseBrowserClient();
    const { data, error } = await sb
      .from("suppression")
      .select("channel, identifier, reason, notes, created_at")
      .order("created_at", { ascending: false })
      .limit(200);
    setRows(data ?? []);
    if (error) setError(error.message);
    setLoading(false);
  };

  const addManual = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!identifier.trim()) return;
    setError(null);
    const sb = getSupabaseBrowserClient();
    const tenant = await sb.from("tenants").select("id").eq("slug", "globalizame").maybeSingle();
    if (!tenant.data) {
      setError("Tenant 'globalizame' no encontrado en BD.");
      return;
    }
    const { error: insErr } = await sb.from("suppression").insert({
      tenant_id: tenant.data.id,
      channel,
      identifier: identifier.trim(),
      reason: "manual",
    });
    if (insErr) {
      setError(insErr.message);
      return;
    }
    setIdentifier("");
    void load();
  };

  const remove = async (row: SuppressionRow) => {
    const sb = getSupabaseBrowserClient();
    await sb
      .from("suppression")
      .delete()
      .eq("channel", row.channel)
      .eq("identifier", row.identifier);
    void load();
  };

  return (
    <div className="space-y-6 p-6">
      <header className="flex items-center justify-between border-b border-border/60 pb-4">
        <div className="flex items-center gap-3">
          <ShieldOff className="h-4 w-4 text-secondary" />
          <span className="label-eyebrow">Suppression · cross-canal</span>
        </div>
        <span className="text-[11px] tracking-wider text-muted-foreground">
          GDPR + LSSI · una baja es para siempre
        </span>
      </header>

      {/* Añadir manual */}
      <form
        onSubmit={addManual}
        className="grid grid-cols-1 gap-px bg-border/40 border border-border/60 md:grid-cols-[160px_1fr_auto]"
      >
        <div className="bg-card p-3">
          <span className="label-eyebrow">canal</span>
          <Select value={channel} onValueChange={(v) => v !== null && setChannel(v)}>
            <SelectTrigger className="h-9 rounded-none border-0 border-b border-border/0 bg-transparent px-0 text-sm shadow-none focus:ring-0">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="rounded-none border-border">
              <SelectItem value="email" className="rounded-none">email</SelectItem>
              <SelectItem value="whatsapp" className="rounded-none">whatsapp</SelectItem>
              <SelectItem value="phone" className="rounded-none">teléfono</SelectItem>
              <SelectItem value="nif" className="rounded-none">NIF</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="bg-card p-3">
          <span className="label-eyebrow">identificador</span>
          <Input
            value={identifier}
            onChange={(e) => setIdentifier(e.target.value)}
            placeholder="email, teléfono o NIF…"
            className={cn(
              "h-9 rounded-none border-0 border-b border-border/0 bg-transparent px-0 text-sm shadow-none",
              "focus-visible:border-primary focus-visible:ring-0",
            )}
          />
        </div>
        <div className="bg-card p-3 flex items-end justify-end">
          <Button
            type="submit"
            className="h-9 rounded-none bg-primary text-[11px] uppercase tracking-wider"
          >
            <Plus className="mr-1.5 h-3.5 w-3.5" />
            Añadir
          </Button>
        </div>
      </form>

      {error && (
        <div className="border border-destructive/40 bg-destructive/[0.06] px-4 py-2 text-[12px] text-destructive">
          {error}
        </div>
      )}

      {/* Tabla */}
      <div className="border border-border/60">
        <header className="flex items-center justify-between border-b border-border/60 bg-background/40 px-4 py-2 text-[11px] tracking-wider text-muted-foreground">
          <span>{loading ? "cargando…" : `${rows.length} entradas`}</span>
        </header>
        {rows.length === 0 ? (
          <p className="p-8 text-center text-sm text-muted-foreground">
            {loading ? "—" : "Lista vacía. Bien."}
          </p>
        ) : (
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b border-border/40 bg-background/40">
                <th className="px-4 py-2 text-left">
                  <span className="label-eyebrow">canal</span>
                </th>
                <th className="px-4 py-2 text-left">
                  <span className="label-eyebrow">identificador</span>
                </th>
                <th className="px-4 py-2 text-left">
                  <span className="label-eyebrow">razón</span>
                </th>
                <th className="px-4 py-2 text-left">
                  <span className="label-eyebrow">fecha</span>
                </th>
                <th className="w-10" />
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={`${r.channel}-${r.identifier}`} className="border-b border-border/30">
                  <td className="px-4 py-2 font-mono text-[12px] text-muted-foreground">
                    {r.channel}
                  </td>
                  <td className="px-4 py-2 font-mono text-[12.5px]">{r.identifier}</td>
                  <td className="px-4 py-2">
                    <Badge
                      variant="outline"
                      className="rounded-none border-border bg-transparent font-mono text-[10px] uppercase tracking-wider"
                    >
                      {REASON_LABELS[r.reason] ?? r.reason}
                    </Badge>
                  </td>
                  <td className="px-4 py-2 font-mono text-[11px] tabular-nums text-muted-foreground">
                    {r.created_at.split("T")[0]}
                  </td>
                  <td className="px-2 py-2 text-right">
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => remove(r)}
                      className="h-7 w-7 rounded-none text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                      aria-label="Eliminar"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
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
