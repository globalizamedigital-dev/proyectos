"use client";

import { useMemo, useState } from "react";
import { Mail, MessageCircle, Send, ServerCrash } from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ScoreChip } from "@/components/score-chip";
import { cn } from "@/lib/utils";

interface Template {
  id: string;
  slug: string;
  name: string;
  channel: "email" | "whatsapp";
  subject: string | null;
  body: string;
  variables: string[];
}

interface QueueLead {
  id: string;
  razon_social: string | null;
  decisor: string | null;
  email_principal: string | null;
  telefono: string | null;
  score: number;
  grade: "A" | "B" | "C" | "D";
  outreach_status: string;
}

interface Props {
  templates: Template[];
  leads: QueueLead[];
  error: string | null;
}

/** Sustituye {{var}} en el body por valores del lead seleccionado. */
function renderTemplate(body: string, lead: QueueLead | null): string {
  if (!lead) return body;
  const vars: Record<string, string> = {
    empresa: lead.razon_social || "tu empresa",
    nombre_corto: lead.decisor?.split(" ")[0] || "estimado/a",
    nombre_decisor: lead.decisor || "",
    sector: "tu sector",
    enlace_baja: "https://cazador.globalizame.com/unsubscribe?token=demo",
  };
  return body.replace(/\{\{(\w+)\}\}/g, (m, key) => vars[key] ?? m);
}

export function OutreachClient({ templates, leads, error }: Props) {
  const [templateId, setTemplateId] = useState<string>(templates[0]?.id ?? "");
  const [previewLeadId, setPreviewLeadId] = useState<string>(leads[0]?.id ?? "");
  const [selected, setSelected] = useState<Set<string>>(
    new Set(leads.filter((l) => l.outreach_status === "queued").map((l) => l.id)),
  );

  const template = useMemo(
    () => templates.find((t) => t.id === templateId) ?? templates[0],
    [templates, templateId],
  );
  const previewLead = useMemo(
    () => leads.find((l) => l.id === previewLeadId) ?? leads[0],
    [leads, previewLeadId],
  );
  const renderedSubject = useMemo(
    () => (template ? renderTemplate(template.subject ?? "", previewLead) : ""),
    [template, previewLead],
  );
  const renderedBody = useMemo(
    () => (template ? renderTemplate(template.body, previewLead) : ""),
    [template, previewLead],
  );

  const toggleSelect = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const withEmail = leads.filter((l) => l.email_principal).length;
  const withPhone = leads.filter((l) => l.telefono).length;
  const channel = template?.channel ?? "email";

  return (
    <div className="mx-auto flex w-full max-w-[1400px] flex-col gap-6 px-6 py-8 lg:px-10 lg:py-10">
      <header className="flex flex-col gap-2">
        <div className="flex items-center gap-3">
          <span aria-hidden className="h-px w-10 bg-primary" />
          <span className="label-eyebrow">módulo · outreach</span>
        </div>
        <h1 className="font-heading text-[42px] font-light leading-[1.05] tracking-tight md:text-[52px]">
          Cola de salida.
          <br />
          <span className="text-primary">Sin humo, con baja explícita.</span>
        </h1>
        <p className="max-w-2xl text-[14px] leading-relaxed text-muted-foreground">
          Selecciona la plantilla, revisa el preview con el primer lead de la
          cola, y dispara cuando estés. n8n hace el throttling y el seguimiento.
        </p>
      </header>

      {error && (
        <div className="flex items-center gap-2 border border-destructive/40 bg-destructive/[0.06] px-4 py-2 text-[12px] text-destructive">
          <ServerCrash className="h-4 w-4" />
          <span>Error cargando datos: {error}</span>
        </div>
      )}

      {/* Métricas top */}
      <div className="grid grid-cols-3 gap-px bg-border/40 border border-border/60">
        <Stat label="Leads en cola" value={leads.length} />
        <Stat label="Con email" value={withEmail} accent />
        <Stat label="Con teléfono" value={withPhone} />
      </div>

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-[420px_1fr]">
        {/* Izquierda: cola de leads */}
        <section className="border border-border/60 bg-card">
          <header className="flex items-center justify-between border-b border-border/60 bg-background/40 px-4 py-2.5">
            <span className="label-eyebrow">cola · {selected.size}/{leads.length} seleccionados</span>
            <Button
              size="sm"
              variant="ghost"
              onClick={() =>
                setSelected((prev) =>
                  prev.size === leads.length ? new Set() : new Set(leads.map((l) => l.id)),
                )
              }
              className="h-6 rounded-none px-2 text-[10px] uppercase tracking-wider"
            >
              {selected.size === leads.length ? "ninguno" : "todos"}
            </Button>
          </header>

          {leads.length === 0 ? (
            <div className="p-8 text-center">
              <p className="label-eyebrow mb-2">cola vacía</p>
              <p className="text-sm text-muted-foreground">
                Ve a <span className="font-medium text-foreground">Leads</span> y multi-selecciona
                "A outreach" para llenarla.
              </p>
            </div>
          ) : (
            <ul className="max-h-[560px] divide-y divide-border/40 overflow-y-auto">
              {leads.map((lead) => (
                <li
                  key={lead.id}
                  className={cn(
                    "flex cursor-pointer items-center gap-3 px-4 py-2.5 transition-colors",
                    previewLeadId === lead.id ? "bg-muted/40" : "hover:bg-muted/20",
                  )}
                  onClick={() => setPreviewLeadId(lead.id)}
                >
                  <input
                    type="checkbox"
                    checked={selected.has(lead.id)}
                    onChange={(e) => {
                      e.stopPropagation();
                      toggleSelect(lead.id);
                    }}
                    onClick={(e) => e.stopPropagation()}
                    className="accent-primary"
                  />
                  <ScoreChip score={lead.score} grade={lead.grade} size="sm" />
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm font-medium">
                      {lead.razon_social || "—"}
                    </div>
                    <div className="truncate font-mono text-[11px] text-muted-foreground">
                      {lead.email_principal || lead.telefono || "sin contacto"}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>

        {/* Derecha: editor + preview */}
        <section className="flex flex-col gap-4">
          {/* Selector de plantilla */}
          <div className="grid grid-cols-1 gap-px bg-border/40 border border-border/60 md:grid-cols-[1fr_220px_auto]">
            <div className="bg-card p-4">
              <FieldLabel index="01" label="Plantilla" />
              <Select value={templateId} onValueChange={(v) => v !== null && setTemplateId(v)}>
                <SelectTrigger className="h-10 rounded-none border-0 border-b border-border/0 bg-transparent px-0 text-sm shadow-none focus:ring-0">
                  <SelectValue placeholder="Selecciona" />
                </SelectTrigger>
                <SelectContent className="rounded-none border-border">
                  {templates.length === 0 ? (
                    <SelectItem value="__none" disabled className="rounded-none">
                      No hay plantillas
                    </SelectItem>
                  ) : (
                    templates.map((t) => (
                      <SelectItem key={t.id} value={t.id} className="rounded-none">
                        {t.name} · {t.channel}
                      </SelectItem>
                    ))
                  )}
                </SelectContent>
              </Select>
            </div>
            <div className="bg-card p-4">
              <FieldLabel index="02" label="Canal" />
              <Badge
                variant="outline"
                className="rounded-none border-secondary/60 bg-secondary/10 px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider text-secondary"
              >
                {channel === "email" ? (
                  <>
                    <Mail className="mr-1 h-3 w-3" />
                    email
                  </>
                ) : (
                  <>
                    <MessageCircle className="mr-1 h-3 w-3" />
                    whatsapp
                  </>
                )}
              </Badge>
            </div>
            <div className="bg-card p-4 flex items-end justify-end">
              <Button
                disabled={selected.size === 0 || !template}
                className="scanline-cta h-10 rounded-none bg-primary px-4 text-[11px] uppercase tracking-wider disabled:bg-primary/40"
              >
                <Send className="mr-1.5 h-3.5 w-3.5 relative z-[2]" />
                <span className="relative z-[2]">
                  Enviar a {selected.size} {selected.size === 1 ? "lead" : "leads"}
                </span>
              </Button>
            </div>
          </div>

          {/* Preview */}
          <div className="border border-border/60 bg-card">
            <header className="flex items-center justify-between border-b border-border/60 bg-background/40 px-4 py-2.5">
              <span className="label-eyebrow">preview · primer lead seleccionado</span>
              {previewLead && (
                <span className="text-[11px] tracking-wide text-muted-foreground">
                  → {previewLead.email_principal || previewLead.telefono || "sin destino"}
                </span>
              )}
            </header>
            {template ? (
              <div className="space-y-4 p-6">
                {channel === "email" && (
                  <div className="grid grid-cols-[80px_1fr] gap-3 border-b border-border/40 pb-3">
                    <span className="label-eyebrow self-start pt-0.5">Asunto</span>
                    <div className="font-medium">{renderedSubject || "—"}</div>
                  </div>
                )}
                <div className="grid grid-cols-[80px_1fr] gap-3">
                  <span className="label-eyebrow self-start pt-0.5">
                    {channel === "email" ? "Cuerpo" : "Mensaje"}
                  </span>
                  <pre className="whitespace-pre-wrap font-sans text-[13px] leading-relaxed text-foreground/90">
                    {renderedBody || "—"}
                  </pre>
                </div>
                {template.variables.length > 0 && (
                  <div className="grid grid-cols-[80px_1fr] gap-3 border-t border-border/40 pt-3">
                    <span className="label-eyebrow self-start pt-0.5">Vars</span>
                    <div className="flex flex-wrap gap-1">
                      {template.variables.map((v) => (
                        <Badge
                          key={v}
                          variant="outline"
                          className="rounded-none border-border/70 bg-transparent font-mono text-[10px] tracking-wider"
                        >
                          {`{{${v}}}`}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="p-8 text-center text-sm text-muted-foreground">
                Selecciona una plantilla para ver el preview.
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}

function FieldLabel({ index, label }: { index: string; label: string }) {
  return (
    <div className="mb-1 flex items-center gap-2">
      <span className="label-eyebrow text-primary/80 tabular-nums">{index}</span>
      <span className="label-eyebrow">{label}</span>
    </div>
  );
}

function Stat({ label, value, accent }: { label: string; value: number; accent?: boolean }) {
  return (
    <div className="bg-card p-4">
      <div
        className={cn(
          "numeral-display text-3xl",
          accent ? "text-primary" : "text-foreground",
        )}
      >
        {value.toString().padStart(2, "0")}
      </div>
      <div className="label-eyebrow mt-1">{label}</div>
    </div>
  );
}
