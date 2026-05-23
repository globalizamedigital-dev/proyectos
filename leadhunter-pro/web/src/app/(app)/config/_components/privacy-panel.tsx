"use client";

import { useState } from "react";
import { Download, FileWarning, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { apiClient, ApiError } from "@/lib/api-client";
import { cn } from "@/lib/utils";

type Kind = "email" | "phone" | "nif";

interface ExportResult {
  counts: { leads: number; outreach_events: number; suppression: number };
  [key: string]: unknown;
}

interface EraseResult {
  deleted: { leads: number; suppression: number };
}

/**
 * Pestaña Privacidad: derechos RGPD para sujetos concretos.
 * - Export (art. 15): genera JSON con todos los datos del sujeto.
 * - Erase  (art. 17): elimina sin posibilidad de recuperación.
 *
 * Erase tiene confirmación explícita (escribir "ERASE") para evitar
 * borrados accidentales.
 */
export function PrivacyPanel() {
  const [kind, setKind] = useState<Kind>("email");
  const [value, setValue] = useState("");
  const [busy, setBusy] = useState<"export" | "erase" | null>(null);
  const [result, setResult] = useState<
    | { kind: "exported"; data: ExportResult; filename: string }
    | { kind: "erased"; data: EraseResult }
    | { kind: "error"; message: string }
    | null
  >(null);
  const [confirmText, setConfirmText] = useState("");

  const runExport = async () => {
    if (!value.trim()) return;
    setBusy("export");
    setResult(null);
    try {
      const data = (await apiClient.request("/privacy/export", {
        kind,
        value: value.trim(),
      })) as ExportResult;

      // Auto-descarga del JSON
      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: "application/json",
      });
      const filename = `gdpr-export-${kind}-${Date.now()}.json`;
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      setResult({ kind: "exported", data, filename });
    } catch (err) {
      setResult({
        kind: "error",
        message: err instanceof ApiError ? `${err.status} · ${err.message}` : String(err),
      });
    } finally {
      setBusy(null);
    }
  };

  const runErase = async () => {
    if (!value.trim() || confirmText !== "ERASE") return;
    setBusy("erase");
    setResult(null);
    try {
      const data = (await apiClient.requestDelete("/privacy/erase", {
        kind,
        value: value.trim(),
      })) as EraseResult;
      setResult({ kind: "erased", data });
      setValue("");
      setConfirmText("");
    } catch (err) {
      setResult({
        kind: "error",
        message: err instanceof ApiError ? `${err.status} · ${err.message}` : String(err),
      });
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="space-y-6 p-6">
      <header className="flex items-center justify-between border-b border-border/60 pb-4">
        <div className="flex items-center gap-3">
          <FileWarning className="h-4 w-4 text-secondary" />
          <span className="label-eyebrow">Privacidad · RGPD + LSSI</span>
        </div>
        <span className="text-[11px] tracking-wider text-muted-foreground">
          Derecho de acceso (art. 15) · Derecho al olvido (art. 17)
        </span>
      </header>

      <p className="text-[13px] leading-relaxed text-muted-foreground">
        Identifica al sujeto (email, teléfono o NIF), elige acción y dispara.
        El export descarga un JSON con todos los datos. El erase es{" "}
        <span className="font-medium text-foreground">irreversible</span>.
      </p>

      {/* Sujeto */}
      <div className="grid grid-cols-1 gap-px bg-border/40 border border-border/60 md:grid-cols-[160px_1fr]">
        <div className="bg-card p-4">
          <span className="label-eyebrow">tipo</span>
          <Select value={kind} onValueChange={(v) => v !== null && setKind(v as Kind)}>
            <SelectTrigger className="h-10 rounded-none border-0 border-b border-border/0 bg-transparent px-0 text-sm shadow-none focus:ring-0">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="rounded-none border-border">
              <SelectItem value="email" className="rounded-none">email</SelectItem>
              <SelectItem value="phone" className="rounded-none">teléfono</SelectItem>
              <SelectItem value="nif" className="rounded-none">NIF</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="bg-card p-4">
          <span className="label-eyebrow">identificador</span>
          <Input
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder={
              kind === "email"
                ? "ejemplo@dominio.com"
                : kind === "phone"
                  ? "+34 600 00 00 00"
                  : "B12345678"
            }
            className={cn(
              "h-10 rounded-none border-0 border-b border-border/0 bg-transparent px-0 text-sm shadow-none",
              "focus-visible:border-primary focus-visible:ring-0",
            )}
          />
        </div>
      </div>

      {/* Export */}
      <div className="space-y-3 border border-border/60 p-5">
        <div className="flex items-center gap-2">
          <Download className="h-4 w-4 text-primary" />
          <span className="label-eyebrow">01 · derecho de acceso</span>
        </div>
        <p className="text-[12px] leading-relaxed text-muted-foreground">
          Genera y descarga un JSON con todos los datos asociados al sujeto:
          leads, eventos de outreach y entradas de suppression.
        </p>
        <Button
          onClick={runExport}
          disabled={busy !== null || !value.trim()}
          className="rounded-none bg-primary uppercase tracking-wider"
        >
          {busy === "export" ? "Generando…" : "Generar export"}
        </Button>
      </div>

      {/* Erase */}
      <div className="space-y-3 border border-destructive/40 bg-destructive/[0.04] p-5">
        <div className="flex items-center gap-2">
          <Trash2 className="h-4 w-4 text-destructive" />
          <span className="label-eyebrow text-destructive">02 · derecho al olvido</span>
        </div>
        <p className="text-[12px] leading-relaxed text-destructive">
          Borra <span className="font-medium">de forma irreversible</span> todos
          los leads, eventos y entradas de suppression del sujeto. Escribe{" "}
          <code className="bg-destructive/15 px-1 py-0.5 font-mono">ERASE</code>{" "}
          para confirmar.
        </p>
        <div className="flex items-center gap-2">
          <Input
            value={confirmText}
            onChange={(e) => setConfirmText(e.target.value)}
            placeholder="Escribe ERASE para confirmar"
            className={cn(
              "h-10 max-w-[280px] rounded-none border-destructive/40 bg-transparent text-sm shadow-none",
              "focus-visible:border-destructive focus-visible:ring-0",
            )}
          />
          <Button
            onClick={runErase}
            disabled={busy !== null || !value.trim() || confirmText !== "ERASE"}
            className="rounded-none bg-destructive uppercase tracking-wider hover:bg-destructive/90"
          >
            {busy === "erase" ? "Borrando…" : "Borrar definitivamente"}
          </Button>
        </div>
      </div>

      {/* Resultado */}
      {result?.kind === "exported" && (
        <div className="border-l border-primary/60 bg-primary/[0.05] px-4 py-3 text-[12px]">
          <div className="label-eyebrow mb-1 text-primary">export listo</div>
          <div className="space-y-1 text-foreground">
            <div>
              Descargado: <code className="bg-muted/60 px-1 py-0.5 font-mono">{result.filename}</code>
            </div>
            <div className="text-muted-foreground">
              {result.data.counts.leads} leads · {result.data.counts.outreach_events} eventos ·{" "}
              {result.data.counts.suppression} suppression
            </div>
          </div>
        </div>
      )}
      {result?.kind === "erased" && (
        <div className="border-l border-destructive/60 bg-destructive/[0.06] px-4 py-3 text-[12px]">
          <div className="label-eyebrow mb-1 text-destructive">erased</div>
          <div className="text-foreground">
            Eliminados: {result.data.deleted.leads} leads · {result.data.deleted.suppression}{" "}
            suppression. Operación registrada en <code>usage_events</code>.
          </div>
        </div>
      )}
      {result?.kind === "error" && (
        <div className="border-l border-destructive/60 bg-destructive/[0.06] px-4 py-3 text-[12px] text-destructive">
          <div className="label-eyebrow mb-1 text-destructive">error</div>
          <div>{result.message}</div>
        </div>
      )}
    </div>
  );
}
