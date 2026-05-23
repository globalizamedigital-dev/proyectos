"use client";

import {
  Send,
  FileText,
  Shield,
  ShieldOff,
  Globe,
  Phone,
  Mail,
  Briefcase,
  Coins,
  Users,
  X,
} from "lucide-react";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
  SheetClose,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ScoreChip } from "@/components/score-chip";
import type { Lead } from "@/app/(app)/discover/_data/mock-leads";

interface LeadDetailSheetProps {
  lead: Lead | null;
  onClose(): void;
}

export function LeadDetailSheet({ lead, onClose }: LeadDetailSheetProps) {
  return (
    <Sheet open={lead !== null} onOpenChange={(open) => !open && onClose()}>
      <SheetContent
        side="right"
        className="w-full !max-w-[520px] gap-0 overflow-y-auto border-l-0 bg-card p-0 sm:max-w-[520px]"
      >
        {lead && (
          <div className="relative flex h-full flex-col">
            {/* Hairline verde a la izquierda */}
            <div
              aria-hidden
              className="absolute inset-y-0 left-0 w-[3px] bg-primary"
            />

            {/* Cabecera */}
            <SheetHeader className="space-y-0 border-b border-border/60 px-7 py-6">
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0 flex-1">
                  <div className="mb-2 flex items-center gap-2">
                    <ScoreChip
                      score={lead.score}
                      grade={lead.grade}
                      size="sm"
                    />
                    <span className="label-eyebrow">expediente · lead</span>
                  </div>
                  <SheetTitle className="font-heading text-2xl font-light leading-tight">
                    {lead.razonSocial}
                  </SheetTitle>
                  {/* Description inline para a11y; el bloque visual va aparte */}
                  <SheetDescription className="sr-only">
                    Ficha del lead {lead.razonSocial}
                    {lead.nif ? `, NIF ${lead.nif}` : ""}, ubicado en{" "}
                    {lead.city}.
                  </SheetDescription>
                  <div className="mt-2 flex flex-wrap items-center gap-3 text-[12px] tabular-nums tracking-wide text-muted-foreground">
                    {lead.nif && (
                      <span className="font-mono">NIF · {lead.nif}</span>
                    )}
                    <span>{lead.city}</span>
                    {lead.cnae && (
                      <span className="font-mono">CNAE · {lead.cnae}</span>
                    )}
                  </div>
                </div>

                <SheetClose
                  render={
                    <button
                      className="rounded-none border border-border p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                      aria-label="Cerrar"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  }
                />
              </div>
            </SheetHeader>

            <div className="flex-1 space-y-7 px-7 py-6">
              <Section icon={Globe} title="Web & contacto">
                <DataRow
                  label="Dominio"
                  value={
                    lead.domain ? (
                      <a
                        href={`https://${lead.domain}`}
                        target="_blank"
                        rel="noreferrer"
                        className="text-primary underline decoration-primary/40 underline-offset-4 transition-colors hover:decoration-primary"
                      >
                        {lead.domain}
                      </a>
                    ) : (
                      <Muted>sin web</Muted>
                    )
                  }
                />
                <DataRow
                  label="Email"
                  value={
                    lead.email ? (
                      <span className="flex items-center gap-2">
                        <Mail className="h-3.5 w-3.5 text-muted-foreground" />
                        <span className="font-mono text-[13px]">
                          {lead.email}
                        </span>
                        {lead.emailConfidence && (
                          <Badge
                            variant="outline"
                            className="rounded-none border-border bg-transparent text-[9px] uppercase tracking-wider"
                          >
                            {lead.emailConfidence}
                          </Badge>
                        )}
                      </span>
                    ) : (
                      <Muted>sin email</Muted>
                    )
                  }
                />
                <DataRow
                  label="Teléfono"
                  value={
                    lead.phone ? (
                      <span className="flex items-center gap-2">
                        <Phone className="h-3.5 w-3.5 text-muted-foreground" />
                        <span className="font-mono text-[13px] tabular-nums">
                          {lead.phone}
                        </span>
                      </span>
                    ) : (
                      <Muted>sin teléfono</Muted>
                    )
                  }
                />
                {lead.webNote && (
                  <p className="mt-1 border-l border-[var(--warning)]/60 bg-[var(--warning)]/[0.06] px-3 py-2 text-[11px] tracking-wide text-[var(--warning)]">
                    {lead.webNote}
                  </p>
                )}
              </Section>

              <Section icon={Users} title="Decisores">
                {lead.decisionMakers.length > 0 ? (
                  <ul className="divide-y divide-border/60">
                    {lead.decisionMakers.map((p) => (
                      <li
                        key={p.name}
                        className="flex items-center justify-between gap-3 py-2"
                      >
                        <div>
                          <div className="text-sm font-medium">{p.name}</div>
                          <div className="text-[11px] tracking-wide text-muted-foreground">
                            {p.role}
                          </div>
                        </div>
                        {p.email && (
                          <span className="truncate font-mono text-[11px] text-muted-foreground">
                            {p.email}
                          </span>
                        )}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <Muted>Sin decisores extraídos. Probar enriquecimiento manual.</Muted>
                )}
              </Section>

              <Section icon={Shield} title="Compliance">
                <div className="flex items-center gap-3">
                  {lead.compliance.dpoRegistered === true && (
                    <>
                      <Shield className="h-4 w-4 text-primary" />
                      <span className="text-sm">
                        DPO registrado en AEPD
                      </span>
                    </>
                  )}
                  {lead.compliance.dpoRegistered === false && (
                    <>
                      <ShieldOff className="h-4 w-4 text-muted-foreground" />
                      <span className="text-sm text-muted-foreground">
                        Sin DPO registrado
                      </span>
                    </>
                  )}
                  {lead.compliance.dpoRegistered === null && (
                    <>
                      <ShieldOff className="h-4 w-4 text-[var(--warning)]" />
                      <span className="text-sm text-[var(--warning)]">
                        AEPD no respondió
                      </span>
                    </>
                  )}
                </div>
                {lead.compliance.note && (
                  <p className="mt-1 text-[11px] text-muted-foreground">
                    {lead.compliance.note}
                  </p>
                )}
              </Section>

              <Section icon={Briefcase} title="Sector público">
                <div className="grid grid-cols-2 gap-px bg-border/40">
                  <Stat label="Contratos PLACSP" value={lead.publicSector.contracts} />
                  <Stat label="Subvenciones" value={lead.publicSector.subsidies} />
                </div>
              </Section>

              <Section icon={Coins} title="Fuentes que han contribuido">
                <div className="flex flex-wrap gap-1.5">
                  {lead.sources.map((s) => (
                    <Badge
                      key={s}
                      variant="outline"
                      className="rounded-none border-border/80 bg-background font-mono text-[10px] uppercase tracking-wider"
                    >
                      {s}
                    </Badge>
                  ))}
                </div>
              </Section>
            </div>

            {/* Footer pegado abajo */}
            <div className="sticky bottom-0 flex items-center gap-3 border-t border-border/60 bg-card px-7 py-4">
              <Button className="flex-1 rounded-none bg-primary text-primary-foreground hover:bg-primary/90">
                <Send className="mr-2 h-4 w-4" />
                Añadir a Outreach
              </Button>
              <Button
                variant="outline"
                className="rounded-none border-border bg-transparent"
              >
                <FileText className="mr-2 h-4 w-4" />
                Ficha completa
              </Button>
            </div>
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
}

function Section({
  icon: Icon,
  title,
  children,
}: {
  icon: typeof Globe;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="space-y-3">
      <header className="flex items-center gap-2 border-b border-border/60 pb-1.5">
        <Icon className="h-3.5 w-3.5 text-secondary" />
        <h3 className="label-eyebrow text-foreground">{title}</h3>
      </header>
      <div>{children}</div>
    </section>
  );
}

function DataRow({
  label,
  value,
}: {
  label: string;
  value: React.ReactNode;
}) {
  return (
    <div className="grid grid-cols-[110px_1fr] items-center gap-3 py-1.5">
      <span className="label-eyebrow">{label}</span>
      <div className="text-sm">{value}</div>
    </div>
  );
}

function Muted({ children }: { children: React.ReactNode }) {
  return <span className="text-muted-foreground">{children}</span>;
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="bg-card p-3">
      <div className="numeral-display text-3xl text-foreground">
        {value.toString().padStart(2, "0")}
      </div>
      <div className="label-eyebrow mt-1">{label}</div>
    </div>
  );
}
