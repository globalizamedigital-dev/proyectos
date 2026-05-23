import {
  Briefcase,
  Coins,
  Globe,
  Mail,
  Phone,
  Shield,
  ShieldOff,
  Users,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";

/** Shape conocido del payload de /analyze (extras tolerados). */
export interface AnalyzeResult {
  input?: { razon_social?: string; nif?: string };
  summary?: Record<string, unknown>;
  registralTimeline?: { date?: string; act?: string; note?: string }[];
  decisionMakers?: { name: string; role?: string; email?: string }[];
  emails?: { email: string; confidence?: string; via?: string }[];
  phones?: string[];
  web?: { domain?: string; resolved_via?: string; confidence?: string };
  compliance?: { dpoRegistered?: boolean | null; signal?: string };
  publicSector?: {
    contracts?: unknown[];
    subsidies?: unknown[];
  };
  warnings?: string[];
  [key: string]: unknown;
}

export function Ficha({ result }: { result: AnalyzeResult }) {
  const nombre = result.input?.razon_social || "Empresa sin nombre";
  const nif = result.input?.nif;
  const contracts = result.publicSector?.contracts?.length ?? 0;
  const subsidies = result.publicSector?.subsidies?.length ?? 0;
  const dpo = result.compliance?.dpoRegistered;

  return (
    <div className="space-y-8 border border-border/80 bg-card p-8">
      {/* Cabecera */}
      <header className="flex flex-col gap-2 border-b border-border/60 pb-6">
        <span className="label-eyebrow">expediente · empresa</span>
        <h2 className="font-heading text-3xl font-light leading-tight">{nombre}</h2>
        <div className="flex flex-wrap items-center gap-3 text-[12px] tabular-nums tracking-wide text-muted-foreground">
          {nif && <span className="font-mono">NIF · {nif}</span>}
          {result.web?.domain && (
            <a
              href={`https://${result.web.domain}`}
              target="_blank"
              rel="noreferrer"
              className="text-primary underline decoration-primary/40 underline-offset-4 hover:decoration-primary"
            >
              {result.web.domain}
            </a>
          )}
        </div>
      </header>

      {/* Decisores */}
      <Section icon={Users} title="Decisores">
        {result.decisionMakers && result.decisionMakers.length > 0 ? (
          <ul className="divide-y divide-border/60">
            {result.decisionMakers.map((p, i) => (
              <li key={`${p.name}-${i}`} className="flex items-center justify-between gap-4 py-2">
                <div>
                  <div className="text-sm font-medium">{p.name}</div>
                  {p.role && (
                    <div className="text-[11px] tracking-wide text-muted-foreground">{p.role}</div>
                  )}
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
          <Empty>No se han extraído decisores reales.</Empty>
        )}
      </Section>

      {/* Web & contacto */}
      <Section icon={Globe} title="Web & contacto">
        <div className="space-y-2">
          {result.emails && result.emails.length > 0 ? (
            <ul className="divide-y divide-border/60">
              {result.emails.slice(0, 6).map((e, i) => (
                <li key={`${e.email}-${i}`} className="flex items-center justify-between py-1.5">
                  <span className="flex items-center gap-2">
                    <Mail className="h-3.5 w-3.5 text-muted-foreground" />
                    <span className="font-mono text-[13px]">{e.email}</span>
                  </span>
                  {e.confidence && (
                    <Badge
                      variant="outline"
                      className="rounded-none border-border bg-transparent text-[9px] uppercase tracking-wider"
                    >
                      {e.confidence}
                    </Badge>
                  )}
                </li>
              ))}
            </ul>
          ) : (
            <Empty>Ningún email extraído.</Empty>
          )}
          {result.phones && result.phones.length > 0 && (
            <div className="flex items-center gap-2 pt-2 text-[13px]">
              <Phone className="h-3.5 w-3.5 text-muted-foreground" />
              <span className="font-mono tabular-nums">{result.phones.join(" · ")}</span>
            </div>
          )}
        </div>
      </Section>

      {/* Compliance */}
      <Section icon={Shield} title="Compliance · AEPD">
        <div className="flex items-center gap-3 text-sm">
          {dpo === true && (
            <>
              <Shield className="h-4 w-4 text-primary" />
              <span>DPO registrado en AEPD</span>
            </>
          )}
          {dpo === false && (
            <>
              <ShieldOff className="h-4 w-4 text-muted-foreground" />
              <span className="text-muted-foreground">Sin DPO registrado</span>
            </>
          )}
          {(dpo === null || dpo === undefined) && (
            <>
              <ShieldOff className="h-4 w-4 text-[var(--warning)]" />
              <span className="text-[var(--warning)]">AEPD no respondió</span>
            </>
          )}
        </div>
      </Section>

      {/* Sector público */}
      <Section icon={Briefcase} title="Sector público">
        <div className="grid grid-cols-2 gap-px bg-border/40">
          <Stat label="Contratos PLACSP" value={contracts} />
          <Stat label="Subvenciones" value={subsidies} />
        </div>
      </Section>

      {/* Timeline */}
      {result.registralTimeline && result.registralTimeline.length > 0 && (
        <Section icon={Coins} title="Timeline registral BORME">
          <ul className="divide-y divide-border/60">
            {result.registralTimeline.slice(0, 8).map((e, i) => (
              <li key={i} className="grid grid-cols-[120px_1fr] gap-3 py-2 text-[12.5px]">
                <span className="font-mono tabular-nums text-muted-foreground">
                  {e.date || "—"}
                </span>
                <div>
                  <div>{e.act || "—"}</div>
                  {e.note && (
                    <div className="text-[11px] text-muted-foreground">{e.note}</div>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </Section>
      )}

      {/* Avisos */}
      {result.warnings && result.warnings.length > 0 && (
        <div className="border-l border-[var(--warning)]/60 bg-[var(--warning)]/[0.06] px-4 py-3 text-[12px] text-[var(--warning)]">
          <div className="label-eyebrow mb-1 text-[var(--warning)]">avisos</div>
          <ul className="list-inside list-disc space-y-0.5">
            {result.warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
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

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="bg-card p-4">
      <div className="numeral-display text-3xl text-foreground">
        {value.toString().padStart(2, "0")}
      </div>
      <div className="label-eyebrow mt-1">{label}</div>
    </div>
  );
}

function Empty({ children }: { children: React.ReactNode }) {
  return <p className="text-sm text-muted-foreground">{children}</p>;
}
